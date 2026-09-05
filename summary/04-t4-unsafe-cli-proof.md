# T4 — Unsafe / insufficient-data + scriptable CLI + JSON proof (issue #5)

## Problem statement (from the ticket)

T1–T3 can certify a decoy (`PASS`), repair it (`CORRECTED`), and catch the joint
fingerprint — but the tool still cannot say **"this decoy is unsafe to expose"**, it
has no way to refuse certification on **insufficient evidence**, and it isn't
**scriptable** (no exit codes) nor does it emit an **objective proof artifact**
(machine-readable JSON). All four are required to turn a demo into a tool a CI/CD
pipeline or an operator can actually rely on.

## What we built (coding terms)

| Module | Responsibility |
|---|---|
| `scenarios/s4_uncorrectable.json` | The `UNSAFE` demo: the s3-style fingerprint, but `timing_band` declared **non-correctable** (infra-locked) via the scenario-level `correctable` override → no scoped repair exists |
| `scenarios/s5_insufficient_data.json` | The `INSUFFICIENT_DATA` demo: `observations: 50` → recent window has ~6 observations (< 100 minimum) |
| `demo.py` (rewritten `main`) | Exit codes, `--json-dir` proof export, prefix scenario selection |
| `decoytell/report.py` (extended) | Clear `INSUFFICIENT DATA` message; suppresses the misleading "PASSING" line when nothing was verified |
| `tests/test_cli.py` | Locks all four acceptance criteria at the seam + through the CLI |

**CLI contract (scriptable gate):**

```
demo.py                       # all scenarios, exit code reflects worst state
demo.py --scenario <prefix>   # e.g. s3 or s3_pair_fingerprint
demo.py --json-dir <dir>      # default: out/

exit 0  all scenarios certified (PASS or CORRECTED)
exit 1  any scenario UNSAFE (unsafe to expose)
exit 2  any scenario INSUFFICIENT_DATA (cannot certify on available evidence)
```

**JSON proof export** (`out/<scenario_id>.json`) contains the complete run:
`schema_version`, `thresholds`, `history_size`, `window_size`, `attributes`
(per-check numbers), `pairs` (expected-vs-observed), `corrections`
(`{attribute, before, after, action, re_verified}`), `blocked_attributes`, `final`
(passing state), `verdict`.

## What this ticket solves (layman terms)

- **"Do not expose this fake"**: when the drift can't be repaired (e.g. response
  timing is physically locked on the decoy host), the tool now says so outright and
  names the blocked attributes.
- **"No evidence, no blessing"**: with too few observations the tool refuses to
  certify instead of guessing.
- **Scriptable**: a pipeline can now gate on the result — exit 0/1/2 tells a CI
  system whether decoys are safe.
- **Proof**: every run leaves a JSON file a judge (or auditor) can open — the exact
  checks, numbers, fixes, and verdict.

## Design intent (why this way)

- **Exit codes encode severity, with `INSUFFICIENT_DATA` (2) ranking above `UNSAFE` (1)**:
  refusing to certify on no evidence is a worse failure than a known-unsafe decoy —
  a silent false-pass is the worst outcome for a security tool.
- **`UNSAFE` comes from the declared surface, not a new heuristic**: the same engine
  and corrector already implement the semantics (ADR-0004); s4 only changes a
  *declaration* (`correctable: {"timing_band": false}`), which is the honest way a
  matched pair records "we can't change this in reality."
- **JSON proof mirrors the CLI report**: the human table and the machine artifact are
  the same report object serialized two ways — no drift between what a judge reads
  and what a system consumes.

## Alternatives considered and rejected

| Alternative | Why rejected |
|---|---|
| A separate "hard-coded" UNSAFE rule (e.g. flag when a specific attribute drifts) | Not data-driven; would duplicate engine logic. The corrector's non-correctable path already produces it |
| No exit-code precedence (first failure wins) | Would make the gate order-dependent; explicit severity ranking is deterministic and documented |
| Write JSON only on demand (no default) | "Each scenario writes a complete JSON proof export" is a ticket requirement; always-on is simpler and judges expect it |
| Human-readable report only, JSON optional | PRD demands proof of correction; an objective artifact is what makes the output auditable |

## How to check

```
python demo.py --scenario s4; echo $?      # UNSAFE, exit 1
python demo.py --scenario s5; echo $?      # INSUFFICIENT_DATA, exit 2
python demo.py --scenario s1; echo $?      # PASS, exit 0
python demo.py --json-dir out              # writes out/<id>.json for every scenario
python -m unittest discover tests          # 24 tests, OK
```

**Expected (`s4`):** all 5 attributes individually `OK`, then
`PAIR (timing_band=slow, monitoring_behavior=immediate): observed 0, expected 12.97 ->
structurally absent`, then `BLOCKED: timing_band is not correctable into tolerance` +
`BLOCKED: monitoring_behavior ...`, `VERDICT: UNSAFE`, exit 1.

**Expected (`s5`):** `INSUFFICIENT DATA: recent window has 6 observations (< 100
minimum) - cannot certify`, `VERDICT: INSUFFICIENT_DATA`, exit 2.

**Open `out/s4_uncorrectable.json`** and confirm every section of the proof is present.

## Status

✅ Implemented, tested (24 green), committed on `main` (`T4` commit).