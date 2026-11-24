"""Échantillonnages aléatoire, périodique et stratifié sur daily.json.

Pour chaque méthode : % de données conservées, erreur moyenne / pire erreur sur les
6 moyennes de température, précision (= 100 - erreur) et ratio précision / % conservé.
Les tirages aléatoires sont répétés N fois (184 jours seulement : un tirage isolé ne veut rien dire).
"""
import csv
import json
import pathlib
import random
from collections import defaultdict
from statistics import mean, quantiles

from push import pousser
from stats import METRIQUES, ecarts, erreur_moyenne, erreurs, moyennes

ICI = pathlib.Path(__file__).parent
JOURS = json.loads((ICI / "data" / "daily.json").read_text())
REF = moyennes(JOURS)
N = 500  # répétitions par configuration aléatoire
rng = random.Random(42)  # graine fixe : résultats reproductibles


# ---------- méthodes ----------
def aleatoire(jours, pct):
    k = max(1, round(len(jours) * pct / 100))
    return rng.sample(jours, k)


def periodique_semaine(jours, decalage):
    """1 jour sur 7, en commençant au jour `decalage` (0..6)."""
    return jours[decalage::7]


def periodique_mois(jours, jour_du_mois):
    """1 jour par mois : le `jour_du_mois` de chaque mois."""
    return [j for j in jours if int(j["date"][8:]) == jour_du_mois]


def strates(jours, cle):
    groupes = defaultdict(list)
    for j in jours:
        groupes[cle(j)].append(j)
    return groupes


def stratifie(groupes, pct):
    """Tirage aléatoire dans chaque strate (allocation proportionnelle), puis moyenne
    pondérée par la taille des strates (estimateur stratifié)."""
    total = sum(len(g) for g in groupes.values())
    moy = dict.fromkeys(METRIQUES, 0.0)
    gardes = 0
    for g in groupes.values():
        ech = rng.sample(g, max(1, round(len(g) * pct / 100)))
        gardes += len(ech)
        for m, v in moyennes(ech).items():
            moy[m] += v * len(g) / total
    return moy, gardes


def classes_terciles(champ):
    s1, s2 = quantiles([j[champ] for j in JOURS], n=3)
    return lambda j: 0 if j[champ] < s1 else (1 if j[champ] < s2 else 2)


STRATES = {
    "mois": lambda j: j["date"][:7],
    "rosee (terciles)": classes_terciles("rosee_moy"),
    "vent (terciles)": classes_terciles("vent_moy"),
}


# ---------- expériences ----------
lignes = []


def ajouter(methode, param, n_gardes, errs):
    pct = n_gardes / len(JOURS) * 100
    e_moy, e_max = mean(errs), max(errs)
    lignes.append({
        "methode": methode, "param": param, "jours": round(n_gardes, 1), "pct_donnees": round(pct, 1),
        "erreur_moy_pct": round(e_moy, 2), "erreur_max_pct": round(e_max, 2),
        "precision_pct": round(100 - e_moy, 2), "ratio_precision_quantite": round((100 - e_moy) / pct, 2),
    })


POURCENTAGES = [1, 2, 5, 10, 15, 20, 30, 50]

for pct in POURCENTAGES:
    ech = [aleatoire(JOURS, pct) for _ in range(N)]
    ajouter("aleatoire", f"{pct}%", len(ech[0]), [erreur_moyenne(REF, moyennes(e)) for e in ech])

# périodique : on teste TOUS les décalages possibles (pas de hasard à répéter)
ech = [periodique_semaine(JOURS, d) for d in range(7)]
ajouter("periodique", "1/semaine", mean(len(e) for e in ech), [erreur_moyenne(REF, moyennes(e)) for e in ech])
ech = [periodique_mois(JOURS, d) for d in range(1, 29)]
ajouter("periodique", "1/mois", mean(len(e) for e in ech), [erreur_moyenne(REF, moyennes(e)) for e in ech])

for nom, cle in STRATES.items():
    groupes = strates(JOURS, cle)
    for pct in POURCENTAGES:
        res = [stratifie(groupes, pct) for _ in range(N)]
        ajouter(f"stratifie:{nom}", f"{pct}%", mean(g for _, g in res), [erreur_moyenne(REF, m) for m, _ in res])

# ---------- sorties ----------
print("Référence (184 jours) :")
for m, v in REF.items():
    print(f"  {m:14s} {v:6.2f} °C")
print("Écarts réel -> ressenti :")
for m, d in ecarts(REF).items():
    print(f"  {m:14s} {d['abs']:+.2f} °C  ({d['pct']:+.1f} %)")

print(f"\n{'méthode':26s} {'param':10s} {'jours':>6s} {'%data':>6s} {'err moy':>8s} {'err max':>8s} {'ratio':>6s}")
for l in lignes:
    print(f"{l['methode']:26s} {l['param']:10s} {l['jours']:6.1f} {l['pct_donnees']:6.1f} "
          f"{l['erreur_moy_pct']:7.2f}% {l['erreur_max_pct']:7.2f}% {l['ratio_precision_quantite']:6.1f}")

# précision catégorie par catégorie (strate "mois", 10 %)
print("\nErreur par strate (stratifié par mois, 10 %, moyenne sur N tirages) :")
for nom_s, g in strates(JOURS, STRATES["mois"]).items():
    ref_s = moyennes(g)
    k = max(1, round(len(g) * 0.10))
    errs = [erreur_moyenne(ref_s, moyennes(rng.sample(g, k))) for _ in range(N)]
    print(f"  {nom_s}  {len(g):3d} jours -> {k} gardés  erreur moy {mean(errs):.2f} %")

for l in lignes:
    pousser("echantillonnage", {"methode": l["methode"], "param": l["param"]}, {
        "td_echantillonnage_pct_donnees": l["pct_donnees"],
        "td_echantillonnage_erreur_moy_pct": l["erreur_moy_pct"],
        "td_echantillonnage_erreur_max_pct": l["erreur_max_pct"],
    })

out = ICI / "results" / "sampling.csv"
out.parent.mkdir(exist_ok=True)
with out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=lignes[0].keys())
    w.writeheader()
    w.writerows(lignes)
print(f"\n-> {out}")
