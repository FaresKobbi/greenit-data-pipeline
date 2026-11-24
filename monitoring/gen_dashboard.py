"""Génère grafana/dashboards/td-stockage.json.  Usage : python3 gen_dashboard.py"""
import json, sys
DS = {"type": "prometheus", "uid": "prom-storing"}
PKG = 'node_rapl_package_joules_total{path=~".*/intel-rapl:0"}'
NET = 'device!~"lo|veth.*|docker.*|br-.*"'
panels, y, pid = [], 0, 0

def nid():
    global pid; pid += 1; return pid

def row(title):
    global y
    panels.append({"type": "row", "title": title, "id": nid(), "collapsed": False,
                   "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}); y += 1

def tgt(expr, legend="", instant=False, ref="A"):
    t = {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": ref}
    if instant: t.update(instant=True, range=False)
    return t

def ts(title, targets, unit, x, w, h=8, desc=""):
    panels.append({"type": "timeseries", "title": title, "id": nid(), "datasource": DS,
        "description": desc, "gridPos": {"x": x, "y": y, "w": w, "h": h}, "targets": targets,
        "fieldConfig": {"defaults": {"unit": unit, "custom": {"fillOpacity": 10, "lineWidth": 1}}, "overrides": []},
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}}})

def stat(title, expr, unit, x, w, h=4, desc="", decimals=None):
    d = {"unit": unit}
    if decimals is not None: d["decimals"] = decimals
    panels.append({"type": "stat", "title": title, "id": nid(), "datasource": DS, "description": desc,
        "gridPos": {"x": x, "y": y, "w": w, "h": h}, "targets": [tgt(expr, instant=True)],
        "fieldConfig": {"defaults": d, "overrides": []},
        "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "value", "graphMode": "none"}})

def bars(title, expr, legend, unit, x, w, h=11, desc="", sort=None):
    panels.append({"type": "bargauge", "title": title, "id": nid(), "datasource": DS, "description": desc,
        "gridPos": {"x": x, "y": y, "w": w, "h": h}, "targets": [tgt(expr, legend, instant=True)],
        "fieldConfig": {"defaults": {"unit": unit, "min": 0, "color": {"mode": "continuous-BlPu"}}, "overrides": []},
        "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "orientation": "horizontal",
                    "displayMode": "gradient", "showUnfilled": True, "valueMode": "color", "namePlacement": "left"},
        "transformations": ([{"id": "sortBy", "options": {"sort": [{"field": sort}]}}] if sort else [])})

# ---- Live ----
row("Mesures en direct (RAPL + node-exporter)")
stat("Puissance package actuelle", f"rate({PKG}[30s])", "watt", 0, 4, desc="Compteur RAPL du package CPU")
stat("Énergie sur la période", f"increase({PKG}[$__range]) / 3600", "watth", 4, 4, decimals=2,
     desc="Énergie package CPU consommée sur la plage de temps sélectionnée")
stat("CO₂e sur la période", f"increase({PKG}[$__range]) / 3600 / 1000 * $intensite", "massg", 8, 4, decimals=3,
     desc="Énergie (kWh) × intensité carbone du réseau (variable 'intensite', g CO₂e/kWh)")
stat("CPU moyen sur la période", f'100 * (1 - avg(avg_over_time(rate(node_cpu_seconds_total{{mode="idle"}}[1m])[$__range:])))',
     "percent", 12, 4, decimals=1)
stat("Puissance moyenne sur la période", f"increase({PKG}[$__range]) / $__range_s", "watt", 16, 4, decimals=1)
stat("Estimation machine entière", f"increase({PKG}[$__range]) / 3600 * $facteur_machine", "watth", 20, 4, decimals=2,
     desc="RAPL ne mesure que CPU (+ uncore). Estimation grossière de la machine entière : × facteur (variable).")
y += 4
ts("Puissance RAPL (W) – zones annotées = benchmarks", [
    tgt(f"rate({PKG}[$__rate_interval])", "package", ref="A"),
    tgt("rate(node_rapl_core_joules_total[$__rate_interval])", "cœurs", ref="B"),
    tgt("rate(node_rapl_uncore_joules_total[$__rate_interval])", "uncore (GPU intégré...)", ref="C")],
   "watt", 0, 12, desc="Les zones colorées sont les annotations envoyées par les scripts (push.py)")
ts("CPU (%)", [tgt('100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[$__rate_interval])))', "CPU total"),
               tgt('100 * avg(rate(node_cpu_seconds_total{mode="iowait"}[$__rate_interval]))', "iowait", ref="B")],
   "percent", 12, 12)
y += 8
ts("Disque (octets/s)", [tgt('sum(rate(node_disk_read_bytes_total[$__rate_interval]))', "lecture"),
                         tgt('sum(rate(node_disk_written_bytes_total[$__rate_interval]))', "écriture", ref="B")],
   "Bps", 0, 12, desc="Utile pour la partie stockage en base")
ts("Réseau (octets/s)", [tgt(f'sum(rate(node_network_receive_bytes_total{{{NET}}}[$__rate_interval]))', "reçu"),
                         tgt(f'sum(rate(node_network_transmit_bytes_total{{{NET}}}[$__rate_interval]))', "envoyé", ref="B")],
   "Bps", 12, 12, desc="Utile pour la partie transfert / protocoles")
y += 8

# ---- Compression ----
row("Compression (résultats poussés par compress.py)")
F = 'fichier=~"$fichier"'
L = "{{fichier}} · {{outil}} -{{niveau}}"
bars("Gain de compression (%)", f"td_compression_gain_pct{{{F}}}", L, "percent", 0, 8)
bars("Temps de compression", f"td_compression_temps_s{{{F}}}", L, "s", 8, 8)
bars("Énergie nette de compression", f"td_compression_energie_nette_joules{{{F}}}", L, "joule", 16, 8,
     desc="Énergie RAPL package pendant la compression, moins la consommation au repos")
y += 11
bars("Ratio gain / temps (% par s)", f"td_compression_gain_pct{{{F}}} / td_compression_temps_s{{{F}}}", L, "none", 0, 8)
bars("Ratio gain / énergie (% par J)", f"td_compression_gain_pct{{{F}}} / td_compression_energie_nette_joules{{{F}}}", L, "none", 8, 8)
bars("Temps de décompression", f"td_decompression_temps_s{{{F}}}", L, "s", 16, 8)
y += 11

# ---- Échantillonnage ----
row("Échantillonnage (résultats poussés par sampling.py)")
M = 'methode=~"$methode"'
bars("Erreur moyenne vs référence (%)", f"td_echantillonnage_erreur_moy_pct{{{M}}}", "{{methode}} · {{param}}", "percent", 0, 8, h=16)
bars("Pire erreur (%)", f"td_echantillonnage_erreur_max_pct{{{M}}}", "{{methode}} · {{param}}", "percent", 8, 8, h=16)
bars("Données conservées (%)", f"td_echantillonnage_pct_donnees{{{M}}}", "{{methode}} · {{param}}", "percent", 16, 8, h=16)
y += 16


# ---- Transfert ----
row("Transfert HTTP vs MQTT (proxy + transfer/send.py)")
ts("Débit à travers le proxy (octets/s)", [tgt("rate(td_proxy_octets_total[$__rate_interval])", "{{proto}} {{sens}}")],
   "Bps", 0, 12, desc="Compté par transfer/proxy.py (niveau applicatif, sans en-têtes TCP/IP)")
ts("CPU broker Mosquitto (cœurs)", [tgt('rate(container_cpu_usage_seconds_total{name="storing-infra-mosquitto-1"}[$__rate_interval])', "mosquitto")],
   "none", 12, 12)
y += 8
SC = "{{scenario}}"
bars("Octets transférés (total)", "td_transfert_octets_total", SC, "decbytes", 0, 8, h=8)
bars("Durée d'envoi", "td_transfert_duree_s", SC, "s", 8, 8, h=8)
bars("Énergie nette", "td_transfert_energie_nette_joules", SC, "joule", 16, 8, h=8)
y += 8
bars("CPU récepteur (serveur HTTP / abonné MQTT)", "td_transfert_cpu_recepteur_s", SC, "s", 0, 8, h=8)
bars("CPU émetteur", "td_transfert_cpu_emetteur_s", SC, "s", 8, 8, h=8)
bars("CPU broker", "td_transfert_cpu_broker_s", SC, "s", 16, 8, h=8)
y += 8

# ---- Bases de données ----
row("Bases de données (cAdvisor + db/bench_*.py)")
C = 'name=~"storing-infra-(postgres|mongo|influxdb).*"'
LC = "{{name}}"
ts("CPU par base (cœurs)", [tgt(f"rate(container_cpu_usage_seconds_total{{{C}}}[$__rate_interval])", LC)], "none", 0, 8)
ts("RAM par base", [tgt(f"container_memory_working_set_bytes{{{C}}}", LC)], "bytes", 8, 8)
ts("Écritures disque par base (octets/s)", [tgt(f"sum by (name) (rate(container_fs_writes_bytes_total{{{C}}}[$__rate_interval]))", LC)],
   "Bps", 16, 8)
y += 8
D = 'jeu=~"$jeu", action=~"$action"'
LD = "{{base}} · {{jeu}} · {{action}} · {{mode}}"
bars("Durée par action", f"td_db_duree_s{{{D}}}", LD, "s", 0, 8, h=16, desc="Échelle très large : filtrer par jeu / action en haut")
bars("Énergie nette par action", f"td_db_energie_nette_joules{{{D}}}", LD, "joule", 8, 8, h=16)
bars("CPU de la base par action", f"td_db_cpu_base_s{{{D}}}", LD, "s", 16, 8, h=16)
y += 16
bars("Débit d'écriture (points/s)", f'td_db_debit_pts_s{{jeu=~"$jeu"}}', "{{base}} · {{jeu}} · {{mode}}", "short", 0, 8, h=12)
bars("Écritures disque par action", f"td_db_io_ecriture_octets{{{D}}}", LD, "decbytes", 8, 8, h=12)
bars("Taille sur disque des données", f'td_db_taille_octets{{jeu=~"$jeu"}}', "{{base}} · {{jeu}}", "decbytes", 16, 8, h=12)
y += 12

def var_query(name, label, metric):
    return {"name": name, "label": label, "type": "query", "datasource": DS, "includeAll": True, "multi": True,
            "current": {"text": "All", "value": "$__all"}, "allValue": ".*", "refresh": 2,
            "query": {"query": f"label_values({metric}, {name})", "refId": name}, "definition": f"label_values({metric}, {name})"}

dash = {
    "uid": "td-stockage", "title": "TD Stockage – énergie & résultats", "schemaVersion": 39, "version": 1,
    "time": {"from": "now-30m", "to": "now"}, "refresh": "10s", "tags": ["greenit", "td-stockage"],
    "annotations": {"list": [
        {"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": True, "hide": True,
         "iconColor": "rgba(0, 211, 255, 1)", "name": "Annotations & Alerts", "type": "dashboard"},
        {"datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": True, "iconColor": "orange",
         "name": "Benchmarks TD", "target": {"type": "tags", "tags": ["td"], "matchAny": True, "limit": 1000}}]},
    "templating": {"list": [
        var_query("fichier", "Fichier", "td_compression_gain_pct"),
        var_query("methode", "Méthode d'échantillonnage", "td_echantillonnage_erreur_moy_pct"),
        var_query("jeu", "Jeu de données", "td_db_duree_s"),
        var_query("action", "Action BDD", "td_db_duree_s"),
        {"name": "intensite", "label": "Intensité carbone (gCO₂e/kWh)", "type": "textbox", "query": "56",
         "current": {"text": "56", "value": "56"},
         "description": "Mix électrique ; ~56 France (ADEME), ~470 Tunisie. À adapter."},
        {"name": "facteur_machine", "label": "Facteur machine / CPU", "type": "textbox", "query": "1.5",
         "current": {"text": "1.5", "value": "1.5"}}]},
    "panels": panels,
}
import pathlib
out = pathlib.Path(__file__).parent / "grafana" / "dashboards" / "td-stockage.json"
json.dump(dash, out.open("w"), indent=1, ensure_ascii=False)
print("->", out)
