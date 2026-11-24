"""Génère les 3 jeux de données du TD à partir des 4 416 heures réelles de Tunis.

Principe : N stations virtuelles autour de Tunis. La station 0 = données réelles ;
les autres = même série avec un décalage propre à la station (température, rosée, vent).
Ordre chronologique (toutes les stations pour une heure, puis l'heure suivante),
comme si les mesures arrivaient en temps réel.

    python3 gen_datasets.py [small medium big]

Colonnes : station,time(epoch s),temp,ressenti,rosee,vent
"""
import json
import pathlib
import random
import sys
from datetime import datetime, timedelta, timezone

ICI = pathlib.Path(__file__).parent
DATA = ICI / "data"
JEUX = {"small": 1, "medium": 113, "big": 11_323}  # x 4 416 h = 4 416 / 499 008 / 50 002 368
TZ_TUNIS = timezone(timedelta(hours=1))  # pas d'heure d'été en Tunisie

h = json.loads((DATA / "raw.json").read_text())["hourly"]
BASE = [(int(datetime.fromisoformat(t).replace(tzinfo=TZ_TUNIS).timestamp()), te, ap, ro, ve)
        for t, te, ap, ro, ve in zip(h["time"], h["temperature_2m"], h["apparent_temperature"],
                                     h["dew_point_2m"], h["wind_speed_10m"])]


def stations(n):
    out = []
    for s in range(n):
        rng = random.Random(s)
        dt, dr, fv = (0.0, 0.0, 1.0) if s == 0 else \
            (rng.uniform(-1.5, 1.5), rng.uniform(-1.0, 1.0), rng.uniform(0.8, 1.2))
        out.append((f"TUN-{s:05d}", dt, dr, fv))
    return out


def generer(nom):
    st = stations(JEUX[nom])
    chemin = DATA / f"{nom}.csv"
    with chemin.open("w", buffering=1 << 20) as f:
        f.write("station,time,temp,ressenti,rosee,vent\n")
        for t, te, ap, ro, ve in BASE:
            f.write("".join(f"{s},{t},{te + dt:.1f},{ap + dt:.1f},{ro + dr:.1f},{ve * fv:.1f}\n"
                            for s, dt, dr, fv in st))
    n = len(BASE) * len(st)
    print(f"{nom:6s} {len(st):6d} stations x {len(BASE)} h = {n:>11,d} points -> "
          f"{chemin} ({chemin.stat().st_size / 1e6:,.1f} Mo)")


if __name__ == "__main__":
    for nom in sys.argv[1:] or JEUX:
        generer(nom)
