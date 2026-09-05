# Live T1–T3 — Live integration: real containers + PostgreSQL + scheduled loop (issues #8–#10)

## Problem statement (from the spec, issue #7)

The core engine (T1–T5) is fully verified against simulated data. To prove the system
works against a *real, running* server, the live-integration layer deploys actual
server containers in Docker, persists observations in PostgreSQL, probes the live
endpoints to measure the declared surface, and runs a scheduled verification/correction
loop against them. The three tickets: collection path (prober + store + containers),
the real-time loop, and integration verification + docs.

## What we built (coding terms)

| Ticket | Piece | Responsibility |
|---|---|---|
| T1 | `decoytell/probe.py` | Real collector: socket banner grab, version→patch-cadence map, latency band, TLS cert `notBefore` → account age (stdlib DER decoder), 6-probe scan burst → monitoring profile. Returns the same 5-field observation the engine consumes |
| T1 | `decoytell/store.py` | PostgreSQL observation store: `init_schema` / `seed` (mock history) / `append` / `recent_window(days, target)` → engine `Observation`s |
| T1 | `containers/identity/` | Engineered HTTPS identity server (banner / timing / monitoring configurable); Dockerfile generates a **backdated self-signed cert** via `openssl ca -startdate` so account age is real metadata |
| T1 | `docker-compose.yml` | real-asset (correct identity), decoy (flawed clone), postgres (persistent volume, healthcheck) |
| T1 | `collect_live.py` | `--seed` mock history → probe → append → report window |
| T1 | ADR-0003 v2 | stdlib carve-out: core stays pure stdlib + in-memory; live layer may use a database client, isolated |
| T2 | `decoytell/live.py` | `run_loop`: per cycle — probe real → append; probe decoy → verify vs store window → apply fixes via control plane → re-probe → re-verify → log. `map_fix_to_identity`: engine corrections → live-applicable identity changes (cadence fixes map to the modal banner; account age honestly "not applicable") |
| T2 | `decoytell/control.py` | Management-plane client (`POST /admin/identity`) |
| T2 | `live_demo.py` | Scheduled loop CLI with pretty per-cycle log |
| T3 | `verify_live.py` | End-to-end integration check: compose up → seed → loop → corrected → matching; fails non-zero on any step |
| T3 | README / `summary/06` | Live demo commands + honest framing; this writeup |

**Test count: 43** (29 core + 5 prober + 2 store + 7 loop). Store tests skip cleanly
without a DSN, so the core suite runs with zero live dependencies.

## What this solves (layman terms)

The "mock-data" criticism is answered with a working artifact: two real HTTPS
servers in Docker, one proper and one a flawed clone; observations measured from
live connections and stored in a real PostgreSQL database; a loop that checks the
decoy on a real clock, and when the decoy drifts (serves a banner the real asset
never shows + a joint fingerprint), it **changes the running decoy's actual served
identity** through a management endpoint and proves it green again with a fresh
probe. The engine's verdicts and proof are byte-identical to the simulated path —
only the data source changed.

## Design intent (why this way)

- **Live layer below the engine seam**: `verify(history, decoy)` is the loop's
  decision function; the engine, corrector, verdicts, and JSON proof were never
  modified. This is the payoff of ADR-0001/ADR-0004.
- **Control plane on the server**: a decoy platform has a management API in real
  life; `POST /admin/identity` is its analogue. The loop changes the served
  identity, and the next probe proves it — correction is real, not tuple-editing.
- **Honest applicability mapping**: not every engine fix is settable on a live
  box (you can't backdate a live cert); the mapping translates what *can* change
  (banner → cadence, timing, monitoring) and marks the rest "cannot apply".
- **Backdated certs via `openssl ca`**: `openssl req` ignores
  `default_startdate`; self-signing through `openssl ca -startdate` produces a
  cert whose `notBefore` is genuinely 800/100 days ago — account age is a real
  measurement.
- **Test isolation**: store tests use `test-` prefixed targets and delete only
  their own rows, so the demo store's seeded history is never destroyed by a
  test run.

## Alternatives considered and rejected

| Alternative | Why rejected |
|---|---|
| Real Apache containers | Less controllable (banner/cert/timing not tunable per-container); the engineered Python identity server gives exact identity control for the demo |
| SQLite store | Functional but loses the "real PostgreSQL" story the operator asked for; the `psycopg` dep is isolated to the live layer (ADR-0003 v2) |
| Apply corrections by container restart with new env | Heavy and slow per cycle; a management endpoint is how real platforms do it |
| `openssl req` backdating via `default_startdate` | Silently ignored by `req -x509` (verified empirically); `openssl ca -startdate` actually works |
| Wait for the real window to slide after a real patch | Takes ~90 real days — impossible in a demo; instead the decoy's drift is immediate (unseen banner + fingerprint) and the loop catches it in cycle 1 |

## How to check

```
docker compose up -d
pip install -r requirements-live.txt
python verify_live.py            # ALL LIVE CHECKS PASSED, exit 0
python collect_live.py --seed    # optional manual walkthrough
python live_demo.py --cycles 5 --interval 2
```

**Expected (`live_demo.py`):** cycle 1 `CORRECTED -> PASS` with the two fixes
applied to the live decoy (`service_banner 2.4.55 -> 2.4.54`, `timing_band slow ->
fast`), cycles 2+ `PASS -> PASS`.

**Honest framing** (also in README): real probing of containerized servers in an
isolated Docker environment; timing and scan behavior measured against engineered
container configuration; not a production network.

## Status

✅ T1–T3 implemented, tested (43 green), `verify_live.py` green end-to-end,
committed + pushed on `main`.