# Web Dashboard — monitoring UI (ADR-0005)

## Problem statement

DecoyTell's outputs live in CLI tables, JSON files, and Postgres — powerful but not
easy to monitor. The operator needs a dashboard: one glance at scenario verdicts, the
live loop's real-vs-decoy observations, drift/fingerprint tracking (the 10 pairwise
joint checks), and corrections with their reasoning — documented as the process runs.

## What we built

| Piece | Responsibility |
|---|---|
| `decoytell/api.py` | FastAPI web layer: status, scenarios, scenario report, pair matrix, observations, loop events (paged tail), loop start/stop (control row), verify-now (one-shot cycle). Serves the built UI statically |
| `decoytell/store.py` (extended) | `loop_events` table (persisted cycles: probes, verdict, fixes) + `loop_control` row (running flag) |
| `loop_service.py` | Standalone loop process (ADR-0005): persists every cycle, polls the control row, stops cleanly when flipped |
| `web/` | Vite + React + TypeScript + Tailwind v4 + shadcn/ui: Dashboard, Scenarios, Live loop, Pair matrix, Observations views; 3s polling hook |
| `requirements-web.txt` | fastapi + uvicorn (web-layer deps, per the ADR-0003 v2 carve-out) |
| `Dockerfile.api` + compose `api` service | Everything containerized: one image serves API + built UI |

**Test count: 58** — including 9 API tests through the FastAPI TestClient seam and
loop-event/control store tests, all DSN-guarded and isolated from demo rows.

## How it works (layman)

A browser dashboard shows: every scenario's verdict at a glance; each decoy's five
attributes against the real window; the 10 pairwise checks with the fingerprint
highlighted; the live loop's per-cycle view of what the real server and the decoy
reported side by side, with the fixes the robot applied and why; and the observation
streams. Buttons start/stop the loop and trigger a one-shot verification. The UI never
talks to the engine directly — it reads the API, which reads Postgres; the loop keeps
running independently (ADR-0005), so the dashboard survives and so does the loop.

## Design intent

- **Loop-as-service with Postgres control** (ADR-0005): the robust choice — loop
  survives API restarts, API survives loop crashes, single source of truth.
- **Persisted loop events**: the "real vs decoy logs" view is a query over the event
  table, not a live connection to a dying process.
- **Reused everything**: scenario reports and pair matrices come from the existing
  `run_scenario` seam; the verify-now endpoint is one `run_loop` cycle. Nothing in the
  engine changed.
- **Tailwind via `@tailwindcss/postcss`**: the `@tailwindcss/vite` plugin hit a known
  rolldown (Vite 7) incompatibility; the official PostCSS route builds cleanly.

## Alternatives considered and rejected

| Alternative | Why rejected |
|---|---|
| Thread inside the API for the loop | Dies with the API; couples monitoring availability to loop health (ADR-0005 decision) |
| Subprocess managed by FastAPI | Process lifecycle/zombie plumbing for no benefit over the control row |
| SSE/WebSocket streaming | Polling (3s) is simpler and robust enough for v1 |
| Raw CLI logs only | The whole point of the ticket is monitoring + documentation in a UI |

## How to check

```
python verify_live.py                       # backend stack green
pip install -r requirements-web.txt
python loop_service.py &                    # loop process (waits for control)
python -m uvicorn decoytell.api:app --port 8000
cd web && npm install && npm run build
# open http://localhost:8000 — Dashboard -> Start loop -> Live loop tab
# or fully containerized:
docker compose up -d --build                # http://localhost:8000
python -m unittest discover tests           # 58 tests (with DECOYTELL_TEST_DSN)
```

## Status

✅ Implemented, tested (58 green + UI build), verified live (loop start/stop via API,
events persisted, verify-now PASS), committed + pushed on `main`.