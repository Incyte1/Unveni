# Unveni

Unveni is a starter monorepo for an AI-driven options trading assistant built around the architecture in your blueprint: Cloudflare Pages at the edge, Render for heavier API and batch workloads, and a ranking-first decision system that can evolve from mock data into licensed market-data and model pipelines.

This repository is intentionally a foundation, not a live trading system. It ships with mock opportunity, risk, and backtest data so the UI contract, API shape, and pipeline structure are in place before you attach OPRA-licensed data, broker connectivity, or production compliance controls.

## What is here

- `apps/web`: React dashboard for a Cloudflare Pages deployment, plus Pages Functions routes that act as an edge BFF and can proxy to the Render API.
- `services/api`: FastAPI service for opportunities, trade detail, risk, and health endpoints.
- `services/pipeline`: ingestion, candidate-generation, training, and backtest planning scaffold with a simple CLI.
- `render.yaml`: Render Blueprint for the API, worker, cron job, and Postgres.
- `docs/architecture.md`: how the pieces map back to the Seero-style options-assistant design.

## Local development

### Web

```bash
npm install
npm run dev:web
```

The dashboard runs from local mock data by default. To have Cloudflare Pages Functions proxy to the API during `wrangler pages dev`, copy `apps/web/.dev.vars.example` to `.dev.vars` and set `API_ORIGIN`.

### API

```bash
cd services/api
python -m pip install -e .[dev]
uvicorn app.main:app --reload
```

### Pipeline

```bash
cd services/pipeline
python -m pip install -e .
python -m pipeline plan
```

## Deploy shape

- Cloudflare Pages serves the dashboard and the `/api/*` edge routes.
- Render hosts the main FastAPI service and the longer-running worker and cron workloads.
- The Pages Functions layer can return local fallbacks or proxy to the Render API via `API_ORIGIN`.
- Postgres is provisioned in Render by `render.yaml`.

## Production hardening next

1. Replace mock providers in `services/pipeline` with licensed options, macro, and news ingestion modules.
2. Persist candidate tables, model artifacts, and backtest outputs instead of returning in-memory samples.
3. Move the React app from static mocks to live fetches against `/api/opportunities`, `/api/trade/:id`, and `/api/risk`.
4. Add entitlement-aware display rules and audit logging before any real-time options data is exposed.
5. Add broker integration only after paper-trading controls, disclosures, and kill switches are in place.
