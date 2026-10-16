# Demo video script

Target: 10 to 12 minutes. Record the screen with OBS or the built-in recorder, export as MP4, save it here as `demo/presentation.mp4`.

If the MP4 is over 100 MB, GitHub will reject the push. Either compress it (`ffmpeg -i in.mp4 -vcodec libx264 -crf 28 demo/presentation.mp4`) or attach it to a GitHub Release and link it below.

## Before you hit record

```bash
cd terraform && terraform apply                 # ~15 min, do this first
$(terraform output -raw configure_kubectl)
cd .. && GRAFANA_PASSWORD=... DB_PASSWORD=... ./scripts/bootstrap-cluster.sh
kubectl -n argocd get application stockroom     # wait for Synced / Healthy
```

Open these tabs ahead of time:

- GitHub repo + Actions tab
- AWS Console: VPC page and EKS page (region ap-south-1)
- ArgoCD: `kubectl -n argocd port-forward svc/argocd-server 8080:443` then https://localhost:8080
- Prometheus: `kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090` then http://localhost:9090/targets
- Grafana: `kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3001:80` then the StockRoom API dashboard
- The app via the load balancer hostname

## 1. Slides (2 to 3 min)

Go through `StockRoom-Capstone.pptx`. Speaker notes are in the deck.

## 2. Codebase (1.5 min)

Show the folder tree, then quickly open:

- `backend/app/main.py`: routes, `/health`, `/ready`, `/metrics`
- `backend/tests/test_api.py` and run `pytest -v`
- `frontend/Dockerfile`: multi-stage, non-root Nginx
- `helm/stockroom/templates/backend.yaml`: probes, init container

## 3. CI/CD (2 min)

Make a small visible change, for example the subtitle in `frontend/src/App.jsx`, then:

```bash
git commit -am "Tweak dashboard subtitle"
git push
```

In Actions, show the run: test, then both build/scan/push jobs (open the Trivy step output), then deploy. Show the `deploy: stockroom <sha> [skip ci]` commit it creates and the new SHA tag on the GHCR package page.

## 4. Terraform (1.5 min)

```bash
cd terraform && terraform plan      # should say no changes, infra already matches
```

Then in the AWS Console show the VPC with its 4 subnets and the EKS cluster with its node group.

## 5. ArgoCD (1 min)

Show the `stockroom` app Synced and Healthy, the resource tree, and that it picked up the new commit from step 3. Then refresh the app in the browser and show your change is live.

## 6. Kubernetes (1 min)

```bash
kubectl get pods -n stockroom
kubectl get svc,ingress,hpa -n stockroom
helm list -A
```

## 7. Prometheus (30 sec)

Targets page, filter to `stockroom-backend`, show all UP.

## 8. Grafana (1 min)

Run the load test in a terminal and let the dashboard move:

```bash
URL=http://<load-balancer-host> ./scripts/load-test.sh 1500
```

Point out requests/sec, p95 latency, error rate, stock movements. Optional: `kubectl get hpa -n stockroom -w` to show it scaling.

## Wrap up

`terraform destroy` after recording (see README "Tear down"), and take the destroy screenshot.

## Screenshots the rubric asks for

Save these into `docs/screenshots/` while you record:

- [ ] app in the browser via the load balancer
- [ ] `pytest -v` all passing
- [ ] `docker compose up --build` running + http://localhost:3000
- [ ] commit history (10+ commits)
- [ ] green Actions run
- [ ] GHCR packages with SHA tags
- [ ] Trivy step output
- [ ] `terraform plan` output
- [ ] AWS Console VPC + EKS
- [ ] `terraform destroy` complete
- [ ] `kubectl get pods`, `kubectl get svc`, `helm list`
- [ ] `curl <backend>/metrics`
- [ ] Prometheus targets UP
- [ ] Grafana dashboard
