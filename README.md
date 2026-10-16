# StockRoom

A small inventory tracker for a cafe or shop: add items, bump stock up and down, and see what needs reordering before you run out.

The app itself is simple on purpose. The real point of this repo is the path it takes from a laptop to a monitored Kubernetes cluster on AWS: tests, containers, a security gate, Terraform, Helm, GitOps with ArgoCD, and Prometheus + Grafana.

![StockRoom UI](docs/screenshots/app.png)

## Architecture

```mermaid
flowchart LR
  dev[Developer] -->|git push| gh[GitHub]
  gh --> ci[GitHub Actions]
  ci -->|pytest, ruff, npm build| ci
  ci -->|docker build + Trivy| ghcr[(GHCR)]
  ci -->|bump image tag in values.yaml| gh
  gh -->|watched by| argo[ArgoCD]
  tf[Terraform] --> aws[AWS VPC + EKS]
  argo -->|helm sync| eks
  subgraph eks[EKS cluster]
    ing[ingress-nginx] -->|/| fe[frontend x2]
    ing -->|/api| be[backend x2..6 HPA]
    fe -->|/api proxy| be
    be --> pg[(Postgres StatefulSet)]
    prom[Prometheus] -->|scrape /metrics| be
    graf[Grafana] --> prom
  end
  ghcr -->|pull| eks
```

Request flow: browser hits the AWS load balancer, ingress-nginx sends `/api/*` to the FastAPI service and everything else to the Nginx frontend. Backend talks to Postgres. Prometheus scrapes the backend through a ServiceMonitor and Grafana reads from Prometheus.

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | React 19, Vite 8, plain CSS, Nginx (unprivileged) |
| Backend | Python 3.13, FastAPI, SQLAlchemy 2, Alembic, Pydantic |
| Database | PostgreSQL 17 |
| Testing | pytest (SQLite test DB), ruff |
| Containers | Docker, Docker Compose |
| CI/CD | GitHub Actions, GHCR |
| Security | Trivy image scanning |
| Infra | Terraform, AWS VPC, EKS, EBS CSI |
| Deploy | Kubernetes, Helm, ArgoCD, ingress-nginx, HPA, metrics-server |
| Observability | kube-prometheus-stack (Prometheus, Grafana), prometheus-fastapi-instrumentator |

## Repo layout

```text
backend/         FastAPI app, Alembic migrations, pytest tests
frontend/        React app, Nginx config template, multi-stage Dockerfile
docker-compose.yml
.github/workflows/ci-cd.yml
terraform/       VPC + EKS
helm/stockroom/  Helm chart (deployments, services, ingress, HPA, ServiceMonitor, Grafana dashboard)
argocd/          ArgoCD Application
k8s/             namespace + gp3 StorageClass
monitoring/      kube-prometheus-stack values
scripts/         cluster bootstrap, local kind setup, load test
troubleshooting/ deliberately broken manifests for debugging practice
demo/            slides + presentation video
```

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | liveness, no DB |
| GET | `/ready` | readiness, checks the DB |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/items` | list items (`?q=`, `?category=`, `?low_stock=true`) |
| GET | `/api/items/{id}` | one item |
| POST | `/api/items` | create (409 on duplicate SKU) |
| PUT | `/api/items/{id}` | update |
| DELETE | `/api/items/{id}` | delete |
| POST | `/api/items/{id}/adjust` | add or remove stock (`{"delta": -3}`), 400 if it would go negative |
| GET | `/api/stats` | totals, low stock, out of stock, stock value |

Swagger lives at `/docs` when the backend is running.

The DB schema is managed by Alembic (`backend/alembic/versions/`). `0001` creates the `items` table, `0002` seeds some demo stock. The backend container runs `alembic upgrade head` on start, wrapped in a Postgres advisory lock so multiple replicas don't migrate at the same time.

## Run it locally

You need Docker with Compose.

```bash
docker compose up --build
```

- App: http://localhost:3000
- API docs: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics

`docker compose down -v` stops everything and wipes the DB volume.

### Without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://stockroom:stockroom@localhost:5432/stockroom
alembic upgrade head
uvicorn app.main:app --reload

cd ../frontend
npm ci && npm run dev    # http://localhost:5173, proxies /api to :8000
```

## Tests

```bash
cd backend
pytest -v
```

12 tests covering health/ready, create (including validation and duplicate SKU), list + filters, get + 404, update, stock adjust, delete, stats and the metrics endpoint. `tests/conftest.py` points the app at a throwaway SQLite file before import, so tests never touch Postgres and each test starts with empty tables.

## Docker

- `backend/Dockerfile`: `python:3.13-slim`, installs deps, then removes pip (it's build-time only and its vendored libs were the only Trivy findings). Runs as uid 10001.
- `frontend/Dockerfile`: multi-stage. Stage 1 is `node:24-alpine` running `npm ci && npm run build`. Stage 2 is `nginxinc/nginx-unprivileged`, runs as uid 101 on port 8080. The Nginx config is a template, so `BACKEND_URL` decides where `/api` gets proxied. Same image works in Compose and Kubernetes.

## CI/CD

`.github/workflows/ci-cd.yml` runs on every push and PR to `main`.

1. **test**: ruff, `pytest -v`, then `npm ci && npm run build`. Any failure stops the pipeline, so no image gets built from broken code.
2. **build-scan-push** (matrix: backend, frontend): builds the image tagged with the commit SHA, scans it with Trivy, and pushes to `ghcr.io/<owner>/stockroom-<service>:<sha>`. PRs build and scan but don't push.
3. **deploy** (main only): rewrites the image tags in `helm/stockroom/values.yaml` to the new SHA and commits back with `[skip ci]`. ArgoCD sees the commit and rolls the cluster forward.

Tags are always the commit SHA, never `latest`, so any running pod can be traced back to the exact commit.

## Security (Trivy)

Trivy scans both final images for known CVEs in OS packages (Debian/Alpine) and language packages (the Python wheels in the backend). The pipeline fails on any HIGH or CRITICAL finding that has a fix available (`--ignore-unfixed`), so nothing with a patchable serious hole reaches GHCR.

The first scan of the backend flagged 4 HIGHs: CVE-2025-47273 (setuptools path traversal), two urllib3 CVEs and one in msgpack. All four were inside pip's own vendored copies, not in anything the app imports. Since pip isn't needed at runtime, the Dockerfile uninstalls it after installing deps, and both images now scan clean. The Trivy action is pinned to a commit SHA rather than a tag, since action tags can be moved.

## Terraform (AWS)

`terraform/` builds:

- VPC `10.20.0.0/16` across 2 AZs, with 2 public subnets (load balancers, NAT) and 2 private subnets (nodes), plus 1 NAT gateway
- EKS cluster (`stockroom-eks`, Kubernetes 1.35) with a managed node group of 2 x t3.large (scales 2 to 4)
- Add-ons: vpc-cni, coredns, kube-proxy, aws-ebs-csi-driver (nodes get the EBS CSI policy so the Postgres PVC can get a gp3 volume)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply                       # ~15 min
$(terraform output -raw configure_kubectl)
```

Default region is `ap-south-1`. No credentials live in the repo: use `aws configure` or env vars. `*.tfvars` and state files are gitignored.

## Kubernetes, Helm and ArgoCD

The Helm chart in `helm/stockroom` deploys:

- backend Deployment (2 replicas min, HPA up to 6 at 60% CPU) with readiness on `/ready`, liveness on `/health`, and an init container that waits for Postgres
- frontend Deployment (2 replicas)
- Postgres StatefulSet with a PVC
- ClusterIP Services for all three
- Ingress: `/api` to backend, `/` to frontend
- ServiceMonitor for Prometheus and a ConfigMap holding the Grafana dashboard

Everything runs as non-root with privilege escalation off.

### First deploy on EKS

1. `argocd/application.yaml` already points at this repo. Change `repoURL` if you fork it.
2. Make sure the GHCR packages are public (GitHub > your profile > Packages > package settings > visibility), or add an `imagePullSecrets` entry.
3. Run the bootstrap:

```bash
GRAFANA_PASSWORD=... DB_PASSWORD=... ./scripts/bootstrap-cluster.sh
```

That installs ingress-nginx, metrics-server, kube-prometheus-stack and ArgoCD, applies the namespace + gp3 StorageClass, then creates the ArgoCD Application. From then on ArgoCD owns the deploy. Push to main, CI bumps the tag, ArgoCD syncs.

Useful checks:

```bash
kubectl get pods,svc,ingress,hpa -n stockroom
helm list -A
kubectl -n argocd port-forward svc/argocd-server 8080:443     # https://localhost:8080, user admin
kubectl -n ingress-nginx get svc ingress-nginx-controller       # EXTERNAL-IP = app URL
```

You can also skip ArgoCD and deploy straight with Helm:

```bash
helm upgrade --install stockroom ./helm/stockroom -n stockroom --create-namespace \
  -f helm/stockroom/values-eks.yaml --set postgres.password=...
```

### Local rehearsal on kind

`./scripts/kind-up.sh` builds the images, creates a kind cluster and installs the same chart and monitoring stack. App ends up at http://localhost:8081. Good for practicing the demo without paying for EKS.

## Observability

- The backend exposes `/metrics` via prometheus-fastapi-instrumentator (request count, latency histograms by endpoint and status) plus a custom `stockroom_stock_movements_total{direction="in|out"}` counter.
- kube-prometheus-stack is installed with `monitoring/kube-prometheus-stack-values.yaml`, which tells Prometheus to pick up ServiceMonitors from every namespace and tells the Grafana sidecar to load dashboards from any ConfigMap labelled `grafana_dashboard: "1"`.
- The chart ships a **StockRoom API** dashboard: pods up, requests/sec, 5xx error rate, p95 latency, requests by endpoint, latency by endpoint, responses by status and stock movements.

```bash
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090   # Status > Target health
kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3001:80        # admin / $GRAFANA_PASSWORD
URL=http://<load-balancer-host> ./scripts/load-test.sh 1000                          # make the graphs move
```

| Prometheus targets | Grafana |
|---|---|
| ![targets](docs/screenshots/prometheus-targets.png) | ![grafana](docs/screenshots/grafana.png) |

## Troubleshooting lab

```bash
kubectl apply -f troubleshooting/broken-image.yaml     # ImagePullBackOff, find it with describe + events
kubectl apply -f troubleshooting/broken-service.yaml   # no endpoints, selector doesn't match any pod
```

Each file has the symptoms and fix in a comment at the top.

## Tear down

```bash
kubectl -n argocd delete application stockroom
helm uninstall ingress-nginx -n ingress-nginx     # removes the AWS load balancer
cd terraform && terraform destroy
```

Delete the load balancer first or `terraform destroy` can get stuck on the VPC.

## Known issues and limits

- Postgres runs in-cluster with one replica. Fine for a demo, but real prod should use RDS with backups and Multi-AZ.
- The DB password is a Helm value (set at bootstrap, not committed). A real setup would use External Secrets or AWS Secrets Manager.
- One NAT gateway to save money, so losing that AZ cuts outbound traffic from the private subnets.
- No TLS on the ingress. Adding cert-manager + a real domain would fix it.
- ingress-nginx is in maintenance mode upstream. It still works, but the AWS Load Balancer Controller or Gateway API would be the long-term pick.
- Terraform state is local. A team would use an S3 backend with locking.
- No auth on the app. Anyone who can reach the URL can edit stock.
