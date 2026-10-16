#!/usr/bin/env bash
# Generates traffic so Grafana panels and the HPA have something to show.
# Usage: URL=http://<ingress-host> ./scripts/load-test.sh [requests]
set -euo pipefail
URL="${URL:-http://localhost:8080}"
N="${1:-1000}"

for i in $(seq 1 "$N"); do
  curl -s "$URL/api/items" >/dev/null &
  curl -s "$URL/api/stats" >/dev/null &
  if (( i % 10 == 0 )); then
    curl -s -X POST "$URL/api/items/1/adjust" -H 'Content-Type: application/json' -d '{"delta": 1}' >/dev/null
    curl -s -X POST "$URL/api/items/1/adjust" -H 'Content-Type: application/json' -d '{"delta": -1}' >/dev/null
    curl -s "$URL/api/items/999999" >/dev/null
  fi
  (( i % 50 == 0 )) && wait && echo "$i / $N"
done
wait
echo "done"
