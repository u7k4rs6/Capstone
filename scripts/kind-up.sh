#!/usr/bin/env bash
# Local rehearsal on kind: same chart, same monitoring, no AWS bill.
# App ends up at http://stockroom.local:8081 (add "127.0.0.1 stockroom.local" to /etc/hosts) or http://localhost:8081
set -euo pipefail
cd "$(dirname "$0")/.."
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-admin}"

cat <<'KIND' | kind create cluster --name stockroom --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    labels:
      ingress-ready: "true"
    extraPortMappings:
      - {containerPort: 80, hostPort: 8081}
KIND

docker build -t stockroom-backend:local ./backend
docker build -t stockroom-frontend:local ./frontend
kind load docker-image stockroom-backend:local stockroom-frontend:local --name stockroom

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace \
  --set controller.hostPort.enabled=true --set controller.service.type=ClusterIP \
  --set-string controller.nodeSelector.ingress-ready=true --wait
helm upgrade --install metrics-server metrics-server/metrics-server -n kube-system \
  --set args={--kubelet-insecure-tls} --wait
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/kube-prometheus-stack-values.yaml \
  --set grafana.adminPassword="$GRAFANA_PASSWORD" --wait

kubectl apply -f k8s/namespace.yaml
helm upgrade --install stockroom ./helm/stockroom -n stockroom \
  --set backend.image.repository=stockroom-backend --set backend.image.tag=local \
  --set frontend.image.repository=stockroom-frontend --set frontend.image.tag=local \
  --set ingress.host="" --set postgres.password=kind-local --wait

kubectl -n stockroom get pods,svc,ingress,hpa
echo "App:     http://localhost:8081"
echo "Grafana: kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3001:80  (admin / $GRAFANA_PASSWORD)"
