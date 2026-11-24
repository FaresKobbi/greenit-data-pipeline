"""Benchmark gzip / zstd / lz4 (plusieurs niveaux) : taux de compression, temps, énergie.

Énergie : compteur RAPL du package CPU (/sys/class/powercap/intel-rapl:0/energy_uj).
Il faut le rendre lisible (jusqu'au prochain reboot) :
    sudo chmod o+r /sys/class/powercap/intel-rapl:0/energy_uj
Sinon les colonnes énergie restent vides.

L'énergie "nette" retire la conso au repos (mesurée au début) : E_net = E - P_repos * t.

Usage : python3 compress.py [fichier ...]   (défaut : data/daily.json data/raw.json data/big.json)
"""
import csv
import pathlib
import subprocess
import sys
import tempfile
import time

from push import annoter, pousser

ICI = pathlib.Path(__file__).parent
RAPL = pathlib.Path("/sys/class/powercap/intel-rapl:0")

# (outil, niveau, commande de compression, commande de décompression)
OUTILS = [
    ("gzip", "1", ["gzip", "-1", "-c"], ["gzip", "-dc"]),
    ("gzip", "6", ["gzip", "-6", "-c"], ["gzip", "-dc"]),
    ("gzip", "9", ["gzip", "-9", "-c"], ["gzip", "-dc"]),
    ("zstd", "1", ["zstd", "-1", "-c", "-q"], ["zstd", "-dc", "-q"]),
    ("zstd", "3", ["zstd", "-3", "-c", "-q"], ["zstd", "-dc", "-q"]),
    ("zstd", "19", ["zstd", "-19", "-c", "-q"], ["zstd", "-dc", "-q"]),
    ("zstd", "22", ["zstd", "--ultra", "-22", "-c", "-q"], ["zstd", "-dc", "-q"]),
    ("zstd", "3 --long", ["zstd", "-3", "--long=27", "-c", "-q"], ["zstd", "-dc", "-q", "--long=27"]),
    ("lz4", "1", ["lz4", "-1", "-c", "-q"], ["lz4", "-dc", "-q"]),
    ("lz4", "9", ["lz4", "-9", "-c", "-q"], ["lz4", "-dc", "-q"]),
    ("lz4", "12", ["lz4", "-12", "-c", "-q"], ["lz4", "-dc", "-q"]),
]


def lire_uj():
    try:
        return int((RAPL / "energy_uj").read_text())
    except (PermissionError, FileNotFoundError):
        return None


try:
    MAX_UJ = int((RAPL / "max_energy_range_uj").read_text())
except (PermissionError, FileNotFoundError):
    MAX_UJ = 2 ** 32


def mesurer(fn, reps):
    """Exécute fn() reps fois ; renvoie (temps moyen s, énergie moyenne J ou None)."""
    e0, t0 = lire_uj(), time.perf_counter()
    for _ in range(reps):
        fn()
    dt = (time.perf_counter() - t0) / reps
    e1 = lire_uj()
    e = None if e0 is None or e1 is None else ((e1 - e0) % MAX_UJ) / 1e6 / reps
    return dt, e


def lancer(cmd, src, dst):
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        subprocess.run(cmd, stdin=fi, stdout=fo, check=True)


def creer_gros_fichier(cible, base, taille_mo=300):
    """Duplique `base` jusqu'à ~taille_mo Mo (cf. énoncé)."""
    if cible.exists():
        return
    contenu = base.read_bytes()
    with cible.open("wb") as f:
        for _ in range(taille_mo * 1024 * 1024 // len(contenu) + 1):
            f.write(contenu)


def main():
    fichiers = [pathlib.Path(a) for a in sys.argv[1:]] or \
        [ICI / "data" / n for n in ("daily.json", "raw.json", "big.json")]
    if ICI / "data" / "big.json" in fichiers:
        creer_gros_fichier(ICI / "data" / "big.json", ICI / "data" / "raw.json")

    # puissance au repos
    _, e_repos = mesurer(lambda: time.sleep(3), 1)
    p_repos = e_repos / 3 if e_repos is not None else None
    print(f"Puissance package au repos : {p_repos:.2f} W" if p_repos else
          "RAPL illisible : pas de mesure d'énergie (voir docstring)")

    lignes = []
    with tempfile.TemporaryDirectory() as tmp:
        comp, decomp = pathlib.Path(tmp, "c"), pathlib.Path(tmp, "d")
        for src in fichiers:
            taille = src.stat().st_size
            reps = 20 if taille < 10_000_000 else 1  # petits fichiers : on répète pour sortir du bruit
            print(f"\n== {src.name} ({taille / 1e6:.2f} Mo, {reps} répétition(s)) ==")
            print(f"{'outil':6s} {'niv':9s} {'taille':>11s} {'gain %':>7s} {'t comp':>8s} {'t décomp':>9s} "
                  f"{'E net J':>8s} {'gain/s':>9s} {'gain/J':>8s}")
            for outil, niv, c_cmd, d_cmd in OUTILS:
                debut = time.time()
                t, e = mesurer(lambda: lancer(c_cmd, src, comp), reps)
                annoter(debut, time.time(), f"{outil} -{niv} ({src.name})", ["compression", outil])
                t_d, _ = mesurer(lambda: lancer(d_cmd, comp, decomp), reps)
                assert decomp.stat().st_size == taille, f"{outil} {niv}: décompression incorrecte"
                t_c = comp.stat().st_size
                gain = (1 - t_c / taille) * 100
                e_net = None if e is None else max(e - p_repos * t, 1e-9)
                l = {"fichier": src.name, "taille_orig_o": taille, "outil": outil, "niveau": niv,
                     "taille_comp_o": t_c, "gain_pct": round(gain, 3),
                     "temps_comp_s": round(t, 5), "temps_decomp_s": round(t_d, 5),
                     "energie_J": None if e is None else round(e, 4),
                     "energie_nette_J": None if e_net is None else round(e_net, 4),
                     "gain_par_s": round(gain / t, 1),
                     "gain_par_J": None if e_net is None else round(gain / e_net, 1)}
                lignes.append(l)
                pousser("compression", {"fichier": src.name, "outil": outil, "niveau": niv}, {
                    "td_compression_taille_octets": t_c,
                    "td_compression_gain_pct": l["gain_pct"],
                    "td_compression_temps_s": l["temps_comp_s"],
                    "td_decompression_temps_s": l["temps_decomp_s"],
                    "td_compression_energie_nette_joules": l["energie_nette_J"],
                })
                print(f"{outil:6s} {niv:9s} {t_c:11d} {gain:7.2f} {t:8.3f} {t_d:9.3f} "
                      f"{'-' if e_net is None else f'{e_net:8.3f}':>8s} {l['gain_par_s']:9.1f} "
                      f"{'-' if l['gain_par_J'] is None else l['gain_par_J']:>8}")

    out = ICI / "results" / "compression.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=lignes[0].keys())
        w.writeheader()
        w.writerows(lignes)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
