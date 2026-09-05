# T1 — Engine + harmless PASS path (issue #2)

## Problem statement (from the ticket)

There is no comparison machinery at all yet. To know whether a decoy "looks real"
we first need: (a) the **declared surface** — the fixed, finite set of attributes
the comparison covers (not open-ended guessing), (b) a **reference** for the real
asset to compare against, (c) the **tolerance checks** that decide if a value is
believable, and (d) an end-to-end path that produces a verdict. Without this
foundation nothing else (correction, joint check, UNSAFE) can exist.

## What we built (coding terms)

| Module | Responsibility |
|---|---|
| `decoytell/schema.py` | The declared surface: 5 attributes (`service_banner`, `patch_cadence_days`, `timing_band`, `account_age_days`, `monitoring_behavior`) with kind, tolerance rule, `correctable` flag and `fix_action`; plus all thresholds as constants (`THRESHOLDS`) |
| `decoytell/validate.py` | `validate_scenario()` — rejects malformed scenario declarations loudly (missing/unknown attribute, undeclared categorical value, non-numeric value, bad seed) |
| `decoytell/generator.py` | `generate_history(seed)` — seeded, parametric synthesis of the real asset: 1400 time-ordered observations over 730 days, with engineered dependencies |
| `decoytell/engine.py` | `analyze()` (marginal + pairwise joint checks) and the **single seam** `run_scenario(config) → report` |
| `decoytell/report.py` | `build_report()` / `render_text()` / `to_json()` — the CLI table + serializable JSON report |
| `demo.py`, `scenarios/s1_harmless.json` | CLI entry + the first demo scenario |
| `CONTEXT.md`, `docs/adr/0001–0004` | Domain glossary + the four architecture decisions |

**The engine's rules (all constants in `schema.py`):**

- **Recent window**: only observations from the last `90` days are used — the decoy
  is judged against the asset *as it is now*, not as it was a year ago.
- **Minimum evidence**: if the window has `< 100` observations the engine refuses
  to certify → `INSUFFICIENT_DATA`.
- **Numeric attributes** (`patch_cadence_days`, `account_age_days`): in-tolerance iff
  the value falls inside the window's `[Q05, Q95]` percentile band (linear-interpolation
  percentiles, pure stdlib).
- **Categorical attributes**: in-tolerance iff the value was seen in the window **and**
  its count `≥ 2`.
- **Joint check** (all 10 attribute pairs): a pair is a *fingerprint* iff
  `observed == 0` **and** `expected = N·P(a)·P(b) ≥ 1` — i.e. the real asset *should*
  have produced the combination but never did.

**The generator's engineered dependencies** (what makes the demo honest):

- Banner lifecycle: the asset upgraded `Apache/2.4.29 → 2.4.41 → 2.4.54` over time.
- **New banner ⇒ short patch cadence** (`patch_cadence ≈ Uniform(1, release_age·0.6)`).
- **`timing_band × monitoring_behavior` constraint**: `immediate` boxes are never
  `slow`; `silent` boxes are never `fast` → some pairs are structurally impossible.
- `account_age` tracks the asset's birth (~800 days ± jitter).

## What this ticket solves (layman terms)

We built the **measuring stick and the measurement**. Before T1 you could only
"hope" a decoy looked real. Now the tool has: a fixed checklist (the 5 attributes),
a picture of what a real server looks like recently (the seeded history), rules for
"close enough" (tolerances), and a verdict machine that says `PASS` or "not enough
data to know". It can already *say* "this decoy is believable" — fixing it is T2.

## Design intent (why this way)

- **Observation history, not a snapshot** (ADR-0001): tolerance bands and
  co-occurrence counts need *data*, and the joint check needs to see combinations
  that never happen. One snapshot can't provide either.
- **Pairwise joint check with an expected-count guard** (ADR-0002): the
  `expected ≥ 1` guard is what stops sparse-data false positives — it only flags
  combinations the data says *should* exist but doesn't.
- **Python stdlib only** (ADR-0003): zero dependencies, fully offline — runs on any
  laptop, including the hackathon one.
- **Single seam `run_scenario`**: all tests (and the demo) go through one pure,
  deterministic function, so behavior is verified exactly as a judge runs it.

## Alternatives considered and rejected

| Alternative | Why rejected |
|---|---|
| Real asset = single snapshot + hand-written tolerance ranges | The joint check needs data on observed combinations; hand-written ranges are exactly the "open-ended guessing" the PRD forbids |
| Live network scanning of a real server | Offline constraint (no internet dependency); the PRD explicitly allows synthetic/simulated data |
| Full 5-tuple joint probability model | Sparse at ~170 window observations; needs smoothing that hides exactly the signal we want |
| pandas / numpy for statistics | ADR-0003: stdlib-only; the percentile implementation is ~10 lines |
| Flag any pair with `observed == 0` (no expected guard) | False positives on continuous numeric values; the `expected ≥ 1` guard is what makes the check robust |

## How to check

```
cd C:\Users\91999\OneDrive\Desktop\final\FinalDay_myonsite_86_DecoyTell
python demo.py --scenario s1        # the PASS demo
python -m unittest discover tests   # 18 tests, OK
```

**Expected (`s1`):** all 5 attributes `OK` (e.g. `patch_cadence_days 12  in [3.1, 187.2]`,
`timing_band fast  seen 98/173`), `JOINT check: no fingerprints across 10 pairs`,
`VERDICT: PASS (expected: PASS)`.

**Also check:** the `INSUFFICIENT_DATA` guard is proven by `tests/test_engine.py`
(`test_insufficient_history_refuses_to_certify`), and determinism by
`test_every_scenario_is_deterministic` (same seed ⇒ byte-identical report).

## Status

✅ Implemented, tested (18 green), committed on `main` (`602ecbf`).