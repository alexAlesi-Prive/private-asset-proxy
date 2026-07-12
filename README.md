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
Dockerfile, docker-compose.yml, .github/workflows/  Deployment
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

## Deploy (Docker via GHCR)

Images are published to GitHub Container Registry by
[`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml).
Pushing to `main` (or running the workflow manually) produces the `:main` tag.

```bash
docker pull ghcr.io/alexAlesi-Prive/prive-proxy-assets:main

docker run -d --name prive-proxy-assets --restart unless-stopped -p 5530:5530 \
  ghcr.io/alexAlesi-Prive/prive-proxy-assets:main
```

Then open **http://localhost:5530** — the container serves the full UI and the
API on the same port. Health check: `curl http://localhost:5530/healthz`.

Or with compose: `docker compose up -d`.

### Build & run the image locally

```bash
docker build -t prive-proxy-assets:local .
docker run -d --name prive-proxy-assets -p 5530:5530 prive-proxy-assets:local
```

### First-time GHCR notes
- The workflow authenticates with the built-in `GITHUB_TOKEN` (needs
  `packages: write`, already set in the workflow).
- A newly published GHCR package is **private by default**. To `docker pull`
  without authenticating, set the package visibility to **Public** in
  GitHub → your profile → Packages → `prive-proxy-assets` → Package settings.
  Otherwise run `docker login ghcr.io` with a token that has `read:packages`.
- The package links to this repo automatically via the image's
  `org.opencontainers.image.source` label.
