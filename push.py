"""Envoi des résultats du TD vers la stack storing/monitoring.

- pousser()  : métriques -> Pushgateway (scrapé par Prometheus) -> panneaux Grafana
- annoter()  : zone temporelle annotée dans Grafana (visible sur les courbes de puissance)

Identifiants Grafana : variable d'env GRAFANA_PASSWORD, sinon fichier storing/.grafana_password
(une ligne), sinon admin/admin. Si un service est injoignable, on prévient une fois et on continue.
"""
import base64
import os
import pathlib

import requests

PUSHGATEWAY = "http://localhost:9091"
GRAFANA = "http://localhost:3001"
_fichier_mdp = pathlib.Path(__file__).parent / ".grafana_password"
_mdp = os.environ.get("GRAFANA_PASSWORD") or \
    (_fichier_mdp.read_text().strip() if _fichier_mdp.exists() else "admin")
GRAFANA_AUTH = (os.environ.get("GRAFANA_USER", "admin"), _mdp)
_hs = set()  # services en échec


def _echec(service, e):
    if service not in _hs:
        print(f"[push] {service} : échec ({e}) -> désactivé pour ce run")
    _hs.add(service)


def pousser(job, labels, metriques):
    """labels : identifient le groupe (ex. outil/niveau) ; metriques : {nom: valeur}."""
    if "pushgateway" in _hs:
        return
    # valeurs encodées en base64 : supporte '/', ':', espaces... dans les labels
    chemin = "".join(f"/{k}@base64/{base64.urlsafe_b64encode(str(v).encode()).decode() or '='}"
                     for k, v in labels.items())
    corps = "".join(f"{n} {v}\n" for n, v in metriques.items() if v is not None and v == v)  # v==v : pas NaN
    try:
        requests.put(f"{PUSHGATEWAY}/metrics/job/{job}{chemin}", data=corps, timeout=2).raise_for_status()
    except requests.RequestException as e:
        _echec("pushgateway", e)


def annoter(debut, fin, texte, tags):
    """debut/fin : time.time() en secondes."""
    if "grafana" in _hs:
        return
    try:
        requests.post(f"{GRAFANA}/api/annotations", auth=GRAFANA_AUTH, timeout=2,
                      json={"time": int(debut * 1000), "timeEnd": int(fin * 1000),
                            "text": texte, "tags": ["td", *tags]}).raise_for_status()
    except requests.RequestException as e:
        _echec("grafana (annotations ; mot de passe dans storing/.grafana_password ?)", e)
