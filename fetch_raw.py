"""Récupère 6 mois de données météo horaires brutes pour Tunis (Open-Meteo archive API).

On télécharge volontairement beaucoup de variables : c'est le jeu "brut" que l'on
nettoiera ensuite (clean.py) pour comparer tailles et coûts.
"""
import json
import pathlib
import sys
import time

import requests

LAT, LON = 36.806389, 10.181667  # Tunis
START, END = "2026-05-01", "2026-10-31"  # 6 mois complets

VARS = [
    "temperature_2m", "apparent_temperature", "relative_humidity_2m", "dew_point_2m",
    "precipitation", "rain", "snowfall", "weather_code", "pressure_msl", "surface_pressure",
    "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high",
    "wind_speed_10m", "wind_speed_100m", "wind_direction_10m", "wind_direction_100m",
    "wind_gusts_10m", "shortwave_radiation", "direct_radiation", "diffuse_radiation",
    "vapour_pressure_deficit", "sunshine_duration", "is_day",
]

out = pathlib.Path(__file__).parent / "data" / "raw.json"
out.parent.mkdir(exist_ok=True)

params = {
    "latitude": LAT, "longitude": LON,
    "start_date": START, "end_date": END,
    "hourly": ",".join(VARS),
    "timezone": "Africa/Tunis",
}

t0 = time.perf_counter()
r = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params, timeout=60)
r.raise_for_status()
data = r.json()
out.write_text(json.dumps(data, indent=2))  # indenté, comme un export "naïf"
dt = time.perf_counter() - t0

n = len(data["hourly"]["time"])
print(f"{n} heures x {len(VARS)} variables -> {out} ({out.stat().st_size / 1024:.1f} Ko) en {dt:.2f}s",
      file=sys.stderr)
