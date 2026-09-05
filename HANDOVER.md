# DecoyTell — Session Handover

**Repo**: `C:\Users\91999\OneDrive\Desktop\final\FinalDay_myonsite_86_DecoyTell`
**GitHub**: https://github.com/shrey2522/FinalDay_myonsite_86_DecoyTell
**Branch**: `main` (clean, all committed). Last commit `b49fcaa`. 20 commits.
**Date**: 2026-09-05.

---

## What this project is

**DecoyTell — Bounded Deception-Surface Consistency Verification.** A tool that checks
whether a fake/decoy server convincingly resembles a real server across a **fixed,
declared set of 5 observable attributes**, catches drift **individually and jointly**,
auto-corrects the drifted attribute, and certifies whether the decoy is safe to expose.

The 5 attributes: `service_banner`, `patch_cadence_days`, `timing_band`,
`account_age_days`, `monitoring_behavior`.

---

## What's built (complete and working)

Three layers, all on `main`:

### 1. Core engine (T1–T5) — pure Python stdlib, no DB, offline
`decoytell/` : `schema.py` (declared surface + thresholds), `generator.py` (seeded
real-asset history synthesis), `engine.py` (the seam `run_scenario(config) -> report`
and `verify(history, decoy)`), `corrector.py` (scoped conditional-mode correction),
`report.py` (CLI table + JSON proof), `validate.py`.
- Verdicts: `PASS` / `CORRECTED` / `UNSAFE` / `INSUFFICIENT_DATA`.
- `demo.py` runs scenarios s1–s5 (harmless / single-drift / pair-fingerprint /
  uncorrectable / insufficient-data), exit codes 0/1/2, JSON proof to `out/`.
- `observe_demo.py` — simulated continuous-observation loop.
- Docs: `CONTEXT.md`, `docs/adr/0001–0004`, `summary/01–05`.

### 2. Live integration layer (Live T1–T3) — real containers + Postgres + loop
- `decoytell/probe.py` — real collector (banner grab, version→cadence map, latency
  band, TLS-cert `notBefore` → account age, 6-probe scan burst → monitoring).
- `decoytell/store.py` — PostgreSQL store (`seed`/`append`/`recent_window`), plus
  `loop_events` + `loop_control` tables (for the dashboard).
- `decoytell/live.py` — `run_loop(...)` (probe→append→verify→apply fixes→re-probe→
  re-verify→persist event), `map_fix_to_identity`.
- `decoytell/control.py` — management-plane client (`POST /admin/identity`).
- `containers/identity/` — engineered HTTPS identity server; Dockerfile generates a
  **backdated self-signed cert** via `openssl ca -startdate`.
- `docker-compose.yml` — services: `real-asset`, `decoy`, `postgres`, `api`, `loop`.
- `collect_live.py`, `loop_service.py` (standalone loop process), `live_demo.py`,
  `demo_prep.py` (reset+seed+re-break decoy in one command), `verify_live.py`
  (end-to-end integration check).
- ADR-0003 v2 (stdlib carve-out), `summary/06`.

### 3. Web dashboard (ADR-0005)
- `decoytell/api.py` — FastAPI: `/api/status`, `/api/scenarios`, `/api/scenarios/{id}`,
  `/api/pairs`, `/api/observations`, `/api/loop/events`, `/api/loop/start`,
  `/api/loop/stop`, `/api/verify`. Serves the built UI at `/`.
- `web/` — Vite + React + TypeScript + Tailwind v4 + shadcn/ui: views **Dashboard**,
  **Scenarios**, **Live loop**, **Pair matrix** (the "10 possible drifts"),
  **Observations**. 3s polling (`usePolling` hook). Components in `web/src/components/ui/`.
- `loop_service.py` — standalone loop process; persists cycles to `loop_events`, polls
  `loop_control`. **Robustness (ADR-0005): the loop survives API restarts and vice versa.**
- ADR-0005, `requirements-web.txt` (fastapi/uvicorn), `Dockerfile.api`, `summary/07`.

---

## Tests

`python -m unittest discover tests` → **58 tests**, `OK` (with
`DECOYTELL_TEST_DSN=postgres://decoytell:decoytell@localhost:5433/decoytell`).
Store/API tests **skip cleanly without the DSN** (core suite runs dependency-free).
Live integration: `python verify_live.py` → `ALL LIVE CHECKS PASSED`.

---

## Environment / tools

- Python 3.12.4, Node v22.21.0, npm 11, Docker (Desktop, daemon must be running),
  `gh` CLI (auth'd as `shrey2522`), psycopg + fastapi + uvicorn installed.
- Tailwind via `@tailwindcss/postcss` (the `@tailwindcss/vite` plugin hit a known
  Vite 7/rolldown incompatibility — do **not** switch back).
- Ports: postgres `5433`, real-asset `8443`, decoy `8444`, api `8000`.

---

## How to run the demo (judge-ready)

```
docker compose up -d --build      # starts all 5 services
# open http://localhost:8000
python demo_prep.py               # resets store, seeds 1400 mock obs, re-breaks the decoy
# UI: click "Start loop" -> watch Live loop tab:
#   cycle 1 CORRECTED->PASS (banner 2.4.55->2.4.54, timing slow->fast),
#   cycles 2+ PASS->PASS; Observations tab shows BOTH real-asset and decoy streams
```

**Demo prep** = `demo_prep.py` (one command). **Verification** = `verify_live.py`.

---

## What the user was working on when this session ended

They were confused that the **Observations** view showed ~50 identical rows
(`days ago 0, Apache/2.4.54, cadence 60, fast, age 800.1, immediate`) for both
`real-asset` and `decoy`. **This is correct, not a bug:**

- The loop appends one observation per cycle with `days_ago = 0` (just observed). The
  real server is stable, so every live probe is identical.
- The UI does `rows.slice(-50)` = the **last 50** = the newest = the loop's live probes
  → all `days_ago 0` and identical.
- The varied seeded history IS in the DB: `1528` real-asset rows, `3` distinct banners,
  patch cadence `1.1–438.7`, account age `785–844.9`, `3` timing bands, oldest rows from
  2024-09-06 (730 days ago).

**Open decision offered to the user (not yet done):** improve the Observations view —
add a timestamp column + sort control (newest/oldest), or sample across the window, so
the seeded variety is visible to judges. Also offered: a `--rebreak-every N` loop flag
so the Live loop continuously shows `PASS → CORRECTED → PASS …` for longer demos.

---

## Known notes / gotchas

- The `loop` container shows `Restarting` when the loop is stopped (control row
  `running=false`): the loop process exits cleanly and `restart: unless-stopped`
  restarts it into "waiting for control". **Expected.** Click "Start loop" to make it
  cycle; `demo_prep.py` sets control back to stopped.
- `loop_service.py` / `live_demo.py` now read `DECOYTELL_REAL_HOST`/`_PORT` etc. env
  vars (a bug was fixed where they defaulted to `localhost` inside the container,
  causing `UNREACHABLE`).
- `loop_control` is a single row (`id=1`) shared by the demo, the loop, and tests;
  store tests save/restore it.
- Store tests are isolated via `test-` prefixed targets + baseline loop-event id, so
  they never wipe demo data.

---

## Next steps / ideas (priority order)

1. **Observations view clarity** — timestamp + sort control (user's active question).
2. **`--rebreak-every N`** flag for a self-demonstrating loop demo.
3. Close GitHub tickets #2–#6 (and #8–#10) as done if desired.
4. Optional: seed the store via an init SQL volume instead of `demo_prep.py`.

---

## Key commands reference

```
python demo.py                    # core scenarios
python observe_demo.py            # simulated continuous loop
docker compose up -d --build      # full stack
python demo_prep.py               # reset+seed+rebreak decoy
python verify_live.py             # integration check
python -m unittest discover tests # 58 tests (set DECOYTELL_TEST_DSN for store/api)
cd web && npm run build           # rebuild the UI
python loop_service.py            # run the loop process standalone
python -m uvicorn decoytell.api:app --port 8000   # run the API standalone
```
