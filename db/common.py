"""Banc d'essai commun aux 3 bases : écriture (unitaire / par lots), lecture brute, agrégation.

Chaque script bench_<base>.py définit une classe Base et appelle bench().
Mesures par action (cf. measure.py) : durée, CPU client, CPU / I/O / RAM du conteneur de la base
(cgroup), énergie RAPL. Résultats : results/db.csv (ajout), Pushgateway, annotations Grafana.

    python bench_postgres.py [small medium big]
"""
import argparse
import csv
import os
import pathlib
import sys
import time
from datetime import datetime

ICI = pathlib.Path(__file__).parent
sys.path.insert(0, str(ICI.parent))
from measure import Mesure, puissance_repos  # noqa: E402
from push import annoter, pousser  # noqa: E402

DATA = ICI.parent / "data"
RESULTATS = ICI.parent / "results" / "db.csv"
# jeux écrits aussi un par un (50 M en unitaire = plusieurs heures par base).
# Version courte : TD_JEUX_UNITAIRE=small
JEUX_UNITAIRE = set(os.environ.get("TD_JEUX_UNITAIRE", "small,medium").split(","))
TAILLE_LOT = 10_000
REPETITIONS = 5


def lire_points(jeu):
    """(station, time epoch s, temp, ressenti, rosee, vent), en flux (le gros jeu ne tient pas en RAM)."""
    with open(DATA / f"{jeu}.csv", buffering=1 << 20) as f:
        next(f)
        for ligne in f:
            s, t, te, ap, ro, ve = ligne.rstrip("\n").split(",")
            yield s, int(t), float(te), float(ap), float(ro), float(ve)


def lots(it, n=TAILLE_LOT):
    lot = []
    for x in it:
        lot.append(x)
        if len(lot) == n:
            yield lot
            lot = []
    if lot:
        yield lot


class Base:
    nom = "?"
    conteneur = "?"
    modes_unitaires = ["unitaire"]

    def reinitialiser(self): ...
    def preparer_mode(self, mode): ...
    def ecrire_un(self, p): ...
    def ecrire_lot(self, pts): ...
    def fin_ecriture(self): ...           # mesuré (ex. flush)
    def apres_ecriture(self): ...         # non mesuré (ex. ANALYZE)
    def lire_derniers(self, n=100): ...   # ORDER BY time DESC LIMIT n
    def moyenne_temp(self): ...
    def taille_octets(self): ...


def _enregistrer(lignes):
    nouveau = not RESULTATS.exists()
    RESULTATS.parent.mkdir(exist_ok=True)
    with RESULTATS.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=lignes[0].keys())
        if nouveau:
            w.writeheader()
        w.writerows(lignes)


def _ligne(base, jeu, action, mode, n, res, extra=None):
    l = {"date": datetime.now().isoformat(timespec="seconds"), "base": base.nom, "jeu": jeu,
         "action": action, "mode": mode, "points": n,
         "duree_s": round(res["duree_s"], 5),
         "debit_pts_s": round(n / res["duree_s"]) if action == "ecriture" else "",
         "cpu_client_s": round(res["cpu_client_s"], 4), "cpu_base_s": round(res["cpu_conteneur_s"], 4),
         "io_lecture_o": res["io_lecture_o"], "io_ecriture_o": res["io_ecriture_o"],
         "ram_base_o": res["ram_conteneur_o"],
         "energie_J": round(res.get("energie_J", float("nan")), 3),
         "energie_nette_J": round(res.get("energie_nette_J", float("nan")), 3),
         "taille_base_o": "", "resultat": ""}
    l.update(extra or {})
    pousser("db", {"base": base.nom, "jeu": jeu, "action": action, "mode": mode}, {
        "td_db_duree_s": l["duree_s"], "td_db_cpu_base_s": l["cpu_base_s"],
        "td_db_cpu_client_s": l["cpu_client_s"], "td_db_io_ecriture_octets": l["io_ecriture_o"],
        "td_db_io_lecture_octets": l["io_lecture_o"], "td_db_ram_octets": l["ram_base_o"],
        "td_db_energie_nette_joules": l["energie_nette_J"],
        "td_db_debit_pts_s": l["debit_pts_s"] or None,
        "td_db_taille_octets": l["taille_base_o"] or None})
    print(f"  {action:10s} {mode:18s} {l['duree_s']:10.4f} s  cpu base {l['cpu_base_s']:8.3f} s  "
          f"io w {l['io_ecriture_o'] / 1e6:9.1f} Mo  {l['energie_nette_J']:9.2f} J  "
          f"{'' if not l['debit_pts_s'] else str(l['debit_pts_s']) + ' pts/s'} {l['resultat']}", flush=True)
    return l


def mesurer(base, p_repos, etiquette, fn):
    debut = time.time()
    with Mesure(base.conteneur, p_repos) as m:
        r = fn()
    annoter(debut, time.time(), f"{base.nom} : {etiquette}", ["db", base.nom])
    return m.res, r


def bench(base, jeux):
    p_repos = puissance_repos()
    print(f"### {base.nom} — repos {p_repos:.2f} W", flush=True)
    for jeu in jeux:
        print(f"## {base.nom} / {jeu}", flush=True)
        lignes = []
        modes = (base.modes_unitaires if jeu in JEUX_UNITAIRE else []) + ["lot"]
        for mode in modes:  # le dernier mode (lot) laisse les données en place pour les lectures
            base.reinitialiser()
            base.preparer_mode(mode)

            def ecrire():
                n = 0
                if mode == "lot":
                    for lot in lots(lire_points(jeu)):
                        base.ecrire_lot(lot)
                        n += len(lot)
                else:
                    for p in lire_points(jeu):
                        base.ecrire_un(p)
                        n += 1
                base.fin_ecriture()
                return n
            res, n = mesurer(base, p_repos, f"écriture {mode} ({jeu})", ecrire)
            base.apres_ecriture()
            extra = {"taille_base_o": base.taille_octets()} if mode == "lot" else {}
            lignes.append(_ligne(base, jeu, "ecriture", mode, n, res, extra))

        for action, fn in (("lecture", lambda: base.lire_derniers(100)), ("agregation", base.moyenne_temp)):
            for i in range(REPETITIONS):
                res, r = mesurer(base, p_repos, f"{action} #{i + 1} ({jeu})", fn)
                resultat = f"{len(r)} lignes" if action == "lecture" else f"moy={r:.4f}"
                lignes.append(_ligne(base, jeu, action, "1er appel" if i == 0 else f"repetition {i}",
                                     n, res, {"resultat": resultat}))
        _enregistrer(lignes)


def main(base):
    ap = argparse.ArgumentParser()
    ap.add_argument("jeux", nargs="*", default=["small", "medium", "big"])
    bench(base, ap.parse_args().jeux)
