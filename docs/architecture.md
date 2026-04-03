# Architecture Notes

## Runtime split

The repo follows the same separation your blueprint recommends:

- Cloudflare Pages + Functions handle the operator-facing dashboard, auth-adjacent edge concerns, caching headers, and thin API orchestration.
- Render handles the heavier Python workloads: inference-oriented API responses, scheduled data ingestion, candidate generation, and training or backtesting jobs.

## Decision-system shape

The starter uses the same core pattern you outlined:

1. ingest multi-modal data
2. generate candidate option structures
3. rank candidates with a learning-to-rank layer
4. apply hard risk gates before execution or display

That pattern shows up directly in the repo:

- `services/pipeline/pipeline/ingest.py` models data collection jobs.
- `services/pipeline/pipeline/features.py` turns strategy templates into candidate trades.
- `services/pipeline/pipeline/train.py` defines the baseline-plus-ranker training plan.
- `services/pipeline/pipeline/backtest.py` carries the execution and risk assumptions forward into evaluation.

## Edge BFF contract

The web app includes Cloudflare Pages Functions routes for:

- `/api/opportunities`
- `/api/trade/:id`
- `/api/risk`

Those routes can:

- proxy to the Render API when `API_ORIGIN` is configured
- return stable fallback payloads during UI-only development
- stamp entitlement and execution-mode headers at the edge

That gives you a clean place to add auth, rate limiting, caching, delayed-data policies, and per-user display entitlements later.

## Data and compliance boundaries

This repo assumes a conservative default:

- public or unauthenticated users see delayed analytics, not real-time quote redistribution
- market-data entitlements are enforced at the edge before payloads reach the browser
- execution remains in paper mode until broker connectivity, ODD delivery, audit trails, and risk controls are finished

## Suggested evolution path

### Phase 1

Swap mock payloads for licensed chain snapshots, official macro calendars, and a news pipeline that writes raw files plus metadata rows.

### Phase 2

Materialize a real candidate table keyed by trade ID, date, strategy, and risk footprint. Point both the API and dashboard at that shared store.

### Phase 3

Add model artifact storage, walk-forward reports, PBO/deflated-Sharpe outputs, and live API-backed explanations for why a trade is ranked.

### Phase 4

Only then add paper execution, broker-specific routing, and eventually opt-in live execution with hard portfolio kill switches.
