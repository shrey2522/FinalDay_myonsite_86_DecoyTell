# T2 — Scoped auto-correction + single-drift repair (issue #3)

## Problem statement (from the ticket)

T1 can *detect* drift and say `PASS` or "drifted", but it cannot **repair** it. The
PRD's core requirement is that a drifted attribute must be **corrected in place —
only that attribute, never a full decoy rebuild** — and the correction must be
**re-verified against the full comparison model**. The ticket also demands the
"can't fix it" path: when an attribute cannot be corrected, the decoy must be marked
**unsafe to expose** (`UNSAFE`).

## What we built (coding terms)

| Module | Responsibility |
|---|---|
| `decoytell/corrector.py` | `correct(schema, history, decoy, analysis, analyze, overrides)` → `(verdict, corrections, final_decoy, blocked_attributes)` |
| `decoytell/engine.py` (extended) | `run_scenario` now routes drift into the corrector and returns `CORRECTED` / `UNSAFE` |
| `decoytell/report.py` (extended) | Report gains `corrections`, `blocked_attributes`, and a **`final`** section (the post-correction passing state — the proof) |
| `decoytell/validate.py` (extended) | Optional scenario-level `correctable` override (lets a matched pair declare an attribute infra-locked) |
| `scenarios/s2_single_drift.json` | The demo: `patch_cadence_days` pushed to 300 days |

**Correction semantics (ADR-0004), as implemented:**

1. **Scoped**: `failing_attributes()` = attributes failing marginally **plus** both
   members of every fingerprint pair, in declared-surface order. Only those are touched.
2. **One at a time, budgeted**: at most `K=50` fix attempts (budget constant); the loop
   always terminates.
3. **Target = conditional mode**: the fix value is the real window's *modal* value
   (categorical) or *median* (numeric) **conditioned on the decoy's other attributes** —
   i.e. "what would a real box of this type carry?" The conditioning pool uses
   progressive relaxation (exact other-categorical match → partner → whole window,
   each requiring ≥ 2 observations).
4. **Full re-verify after every fix**: `analyze` is re-run on the whole check set
   (all 5 + all 10 pairs) after each fix; a fix that introduces a new violation is
   caught, not masked.
5. **UNSAFE triggers**: (a) every failing attribute is non-correctable →
   `blocked_attributes` names them; (b) no correction target exists or the fix is a
   no-op; (c) budget exhausted.
6. **Fix emission**: each fix records `{attribute, before, after, action, re_verified}`.

## What this ticket solves (layman terms)

T1 could say "something's off." T2 makes the tool **do something about it**: if one
attribute is out of line, it changes *only that attribute* to the value a real server
of that type would have, re-checks everything, and reports the before → after as proof.
And when a drift can't be fixed — e.g. the decoy's traffic behavior is physically
locked — it says "**do not expose this fake**". This is the "auto-correction: fix just
that attribute, not a full rebuild" requirement from the PRD.

## Design intent (why this way)

- **Conditional mode, not a random sample**: a random draw from the marginal could
  land on an outlier and look wrong; the *modal value given the decoy's other
  attributes* is exactly how an operator makes a decoy look like a real box "of that
  type", and it is deterministic.
- **Sequential with full re-verify**: guarantees atomicity — every intermediate state
  is validated, so a fix that breaks something else is detected immediately.
- **Per-attribute `correctable` + fix action**: models reality — some attributes are
  editable (banner string), some are infrastructure-locked (monitoring behavior). The
  operator gets an actionable "do this" string, not just a number.

## Alternatives considered and rejected

| Alternative | Why rejected |
|---|---|
| "Fix" = regenerate a fresh decoy from the distribution (rebuild) | The PRD explicitly wants *only the drifted attribute* fixed, not a rebuild; a rebuild also destroys a deployed decoy's identity |
| Correction target = uniform random sample of the failing attribute's marginal | Non-deterministic; can pick an outlier that still looks wrong; conditional mode is principled and reproducible |
| Hand-written "if X drifted then set to Y" fix rules per attribute | Not data-driven; cannot generalise; contradicts the declared-model spirit |
| Mark UNSAFE immediately on any failed re-verify (no budget loop) | A single bad fix attempt would condemn a fixable decoy; the budget loop lets correction genuinely try |

## How to check

```
python demo.py --scenario s2
python -m unittest discover tests   # 18 tests, OK (5 of them corrector-specific)
```

**Expected (`s2`):** `patch_cadence_days 300  DRIFT  in [2.7, 186.4]` (named),
then `FIX patch_cadence_days: 300 -> 17.4 (apply upstream security patch)`,
`re-verified: True`, `RE-VERIFY: all 5 individual checks and all 10 pairs OK -> PASSING`,
`VERDICT: CORRECTED (expected: CORRECTED)`.

**Also check:** `tests/test_corrector.py` proves — harmless decoy untouched
(`PASS`, zero corrections), the non-correctable path (`correctable: {"timing_band": false}`)
→ `UNSAFE` naming the blocked attributes, and the full `{attribute, before, after,
action, re_verified}` emission shape.

## Status

✅ Implemented, tested (18 green), committed on `main` (`T2` commit).