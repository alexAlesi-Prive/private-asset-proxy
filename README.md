# Privé Proxy-Asset Engine

Maps illiquid **private holdings** (private equity/debt/real-estate, funds, hedge
funds) onto **liquid instruments and/or factor exposures** so they can flow
through the same risk and portfolio analytics as listed positions.

**Build goal (`PROXY_GOAL`): risk / analytics representation** — estimate how a
private holding *behaves* (volatility, factor exposures, drawdown, contribution
to portfolio risk), **not** what it is *worth*. This build never produces a
valuation or fair-value mark. See [`docs/proxy-methodology.md`](docs/proxy-methodology.md).

The methodology is designed to be **explainable, auditable, and overridable** —
every proxy is a reviewable proposal with a recorded rationale, not a black box.

## Architecture

```
docs/                        Methodology, provenance, EPC data contract + gap analysis
engine/
  models/                    Canonical typed inputs (PrivateHolding, AssetClassType, BaselineAsset)
  adapters/                  HoldingSource port + EpcAdapter (the one place that knows EPC's shape)
  mapping/                   Metric-comparables proxy construction (config-driven, explainable)
  config/mappings.yaml       Versioned construction config (metrics, k, weighting, filters)
  data/                      Prototype baseline universe (50 traded assets) + generator
  store/                     File-backed store for user-added private holdings
  service/                   HTTP service: JSON API + serves the built SPA
  tests/                     Zero-dependency tests
frontend/                    React + Vite + TS + Tailwind client UI (4 tabs, scatter plots)
Dockerfile, docker-compose.yml, deploy.sh            Deployment (build on the server)
```

The engine depends only on PyYAML; the proxy math is stdlib. It has **no
dependency on `resource-temp/`** (reference-only, excluded from the image).

**Method in one line:** no fixed factor library — a private holding is placed in
a shared metric space (revenue, EBITDA, net income, margins…) and its proxy is a
weighted basket of the nearest **traded comparables**, fully explained.

### Build status
- **Phase 0 — methodology & provenance:** done (`docs/`).
- **Phase 1 — EPC data contract, typed model, adapter:** done.
- **Phase 2 — metric-comparables engine (config-driven, explainable, overridable):** done.
- **Phase 4 — client UI (add/list/scatter/baseline tabs):** done.
- **Phase 3 — validation harness (backtest/coverage report):** pending.

> Note on EPC: no live EPC endpoint was reachable during this build, so the data
> contract is derived from an available sample export and clearly labelled
> unconfirmed. Only the adapter's field-mapping table depends on EPC's real
> shape. See [`docs/epc-data-contract.md`](docs/epc-data-contract.md).

## Run locally (no Docker)

```bash
# 1. Engine API (also serves the built SPA if frontend/dist exists)
python3 -m engine.service                 # http://localhost:5530

# 2. Engine tests
python3 -m engine.tests.test_epc_adapter
python3 -m engine.tests.test_proxy_builder

# 3. Frontend dev server (hot reload; proxies /api to :5530)
cd frontend && npm install && npm run dev  # http://localhost:5173
#    …or build it so the engine serves it directly:
cd frontend && npm run build               # outputs frontend/dist
```

API: `GET /api/config`, `GET /api/baseline`, `GET/POST /api/private-assets`,
`POST /api/proxy/preview`, `GET /healthz`. Env: `PORT` (5530), `HOST`,
`WEB_DIR` (built SPA dir), `PRIVATE_ASSETS_FILE`.

## Deploy (Docker, built on the server)

The image is **built on the server from source** and tagged by the current git
commit — nothing is pulled from a container registry. `deploy.sh` wraps the
whole cycle:

```bash
cp .env.example .env    # first time only; defaults work as-is
./deploy.sh             # git pull, build, (re)start, show status
```

Under the hood that is just Docker Compose:

```bash
IMAGE_TAG=$(git rev-parse --short HEAD) docker compose up -d --build
docker compose ps        # expect: running (healthy)
```

Then open **http://localhost:5530** — the container serves the full UI and the
API on the same port. Health check: `curl http://localhost:5530/healthz`.

User-added holdings persist on the `psi-private-asset-proxy-data` volume
(mounted at `/app/var`), so they survive rebuilds. The compose file joins the
shared external `psi-net` network; create it once per host with
`docker network create psi-net` if it does not already exist.

### Build & run the image directly (no compose)

```bash
docker build -t psi/private-asset-proxy:local .
docker run -d --name prive-proxy-assets -p 5530:5530 psi/private-asset-proxy:local
```
