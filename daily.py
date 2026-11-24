"""raw.json (horaire) -> daily.json (1 ligne par jour), équivalent des données journalières du TD."""
import json
import pathlib
from collections import defaultdict

DATA = pathlib.Path(__file__).parent / "data"
h = json.loads((DATA / "raw.json").read_text())["hourly"]

par_jour = defaultdict(list)
for i, t in enumerate(h["time"]):
    par_jour[t[:10]].append(i)


def moy(v):
    return sum(v) / len(v)


jours = []
for date, idx in sorted(par_jour.items()):
    temp = [h["temperature_2m"][i] for i in idx]
    ress = [h["apparent_temperature"][i] for i in idx]
    jours.append({
        "date": date,
        "temp_max": max(temp), "temp_min": min(temp), "temp_moy": round(moy(temp), 2),
        "ressenti_max": max(ress), "ressenti_min": min(ress), "ressenti_moy": round(moy(ress), 2),
        # variables candidates pour la stratification
        "rosee_moy": round(moy([h["dew_point_2m"][i] for i in idx]), 2),
        "vent_moy": round(moy([h["wind_speed_10m"][i] for i in idx]), 2),
    })

(DATA / "daily.json").write_text(json.dumps(jours, separators=(",", ":")))
print(f"{len(jours)} jours -> {DATA / 'daily.json'}")
