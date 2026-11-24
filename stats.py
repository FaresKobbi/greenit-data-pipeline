"""Fonctions réutilisables : moyennes des températures et comparaison à une référence."""

PAIRES = [("temp_max", "ressenti_max"), ("temp_min", "ressenti_min"), ("temp_moy", "ressenti_moy")]
METRIQUES = [m for p in PAIRES for m in p]


def moyennes(jours):
    """Moyenne de chaque métrique sur la liste de jours."""
    n = len(jours)
    return {m: sum(j[m] for j in jours) / n for m in METRIQUES}


def ecarts(moy):
    """Différence réel / ressenti, en valeur absolue (°C) et en %."""
    return {r: {"abs": moy[r] - moy[t], "pct": (moy[r] - moy[t]) / moy[t] * 100}
            for t, r in PAIRES}


def erreurs(ref, ech):
    """Erreur relative (%) de chaque métrique de l'échantillon par rapport à la référence."""
    return {m: abs(ech[m] - ref[m]) / abs(ref[m]) * 100 for m in METRIQUES}


def erreur_moyenne(ref, ech):
    e = erreurs(ref, ech)
    return sum(e.values()) / len(e)
