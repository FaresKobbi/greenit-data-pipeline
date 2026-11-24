"""Envoie le petit jeu de données (4 416 points) en HTTP et en MQTT, selon plusieurs scénarios,
et mesure : octets transférés (proxy), temps, CPU émetteur / récepteur / broker, énergie.

Prérequis : proxy.py, http_server.py, mqtt_sub.py lancés (cf. run.sh) + broker Mosquitto.
"""
import csv
import json
import pathlib
import sys
import time

import paho.mqtt.client as mqtt
import requests

ICI = pathlib.Path(__file__).parent
sys.path.insert(0, str(ICI.parent))
from measure import Mesure, puissance_repos  # noqa: E402
from push import annoter, pousser  # noqa: E402

URL = "http://127.0.0.1:8001/meteo"  # via le proxy
STATS_HTTP, STATS_MQTT, STATS_PROXY = ("http://127.0.0.1:8000", "http://127.0.0.1:8002",
                                       "http://127.0.0.1:9101/stats")
HDR = {"Content-Type": "application/json"}


def charger(jeu="small"):
    with open(ICI.parent / "data" / f"{jeu}.csv") as f:
        return [{"station": r["station"], "time": int(r["time"]), "temp": float(r["temp"]),
                 "ressenti": float(r["ressenti"]), "rosee": float(r["rosee"]), "vent": float(r["vent"])}
                for r in csv.DictReader(f)]


def js(x):
    return json.dumps(x, separators=(",", ":"))


# ---------- émetteurs ----------
def http_unitaire_nouvelle_connexion(pts):
    for p in pts:  # requests.post sans Session : une connexion TCP par requête
        requests.post(URL, data=js(p), headers=HDR).raise_for_status()


def http_unitaire_keepalive(pts):
    with requests.Session() as s:
        for p in pts:
            s.post(URL, data=js(p), headers=HDR).raise_for_status()


def http_lot(pts):
    requests.post(URL, data=js(pts), headers=HDR).raise_for_status()


def _mqtt(messages, qos):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"td-emetteur-q{qos}")
    c.max_inflight_messages_set(100)
    c.connect("127.0.0.1", 1884)  # via le proxy
    c.loop_start()
    info = None
    for topic, payload in messages:
        info = c.publish(topic, payload, qos=qos)
    info.wait_for_publish()
    c.disconnect()
    c.loop_stop()


def mqtt_unitaire(qos):
    return lambda pts: _mqtt(((f"meteo/{p['station']}", js(p)) for p in pts), qos)


def mqtt_lot(pts):
    _mqtt([("meteo/lot", js(pts))], 1)


SCENARIOS = [
    ("HTTP unitaire, 1 connexion/requête", "http", http_unitaire_nouvelle_connexion),
    ("HTTP unitaire, keep-alive", "http", http_unitaire_keepalive),
    ("MQTT unitaire, QoS 0", "mqtt", mqtt_unitaire(0)),
    ("MQTT unitaire, QoS 1", "mqtt", mqtt_unitaire(1)),
    ("HTTP lot (1 requête)", "http", http_lot),
    ("MQTT lot (1 message, QoS 1)", "mqtt", mqtt_lot),
]


def attendre(url_stats, n, timeout=60):
    fin = time.time() + timeout
    while time.time() < fin:
        s = requests.get(url_stats + "/stats").json()
        if s["points"] >= n:
            return s
        time.sleep(0.02)
    raise TimeoutError(f"{url_stats}: {s['points']}/{n} points reçus")


def main():
    pts = charger()
    utile = sum(len(js(p)) for p in pts)  # octets "utiles" : les données JSON elles-mêmes
    p_repos = puissance_repos()
    print(f"{len(pts)} points, {utile} octets de données JSON utiles ; repos {p_repos:.2f} W\n")
    lignes = []
    for nom, proto, envoyer in SCENARIOS:
        recep = STATS_HTTP if proto == "http" else STATS_MQTT
        requests.get(recep + "/reset")
        p0 = requests.get(STATS_PROXY).json()[proto]
        debut = time.time()
        with Mesure("storing-infra-mosquitto-1", p_repos) as m:
            envoyer(pts)
            r = attendre(recep, len(pts))
        annoter(debut, time.time(), nom, ["transfert", proto])
        p1 = requests.get(STATS_PROXY).json()[proto]
        mont, desc = p1["montant"] - p0["montant"], p1["descendant"] - p0["descendant"]
        l = {"scenario": nom, "proto": proto, "messages": r.get("requetes", r.get("messages")),
             "connexions_tcp": p1["connexions"] - p0["connexions"],
             "octets_montants": mont, "octets_descendants": desc, "octets_total": mont + desc,
             "octets_utiles": utile, "surcout_pct": round((mont + desc - utile) / utile * 100, 1),
             "duree_s": round(m.res["duree_s"], 3), "cpu_emetteur_s": round(m.res["cpu_client_s"], 3),
             "cpu_recepteur_s": round(r["cpu_s"], 3), "cpu_broker_s": round(m.res["cpu_conteneur_s"], 3),
             "energie_nette_J": round(m.res.get("energie_nette_J", float("nan")), 2)}
        lignes.append(l)
        pousser("transfert", {"scenario": nom, "proto": proto}, {
            "td_transfert_octets_total": l["octets_total"], "td_transfert_octets_montants": mont,
            "td_transfert_octets_descendants": desc, "td_transfert_duree_s": l["duree_s"],
            "td_transfert_cpu_emetteur_s": l["cpu_emetteur_s"], "td_transfert_cpu_recepteur_s": l["cpu_recepteur_s"],
            "td_transfert_cpu_broker_s": l["cpu_broker_s"], "td_transfert_energie_nette_joules": l["energie_nette_J"]})
        print(f"{nom:36s} {l['octets_total']:>10,d} o  surcoût {l['surcout_pct']:>6.1f} %  "
              f"{l['duree_s']:6.2f} s  CPU émet {l['cpu_emetteur_s']:.2f} s  récep {l['cpu_recepteur_s']:.2f} s  "
              f"broker {l['cpu_broker_s']:.2f} s  {l['energie_nette_J']:.1f} J  ({l['connexions_tcp']} connexions)")
        time.sleep(2)  # sépare les scénarios sur les courbes Grafana

    o = {l["scenario"]: l["octets_total"] for l in lignes}

    def eco(a, b):
        return f"{(1 - o[a] / o[b]) * 100:5.1f} %"
    print("\nÉconomie d'octets grâce à MQTT :")
    print(f"  QoS 0 vs HTTP keep-alive          : {eco('MQTT unitaire, QoS 0', 'HTTP unitaire, keep-alive')}")
    print(f"  QoS 1 vs HTTP keep-alive          : {eco('MQTT unitaire, QoS 1', 'HTTP unitaire, keep-alive')}")
    print(f"  QoS 1 vs HTTP 1 connexion/requête : {eco('MQTT unitaire, QoS 1', 'HTTP unitaire, 1 connexion/requête')}")
    print(f"  Lot : MQTT vs HTTP                : {eco('MQTT lot (1 message, QoS 1)', 'HTTP lot (1 requête)')}")

    out = ICI.parent / "results" / "transfert.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=lignes[0].keys())
        w.writeheader()
        w.writerows(lignes)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
