# Green IT – Optimisation des données de bout en bout

TD Green IT (Polytech). On suit des données météo de **Tunis** sur toute leur vie : collecte, nettoyage, échantillonnage, compression, transfert (HTTP ou MQTT) et stockage dans 3 bases (PostgreSQL, MongoDB, InfluxDB). Chaque étape est mesurée en **temps, CPU et énergie** (compteur RAPL du processeur), puis affichée dans **Grafana**.

> La leçon qui revient à chaque étape : **regrouper et éviter le travail inutile rapporte bien plus que choisir le « bon » outil.**

## Résultats clés

| Étape | Résultat |
|---|---|
| Nettoyage | 25 variables brutes → 4 utiles. Le point de rosée (r = 0,90) et le vent (r = −0,51) expliquent l'écart réel/ressenti |
| Échantillonnage | 1 jour par semaine (14 % des données) → 1,6 % d'erreur, 2 fois mieux qu'un tirage aléatoire de même taille |
| Compression | zstd -1/-3 = meilleur compromis. Sur 300 Mo, gzip -9 est 500 fois plus lent que zstd -3 et compresse moins |
| Transfert | MQTT économise 72 % des octets en envoi point par point, mais seulement 0,1 % quand tout est envoyé d'un coup |
| Bases de données | Écriture par lots 50 à 400 fois plus rapide qu'un par un. À 500 000 points, PostgreSQL est le plus rapide ; Mongo time-series est 40 fois plus compact que Mongo classique |

Les chiffres détaillés sont dans [`results/`](results/), notamment le tableau comparatif des bases [`results/db_tableau.md`](results/db_tableau.md).

## Architecture

```
.
├── fetch_raw.py         Collecte : 6 mois de météo horaire (Open-Meteo) → data/raw.json
├── analyse.py           Corrélation de chaque variable avec l'écart ressenti − réel
├── daily.py             Horaire → journalier (184 jours) → data/daily.json
├── stats.py             Fonctions réutilisables : moyennes, écarts, erreurs
├── sampling.py          Échantillonnages aléatoire, périodique, stratifié
├── compress.py          Banc gzip / zstd / lz4 (taux, temps, énergie)
├── gen_datasets.py      Jeux small / medium / big (4 416 / 499 008 / 50 M points)
├── measure.py           Mesure commune : durée, CPU, énergie RAPL, CPU/IO/RAM d'un conteneur
├── push.py              Envoi des résultats vers Pushgateway + annotations Grafana
├── transfer/            HTTP vs MQTT : proxy de comptage, serveur, abonné, scénarios
├── db/                  Banc commun + bench_postgres / bench_mongo / bench_influx, rapport
├── infra/               Docker : Mosquitto, PostgreSQL 17, MongoDB 8, InfluxDB 2.7
├── monitoring/          Docker : Prometheus, Grafana, node-exporter, cAdvisor, Pushgateway
├── data/                raw.json et daily.json versionnés ; le reste est régénérable
└── results/             CSV et journaux de toutes les mesures
```

### Comment on mesure

- **Énergie** : compteur RAPL d'Intel (`/sys/class/powercap/intel-rapl:0/energy_uj`), lu avant et après chaque action. On retire la consommation au repos, mesurée juste avant chaque banc.
- **Ressources d'une base** : lecture directe du cgroup du conteneur (CPU, octets lus/écrits sur disque, RAM). Les valeurs sont exactes, sans dépendre de la fréquence de collecte de Prometheus.
- **Octets transférés** : un proxy TCP (`transfer/proxy.py`) placé devant le serveur HTTP et devant le broker MQTT. Il compte les deux protocoles de la même façon.
- **Visualisation** : les scripts poussent leurs résultats vers le Pushgateway, et Prometheus les collecte toutes les 5 s. Le dashboard Grafana (`monitoring/gen_dashboard.py`) est provisionné automatiquement.

## Prérequis

- Linux avec cgroup v2, et un processeur **Intel** (pour RAPL)
- Docker et Docker Compose
- Python ≥ 3.10, ainsi que `gzip`, `zstd` et `lz4` en ligne de commande

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Lecture du compteur d'énergie (réservée à root ; à refaire après chaque redémarrage)
sudo chmod o+r /sys/class/powercap/intel-rapl:0/energy_uj

# Stacks Docker
(cd monitoring && docker compose up -d)
(cd infra && docker compose up -d)
```

Si tu as changé le mot de passe admin de Grafana, écris-le dans `.grafana_password` (une ligne, fichier ignoré par git). Les scripts en ont besoin pour créer les annotations.

| Service | Adresse |
|---|---|
| Grafana | http://localhost:3001 (admin/admin au premier lancement) |
| Prometheus | http://localhost:9092 |
| Pushgateway | http://localhost:9091 |
| PostgreSQL / MongoDB / InfluxDB | :5432 / :27017 / :8086 |
| Mosquitto | :1883 |

Les identifiants des bases (`td`/`td`, jeton InfluxDB `td-token`) sont des valeurs de développement local. Ne pas exposer ces services sur un réseau.

## Utilisation

Toutes les commandes se lancent depuis la racine du projet, dans l'ordre.

```bash
python3 fetch_raw.py                      # collecte (raw.json est déjà versionné)
python3 analyse.py                        # corrélations
python3 daily.py                          # agrégation journalière
.venv/bin/python sampling.py              # échantillonnage
.venv/bin/python compress.py              # compression (crée data/big.json, 300 Mo)
python3 gen_datasets.py                   # jeux de données (≈ 30 s, dont 2 Go pour big.csv)
./transfer/run.sh                         # HTTP vs MQTT (≈ 40 s)

cd db
TD_JEUX_UNITAIRE=small ./run_all.sh small medium   # bases de données, version courte (≈ 2 min)
../.venv/bin/python report.py                      # → results/db_tableau.md
```

Version complète, avec le jeu de 50 M et l'écriture un par un sur le jeu moyen (≈ 2 h). Le processus est détaché, il continue même si la session est fermée :

```bash
cd db && nohup setsid ./run_all.sh > ../results/db.log 2>&1 &
```

Pour arrêter : `docker compose down` dans `infra/` et `monitoring/`. Les données sont conservées dans les volumes Docker.

## Limites

- RAPL ne mesure que le processeur : RAM, disque et réseau ne sont pas comptés.
- RAPL mesure toute la machine. Il faut éviter toute autre activité pendant les mesures.
- Les actions de quelques millisecondes ont une énergie proche de 0 J, sous la résolution de RAPL.
- Une seule exécution par configuration : les écarts de moins de 2 fois ne sont pas significatifs.
- Les stations virtuelles sont des copies décalées d'une même série. Cela flatte la compression (zstd à grande fenêtre, Mongo time-series).
- Le jeu de 50 M points est généré mais n'a pas encore été testé sur les bases.

## Données

Météo historique fournie par [Open-Meteo](https://open-meteo.com/) (licence CC BY 4.0). Tunis : 36,806389 N, 10,181667 E, du 1er mai au 31 octobre 2026.
