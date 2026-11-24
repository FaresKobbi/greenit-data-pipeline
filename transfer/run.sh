#!/usr/bin/env bash
# Lance proxy + serveur HTTP + abonné MQTT, exécute les scénarios d'envoi, puis arrête tout.
# Prérequis : storing/infra (Mosquitto) lancé ; storing/monitoring pour Grafana (optionnel).
set -euo pipefail
cd "$(dirname "$0")"
PY="$(cd .. && pwd)/.venv/bin/python"  # chemin absolu, sans résoudre le lien du venv
LOGS=../results/transfer-logs
mkdir -p "$LOGS"

$PY -u proxy.py > "$LOGS/proxy.log" 2>&1 &
P1=$!
$PY -u http_server.py > "$LOGS/http_server.log" 2>&1 &
P2=$!
$PY -u mqtt_sub.py > "$LOGS/mqtt_sub.log" 2>&1 &
P3=$!
trap 'kill $P1 $P2 $P3 2>/dev/null' EXIT
sleep 2

$PY -u send.py
