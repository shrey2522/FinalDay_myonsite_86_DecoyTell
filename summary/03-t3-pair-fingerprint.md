# T3 — Pair-fingerprint path, the "aha" (issue #4)

## Problem statement (from the ticket)

This is the **judging centerpiece** and the hardest PRD requirement: two attributes
that are **each individually fine** (inside tolerance) but whose **combination is a
unique fingerprint** — a combination the real asset never exhibits. The PRD insists
this must be caught by the comparison model itself, **not by a hand-written rule**,
and the output must **name both attributes** and **prove the fix**. Before T3, the
joint check existed but there was no end-to-end scenario proving it catches what the
individual checks cannot.

## What we built (coding terms)

| Module | Responsibility |
|---|---|
| `scenarios/s3_pair_fingerprint.json` | The demo scenario: `timing_band=slow` + `monitoring_behavior=immediate` |
| `tests/test_joint.py` | Locks the PRD requirement at the seam: individually fine before correction, caught only by the joint check, named, corrected, re-verified |
| `demo.py` (tiny fix) | `--scenario` now accepts id prefixes (`s3` matches `s3_pair_fingerprint`) |

No engine change was needed — the pairwise joint check (T1) and the conditional-mode
corrector (T2) already provide the machinery. T3 made the machine *demonstrable* and
*provable*.

**The fingerprint, by the numbers (seed 3001, window 173):**

- `timing_band=slow` → seen `19/173` → **individually in tolerance**
- `monitoring_behavior=immediate` → seen `99/173` → **individually in tolerance**
- pair `(slow, immediate)` → **observed 0, expected 10.87** → *structurally absent* —
  a real `immediate` box is essentially never `slow`
- Fix: `timing_band slow → fast` (the conditional mode given `monitoring=immediate`,
  since `monitoring_behavior` is declared non-correctable) → pair `(fast, immediate)`
  is observed 76 times → re-verified green.

## What this ticket solves (layman terms)

The case that makes DecoyTell worth building: a decoy that **passes every single check
but is still instantly recognisable as fake** because two otherwise-normal-looking
facts *never occur together on a real server*. Think of it like a fake ID where the
name and the photo are each fine, but the combination of "name" + "birth year" is
impossible. A naive checker approves it; the attacker spots it in a second. T3 proves
DecoyTell sees that combination, names both attributes, fixes one, and shows the
decoy now passes.

## Design intent (why this way)

- **Caught by data, not rules**: the engine computes *expected vs observed* co-occurrence
  from the real history. It did not need to be told about "immediate + slow". This is
  what the PRD means by a *declared comparison model*: reproducible, no hidden
  fingerprint knowledge.
- **Expected-count guard**: `expected ≥ 1` is what makes the check only fire on
  combinations that *should* exist — sparse numeric values never trip it.
- **The non-correctable flag picks the fix side**: the fingerprint involves
  `monitoring_behavior` (non-correctable) and `timing_band` (correctable), so the
  corrector deterministically fixes `timing_band`. The pair is repaired without
  touching an attribute the operator can't change.

## Alternatives considered and rejected

| Alternative | Why rejected |
|---|---|
| Hand-write a fingerprint rule ("if slow and immediate then flag") | Exactly what the PRD forbids: open-ended guessing, not a declared model; wouldn't generalise to fingerprints the author never thought of |
| Flag *any* pair with `observed == 0` | False positives from sparse data; the `expected ≥ 1` guard is what keeps it precise |
| Full 5-tuple likelihood / ML anomaly detection | Too sparse at ~170 observations, needs smoothing, and ML is out of scope (offline, reproducible) |
| Fix both members of the pair | Over-repair; changing the non-correctable attribute is impossible anyway. Fix the one that can be changed (conditional mode) |

## How to check

```
python demo.py --scenario s3
python -m unittest discover tests   # 18 tests, OK (3 of them joint-specific)
```

**Expected (`s3`) — read it top to bottom:**

```
timing_band          slow      OK   seen 19/173     ← individually FINE
monitoring_behavior  immediate OK   seen 99/173     ← individually FINE
JOINT check: fingerprint(s) detected
  PAIR (timing_band=slow, monitoring_behavior=immediate):
       observed 0, expected 10.87 -> structurally absent
FIX timing_band: slow -> fast (adjust response throttling)
  re-verified: True
RE-VERIFY: all 5 individual checks and all 10 pairs OK -> PASSING
VERDICT: CORRECTED (expected: CORRECTED)
```

The judge's "aha": **all five rows say OK, and yet the decoy is caught** — only the
joint check sees it.

**Contrast all three scenarios** (`python demo.py`): `s1 → PASS`, `s2 → CORRECTED`
via the *individual* check, `s3 → CORRECTED` via the *joint* check only.

## Status

✅ Implemented, tested (18 green), committed on `main` (`T3` commit).