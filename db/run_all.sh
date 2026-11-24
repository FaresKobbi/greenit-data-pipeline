#!/usr/bin/env bash
# Lance tous les bancs d'essai bases de données (≈ 2 h), dans l'ordre, sur les 3 jeux.
# Résultats : results/db.csv (+ Pushgateway/Grafana). Journal : results/db.log
#   ./run_all.sh            tout
#   ./run_all.sh small      un seul jeu
set -uo pipefail
cd "$(dirname "$0")"
PY="$(cd .. && pwd)/.venv/bin/python"   # chemin absolu, sans résoudre le lien du venv
JEUX=("${@:-small medium big}")

$PY -u baseline.py ${JEUX[@]}
for b in "bench_postgres.py" "bench_mongo.py" "bench_influx.py" "bench_mongo.py --timeseries"; do
    $PY -u $b ${JEUX[@]} || echo "!!! échec : $b"
done
echo "=== terminé : $(date) ==="
