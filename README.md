# DecoyTell — Bounded Deception-Surface Consistency Verification

A self-contained, offline, deterministic tool that verifies a **decoy** (a fake/honeypot
server) convincingly resembles the **real asset** it impersonates, across a fixed,
declared set of observable attributes — and either **repairs** drift automatically or
marks the decoy **unsafe to expose**.

Python 3.8+ standard library only. No pip installs. No network.

## Why

An attacker fingerprints a decoy by checking small observable properties against what a
real server of that type looks like. If the decoy's attributes drift — *individually*,
or in a *combination* that real servers never exhibit — the attacker spots the trap and
it becomes useless. DecoyTell makes that believability check reproducible and
automatic.

## The declared surface (the comparison model)

Exactly five observable attributes, each with a kind, a tolerance rule, a
correctability flag, and an operator-facing fix action:

| Attribute | Kind | Tolerance rule | Correctable | Fix action |
|---|---|---|---|---|
| `service_banner` | categorical | seen in window, count ≥ 2 | yes | reconfigure server header/banner |
| `patch_cadence_days` | numeric | inside window `[Q05, Q95]` | yes | apply upstream security patch |
| `timing_band` (`fast/nominal/slow`) | categorical | seen in window, count ≥ 2 | yes | adjust response throttling |
| `account_age_days` | numeric | inside window `[Q05, Q95]` | yes | update cert/account-age metadata |
| `monitoring_behavior` (`immediate/rate_limited/silent`) | categorical | seen in window, count ≥ 2 | no | host-level change, not editable |

All thresholds live in `decoytell/schema.py`.

## How it works

1. **Real asset = observation history.** A seeded, parametric generator synthesises the
   real asset's time-ordered history (~1400 observations / 730 days) with realistic
   dependencies (new banner ⇒ short patch cadence; `immediate` boxes are never `slow`;
   `silent` boxes are never `fast`).
2. **Recent window.** All statistics use only the last 90 days — the decoy is judged
   against the asset *as it is now*. Fewer than 100 window observations ⇒
   `INSUFFICIENT_DATA` (refuses to certify rather than guessing).
3. **Individual (marginal) checks.** Numeric: value inside the window's `[Q05, Q95]`
   percentile band. Categorical: value seen in the window with count ≥ 2.
4. **Joint check (the "aha").** For all 10 attribute pairs, a combination is a
   **fingerprint** iff `observed == 0` **and** `expected = N·P(a)·P(b) ≥ 1` — the real
   asset *should* have produced it but never did. This catches two individually-fine
   attributes whose pair is structurally impossible.
5. **Scoped auto-correction.** Drifted attributes are repaired **in place** (never a
   full rebuild), one at a time, to the real window's **conditional mode** given the
   decoy's other attributes, then the **full check set is re-run** after every fix.
   Budget K=50; non-correctable drift ⇒ `UNSAFE`.
6. **Verdicts.** `PASS` · `CORRECTED` · `UNSAFE` · `INSUFFICIENT_DATA`.

## Demo

```
python demo.py                 # all scenarios
python demo.py --scenario s3   # one scenario (prefix match)
python demo.py --json-dir out  # also write out/<id>.json proof exports
```

| Scenario | What it proves | Verdict |
|---|---|---|
| `s1_harmless` | within-tolerance variation is accepted | `PASS` |
| `s2_single_drift` | one out-of-band attribute caught, named, corrected | `CORRECTED` |
| `s3_pair_fingerprint` | two individually-fine attributes whose pair never occurs — caught **only** by the joint check | `CORRECTED` |
| `s4_uncorrectable` | a drift that cannot be repaired (non-correctable attribute) | `UNSAFE` |
| `s5_insufficient_data` | not enough evidence to certify | `INSUFFICIENT_DATA` |

**Continuous observation demo** (`python observe_demo.py`): a simulated live real
server that gets patched mid-run; the observer verifies the decoy every cycle and
automatically catches + corrects the drift when the decoy fails to follow.

## Live integration (Docker + PostgreSQL)

Real servers, real probes, real persistence. Spec: [issue #7](https://github.com/shrey2522/FinalDay_myonsite_86_DecoyTell/issues/7).

```
docker compose up -d                      # real-asset (:8443), decoy (:8444), postgres (:5433)
pip install -r requirements-live.txt      # the only live-layer dependency (psycopg)
python collect_live.py --seed             # seed the store with the mock history, probe real-asset
python live_demo.py --cycles 6 --interval 5   # real-time loop: probe -> verify -> correct -> re-verify
python verify_live.py                     # end-to-end integration check (fails non-zero on any step)
```

What the loop does every cycle: probe the real-asset container and append the
observation to PostgreSQL; probe the decoy; read the real asset's recent 90-day
window from the store; verify the decoy via the engine; apply corrections to the
decoy's **served identity** through the management plane; re-probe and re-verify;
log the cycle. The engine, verdicts, and JSON proof are untouched — the live layer
sits entirely below the `verify(history, decoy)` seam (ADR-0003 v2).

**Honest framing**: this is real probing of containerized servers inside an isolated
Docker environment — banner, TLS-cert account age, and latency are genuine
measurements; patch cadence is inferred from a version->release map; timing and scan
behavior are measured against deliberately engineered container configuration
(disclosed in the output). It demonstrates the full pipeline end-to-end, not a
production network.

## Web dashboard (monitoring UI)

FastAPI API + React/TypeScript/Tailwind/shadcn UI. Spec/design: ADR-0005.

```
pip install -r requirements-live.txt -r requirements-web.txt
python loop_service.py                  # standalone loop process (waits for control)
python -m uvicorn decoytell.api:app --port 8000
cd web && npm install && npm run build  # UI served at http://localhost:8000/
```

Or everything containerized: `docker compose up -d --build` → open
**http://localhost:8000** (the API container serves the API and the built UI).

**Views**: Dashboard (verdicts, loop start/stop, verify now) · Scenarios (full reports:
attributes ✓/✗, fingerprints, corrections with reasoning) · Live loop (real vs decoy
probes per cycle, fixes, timestamps) · Pair matrix (the 10 pairwise joint checks) ·
Observations (recent window streams). Polling every 3s.

**Architecture (ADR-0005)**: the loop is its own process persisting every cycle to
PostgreSQL (`loop_events`) and polling a `loop_control` row; the API only reads events
and toggles the control row — the loop survives API restarts and vice versa.

**Exit codes (scriptable gate):**

| Code | Meaning |
|---|---|
| 0 | all scenarios certified (`PASS` / `CORRECTED`) |
| 1 | any scenario `UNSAFE` |
| 2 | any scenario `INSUFFICIENT_DATA` (takes precedence over 1) |

**JSON proof** (`out/<scenario_id>.json`): schema version, thresholds, window stats,
per-attribute check numbers, pair expected-vs-observed counts, corrections
(`{attribute, before, after, action, re_verified}`), blocked attributes, final passing
state, verdict.

## Tests

```
python -m unittest discover tests
```

Behavioral tests drive everything through the single verification seam
(`run_scenario(config) → report`) and assert verdicts, named attributes, and report
values — never internal implementation. The suite includes byte-identical
determinism tests (same seed ⇒ identical output).

## Docker (isolated verification)

```
docker build -t decoytell .
docker run --rm decoytell
```

Runs the full test suite and the demo inside a `python:3.12-slim` container. Exit is
non-zero on any test failure or any `UNSAFE`/`INSUFFICIENT_DATA` verdict — the demo set
intentionally includes s4/s5, so a non-zero exit here *is* the gate firing correctly.
A clean run: `docker run --rm decoytell sh -c "python demo.py --scenario s1"` (exit 0).

## Project layout

```
demo.py              CLI entry + exit codes + JSON export
observe_demo.py      continuous-observation demo (live-feed simulation)
decoytell/           schema, generator, engine (seam), corrector, report,
                     validate, observe
scenarios/           declarative JSON scenarios (the declared model, tweakable)
tests/               behavioral suite at the run_scenario seam
summary/             per-ticket implementation writeups (problem, intent, alternatives)
CONTEXT.md           domain glossary · docs/adr/0001–0004  architecture decisions
```