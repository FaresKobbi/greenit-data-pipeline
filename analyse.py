"""Quelles variables expliquent l'écart température ressentie - température réelle ?"""
import json
import pathlib
from statistics import correlation

h = json.loads((pathlib.Path(__file__).parent / "data" / "raw.json").read_text())["hourly"]
ecart = [a - t for a, t in zip(h["apparent_temperature"], h["temperature_2m"])]

print(f"Écart ressenti-réel : min {min(ecart):.1f}  max {max(ecart):.1f}  moy {sum(ecart)/len(ecart):.2f} °C\n")
skip = {"time", "apparent_temperature"}
scores = {k: correlation(v, ecart) for k, v in h.items()
          if k not in skip and len(set(v)) > 1}
for k, r in sorted(scores.items(), key=lambda kv: -abs(kv[1])):
    print(f"{k:28s} r = {r:+.3f}")
