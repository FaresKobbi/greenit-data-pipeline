"""Référence : coût de la seule lecture du CSV (incluse dans tous les temps d'écriture des bases)."""
import sys
import time

from common import lire_points, lots
from measure import Mesure, puissance_repos

p = puissance_repos()
for jeu in sys.argv[1:] or ["small", "medium", "big"]:
    for mode in ("unitaire", "lot"):
        with Mesure(None, p) as m:
            n = sum(1 for _ in lire_points(jeu)) if mode == "unitaire" else \
                sum(len(lot) for lot in lots(lire_points(jeu)))
        print(f"lecture CSV {jeu:6s} {mode:8s} {n:>11,d} pts  {m.res['duree_s']:8.2f} s  "
              f"{m.res.get('energie_nette_J', float('nan')):8.1f} J", flush=True)
        time.sleep(1)
