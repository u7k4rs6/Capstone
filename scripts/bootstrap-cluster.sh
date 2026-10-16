#!/usr/bin/env bash
# Installs the cluster add-ons the app depends on, then hands deployment over to ArgoCD.
# Run after `aws eks update-kubeconfig` (or against a kind cluster).
set -euo pipefail
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:?set GRAFANA_PASSWORD}"
DB_PASSWORD="${DB_PASSWORD:?set DB_PASSWORD}"

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

kubectl apply -f k8s/namespace.yaml -f k8s/storageclass-gp3.yaml

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace --wait
helm upgrade --install metrics-server metrics-server/metrics-server -n kube-system --wait
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/kube-prometheus-stack-values.yaml \
  --set grafana.adminPassword="$GRAFANA_PASSWORD" --wait
helm upgrade --install argocd argo/argo-cd -n argocd --create-namespace --wait

# DB password lives in the cluster, not in git. ArgoCD passes it to Helm as a parameter.
kubectl apply -f argocd/application.yaml
kubectl -n argocd patch application stockroom --type merge \
  -p "{\"spec\":{\"source\":{\"helm\":{\"parameters\":[{\"name\":\"postgres.password\",\"value\":\"$DB_PASSWORD\"}]}}}}"

echo
echo "ArgoCD admin password:"
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
echo "Ingress address:"
kubectl -n ingress-nginx get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].hostname}{.status.loadBalancer.ingress[0].ip}'; echo
