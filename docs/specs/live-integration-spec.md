# Spec: DecoyTell Live Integration — real containers, PostgreSQL observation store, scheduled verification loop

## Problem Statement

The core engine (T1–T5) is fully verified against simulated data — a seeded synthetic
history and declared decoy tuples. This proves the comparison, correction, and
certification logic, but it does not demonstrate the system working against a *real,
running* server. As the operator I want to deploy actual server containers, persist
observations in a real database, probe the live endpoints to measure the declared
surface, and run a scheduled verification/correction loop against them — so the
"live real-time working system" claim is demonstrated with real artifacts, not just
synthetic input.

## Solution

An additive live-integration layer that sits entirely *below* the existing engine seam.
Nothing in the core engine, its verdicts, or its 29 tests changes. The layer provides:

1. **Real server containers** in Docker (a properly-configured `real-asset` and a
   deliberately misconfigured `decoy`), plus a **PostgreSQL** container as the
   observation store.
2. **A prober** that measures the 5 declared attributes from a live endpoint (banner
   grab, version→patch-cadence inference, latency band, TLS cert age, controlled scan
   profile) and returns the same observation shape the engine already consumes.
3. **A store** that seeds PostgreSQL with the synthetic history ("previous data = mock"),
   appends live observations, and serves the recent 90-day window.
4. **A live loop** (`probe → read window → verify → correct → re-probe → log`) running
   on a real clock, which applies corrections to the decoy container and re-verifies.
5. **ADR-0003 amendment**: a documented carve-out that keeps the core engine pure
   stdlib + in-memory while allowing the live/collector layer a database client.

## User Stories

1. As a DecoyTell operator, I want to deploy the real-asset, decoy, and PostgreSQL containers with **one command**, so the live demo runs anywhere Docker exists.
2. As a DecoyTell operator, I want the observation store to be **PostgreSQL**, so observations persist and are queryable like a real deployment.
3. As a DecoyTell operator, I want the store **pre-seeded with the synthetic history**, so the recent window has a baseline from day one — "previous data = mock, new data = real."
4. As a DecoyTell operator, I want the prober to measure **service_banner** from a live socket connection, so the banner is a real grab, not a declaration.
5. As a DecoyTell operator, I want **patch_cadence_days** inferred from the banner version against a release timeline, so it reflects the live software.
6. As a DecoyTell operator, I want **timing_band** measured from real request latency, so the timing check is an actual measurement.
7. As a DecoyTell operator, I want **account_age_days** derived from the TLS certificate's `notBefore`, so it reflects real metadata.
8. As a DecoyTell operator, I want **monitoring_behavior** derived from a controlled scan-response probe, so the check reflects how the host answers probes.
9. As a DecoyTell operator, I want each probe to return the **same 5-field observation shape** the engine consumes, so no engine change is needed.
10. As a DecoyTell operator, I want the loop to read the **recent 90-day window from PostgreSQL** each cycle, so verification uses the persisted history.
11. As a DecoyTell operator, I want the loop to **verify the decoy against that window on a real clock** (configurable interval), so it is genuinely real-time.
12. As a DecoyTell operator, I want the loop to **apply corrections to the decoy container** (e.g. rewrite the banner it serves) and re-probe, so correction is real, not tuple-editing.
13. As a DecoyTell operator, I want every cycle logged with **timestamp, verdict, and corrections**, so there is a real-time audit trail.
14. As a DecoyTell operator, I want the loop to catch the moment the **real server patches and the decoy lags**, demonstrating live drift detection.
15. As a DecoyTell operator, I want the engine verdicts (`PASS`/`CORRECTED`/`UNSAFE`/`INSUFFICIENT_DATA`) and JSON proof **unchanged**, so the live layer reuses the certified core.
16. As a DecoyTell operator, I want the **core engine and its 29 tests to stay stdlib-only and green** without the live dependencies installed.
17. As a DecoyTell operator, I want the live layer's only dependency (`psycopg`) **isolated to the collector container**, so the core image stays pip-free.
18. As a DecoyTell operator, I want the **ADR-0003 carve-out documented**, so the dependency exception is a recorded decision, not a silent drift.
19. As a DecoyTell operator, I want the store on a **persistent volume**, so data survives container restarts.
20. As a DecoyTell operator, I want the **mock baseline seeded deterministically**, so the live demo is reproducible.
21. As a DecoyTell operator, I want the **demo commands documented** (`docker compose up -d` + a live-runner command), so the workflow is referenceable.
22. As a DecoyTell operator, I want a test that the **prober returns the correct observation shape** against a real container, so the new seam is verified.
23. As a DecoyTell operator, I want a test that the **store appends and serves the recent window** correctly, so the persistence seam is verified.
24. As a DecoyTell operator, I want the loop behavior tested with fakes, so it is testable without always needing Docker up.
25. As a DecoyTell operator, I want honest labeling that **timing/scan attributes are measured against controlled, engineered container behavior** (localhost latency is otherwise degenerate), so the demo does not overclaim.

## Implementation Decisions

- **Seam contract (unchanged core)**: the live loop calls the existing engine seam
  `verify(history, decoy_tuple)` — no core signature changes. `run_scenario` continues
  to serve the T1–T5 scenario demos.
- **Probe contract** (decision-rich shape, from the design discussion):
  ```
  probe(endpoint) -> {
      "service_banner": str,          # socket banner grab
      "patch_cadence_days": float,    # version -> release timeline map
      "timing_band": "fast"|"nominal"|"slow",
      "account_age_days": float,      # TLS cert notBefore
      "monitoring_behavior": "immediate"|"rate_limited"|"silent",
  }
  ```
- **Store contract**: `seed(observations)` (synthetic baseline), `append(observation)`,
  `recent_window(days) -> [observation]`. Backed by PostgreSQL; the engine only ever
  sees the in-memory observation lists it already expects.
- **PostgreSQL schema** (decision-rich shape):
  ```
  observations(id BIGSERIAL PRIMARY KEY,
               observed_at TIMESTAMPTZ NOT NULL,
               target TEXT NOT NULL,               -- 'real-asset' | 'decoy'
               service_banner TEXT, patch_cadence_days DOUBLE PRECISION,
               timing_band TEXT, account_age_days DOUBLE PRECISION,
               monitoring_behavior TEXT)
  ```
- **Containers**: `real-asset` (correctly configured Apache serving the target identity),
  `decoy` (deliberately misconfigured Apache), `postgres` (observation store, persistent
  volume, init-script seeds the mock baseline).
- **Live loop**: every configurable interval — probe `real-asset` → append to store;
  probe `decoy` → `verify(recent_window(90), decoy_tuple)` → if `CORRECTED`, apply the
  fix to the decoy's served identity, re-probe, re-verify → log timestamp/verdict/fixes.
- **Correction application**: the loop rewrites the decoy container's served observable
  (e.g. banner/timing config) so the next probe reflects the fix — correction is
  real-world, not in-memory.
- **Dependency isolation**: `psycopg[binary]` lives only in the live/collector image
  (`requirements-live.txt`); the core image remains pip-free and the 29 core tests run
  without it.
- **ADR-0003 v2**: "core engine remains pure stdlib + in-memory; the live/collector
  layer may use a database and a client library, isolated to that layer."

## Testing Decisions

- **What makes a good test**: external behavior only — the prober's returned shape and
  values against a real container; the store's append/recent-window round-trip; the
  loop catching drift and applying a fix (with fake probe/store for the no-Docker case).
- **Modules tested**: the two new seams (prober, store) and the loop orchestration via
  fakes. The engine seam's 29 existing tests must remain green with no live
  dependencies installed.
- **Prior art**: `tests/test_observe.py` (the continuous-observation loop) and
  `tests/test_cli.py` (command-level behavior) are the templates; the existing
  `run_scenario` seam tests are reused unchanged.

## Out of Scope

- Internet-facing probing or scanning of third-party hosts.
- Production-grade store HA, authentication, or clustering.
- Real-time CVE/version feeds (a static version→release map is used).
- Full decoy fleet management or discovery.
- Changes to the core engine, verdicts, or the T1–T5 scenario model.

## Further Notes

- Honest framing for judging: this is *real probing of containerized servers* inside an
  isolated Docker environment — a genuine end-to-end demonstration, not a production
  network. Timing and scan behavior are measured against deliberately engineered
  container configuration, and that is disclosed in the output.
- The mock baseline is seeded, so the store's history is reproducible; live observations
  then append nondeterministically, which is expected and absorbed by tolerance bands.
- Deliverables include the live-layer spec doc, ADR-0003 v2, prober, store,
  docker-compose, live runner, tests, and a summary writeup (`summary/06`).