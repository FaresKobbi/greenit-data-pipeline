"""Tableau comparatif à partir de results/db.csv -> results/db_tableau.md (+ affichage).

Lectures / agrégations : « 1er appel » et moyenne des répétitions suivantes (cache chaud).
"""
import csv
import pathlib
from collections import defaultdict
from statistics import mean

ICI = pathlib.Path(__file__).parent
lignes = list(csv.DictReader((ICI.parent / "results" / "db.csv").open()))
BASES = list(dict.fromkeys(l["base"] for l in lignes))
JEUX = [j for j in ("small", "medium", "big") if any(l["jeu"] == j for l in lignes)]

groupes = defaultdict(list)
for l in lignes:
    mode = l["mode"] if l["action"] == "ecriture" or l["mode"] == "1er appel" else "répétitions (moy)"
    groupes[(l["jeu"], l["action"], mode, l["base"])].append(l)


def f(v, unite=""):
    v = float(v)
    if unite == "o":
        for u in ("o", "Ko", "Mo", "Go"):
            if abs(v) < 1024 or u == "Go":
                return f"{v:.0f} {u}" if u == "o" else f"{v:.1f} {u}"
            v /= 1024
    return f"{v:.3g}" if abs(v) < 1000 else f"{v:,.0f}".replace(",", " ")


def cellule(g, champ, unite=""):
    if not g:
        return "–"
    return f(mean(float(x[champ]) for x in g), unite)


ACTIONS = [("ecriture", "Écriture"), ("lecture", "Lecture 100 derniers"), ("agregation", "Moyenne temp")]
METRIQUES = [("duree_s", "Durée (s)", ""), ("energie_nette_J", "Énergie nette (J)", ""),
             ("cpu_base_s", "CPU base (s)", ""), ("io_ecriture_o", "Écrit disque", "o")]

sortie = ["# Comparatif bases de données\n"]
for jeu in JEUX:
    n = next(l["points"] for l in lignes if l["jeu"] == jeu)
    sortie.append(f"\n## Jeu {jeu} ({int(n):,d} points)\n".replace(",", " "))
    for champ, titre, unite in METRIQUES:
        sortie.append(f"\n**{titre}**\n\n| Action | Mode | " + " | ".join(BASES) + " |")
        sortie.append("|---|---|" + "---|" * len(BASES))
        for action, nom in ACTIONS:
            modes = list(dict.fromkeys(m for (j, a, m, b) in groupes if j == jeu and a == action))
            for mode in modes:
                sortie.append(f"| {nom} | {mode} | " + " | ".join(
                    cellule(groupes.get((jeu, action, mode, b)), champ, unite) for b in BASES) + " |")
    sortie.append("\n**Débit d'écriture (points/s) et taille sur disque**\n\n| | " + " | ".join(BASES) + " |")
    sortie.append("|---|" + "---|" * len(BASES))
    modes = list(dict.fromkeys(m for (j, a, m, b) in groupes if j == jeu and a == "ecriture"))
    for mode in modes:
        sortie.append(f"| débit {mode} | " + " | ".join(
            cellule(groupes.get((jeu, "ecriture", mode, b)), "debit_pts_s") for b in BASES) + " |")
    sortie.append("| taille données | " + " | ".join(
        cellule(groupes.get((jeu, "ecriture", "lot", b)), "taille_base_o", "o") for b in BASES) + " |")

texte = "\n".join(sortie) + "\n"
(ICI.parent / "results" / "db_tableau.md").write_text(texte)
print(texte)
