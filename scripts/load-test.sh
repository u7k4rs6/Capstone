#!/usr/bin/env bash
# Generates traffic so Grafana panels and the HPA have something to show.
# Usage: ./scripts/load-test.sh [requests]
# Finds the ingress load balancer on its own. Falls back to the kind setup on localhost:8081.
set -euo pipefail
if [[ -z "${URL:-}" ]]; then
  LB=$(kubectl -n ingress-nginx get svc ingress-nginx-controller \
    -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
  URL="http://${LB:-localhost:8081}"
fi
echo "hitting $URL"
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
