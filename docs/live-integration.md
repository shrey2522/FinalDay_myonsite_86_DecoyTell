# Live-server integration: how DecoyTell works against a real, live asset

## The core claim

DecoyTell's engine is **source-agnostic**. It consumes exactly two things and never
reaches for the network itself:

```
(real asset's recent observation history,  decoy's current observed tuple)  →  verdict
```

Both inputs are *injected*. Today they come from the seeded generator and the scenario
JSON; in production they come from a **collector** that observes the real live server
and **probes** the decoy. Nothing downstream changes — the checks, the joint check, the
corrector, the verdicts, and the JSON proof are identical.

## The three roles in a real deployment

| Role | In the current build | In production |
|---|---|---|
| **Real asset** (live, ~100% uptime) | `generate_history(seed)` — synthetic | A production server; a **collector** samples it passively on a schedule |
| **Decoy** (the fake) | a static tuple in `scenarios/*.json` | The deployed decoy; the same collector **probes** it the way an attacker would |
| **Collector / prober** | (does not exist — not needed for the demo) | New component, outside the engine, that produces observations |

## Production data flow (unchanged engine)

1. **Collect** the real asset's 5 attributes on a schedule (e.g. every 15 min):
   - `service_banner` — banner grab off a connection
   - `patch_cadence_days` — current version vs. its release/CVE timeline
   - `timing_band` — measured latency bucketed to fast/nominal/slow
   - `account_age_days` — TLS cert `notBefore` / domain-age metadata
   - `monitoring_behavior` — controlled-scan response profile (immediate / rate_limited / silent)
   Each sample is one **observation**, appended to a rolling store (keep the last ~90 days;
   the `INSUFFICIENT_DATA` guard refuses to certify until ≥ 100 observations exist).
2. **Probe the decoy** with the *same* collector → its current tuple (fresh, "as of now").
3. **Run** `run_scenario(real_history, decoy_tuple)` → verdict.
4. **Act**:
   - `PASS` → keep exposed.
   - `CORRECTED` → apply the named `fix_action` to the decoy, re-probe, re-verify.
   - `UNSAFE` → pull the decoy out of the exposure path.
   - `INSUFFICIENT_DATA` → not enough evidence; do not certify.

## How the "current status" concern is handled

A hacker checks the *current* state of the server, not just old history — and so does
this system, on both sides:

- **Real asset "as it is now"**: the comparison uses the **recent 90-day window**, the
  tail of the history. If the real server patches today, the new observations land in
  the window immediately and the model follows the live server — the decoy is judged
  against what the real asset looks like *today*, not last year. (This is exactly why
  the ADR-0001 decision used a history + a recent window rather than a static snapshot.)
- **Decoy "as it is now"**: the decoy tuple is a **fresh probe** taken at verification
  time, the same way the attacker would observe it.

So the comparison is current-vs-current: the attacker's view of the decoy is compared
to the defender's recent view of the real asset.

## The idle / 100%-uptime case

- The real server never goes down → the collector keeps a rolling window; old
  observations are dropped, the model tracks the live state forever.
- The decoy sits idle → scheduled probes still sample its state. When the *real* server
  changes (patch, cert renewal, behavior change) and the idle decoy does not follow,
  the next scheduled verification catches exactly that drift — this is s2/s3 happening
  automatically over time.
- Continuous operation = a scheduled re-verify loop (cron / orchestrator): *probe →
  compare → correct → re-probe → re-verify*. DecoyTell is the decision function inside
  that loop.

## What would change in code (very little)

| Piece | Change |
|---|---|
| `generate_history(seed)` | Replaced by a pluggable `HistorySource` (live collector reads a store). Engine signature unchanged — it takes a list of observations |
| `decoy` tuple | Produced by a `probe(decoy_endpoint)` step that returns the same 5-field schema |
| `scenarios/*.json` | Becomes a "runbook": target real asset + decoy endpoint + schedule |
| Engine, corrector, joint check, verdicts, JSON proof | **unchanged** — this is the payoff of the observation-history design |

## Honest limits (collector engineering, not engine)

- The engine is only as good as the observations. Both sides must be measured with the
  **same method** (or the tolerances are meaningless).
- `patch_cadence_days` inference needs a version→release mapping; `account_age_days`
  needs a cert/WHOIS source; `monitoring_behavior` needs controlled scans. These are
  collector concerns, deliberately out of scope for the hackathon build.
- Real deployments would size the window/tolerances from the asset's actual variance —
  all of that is declared in `schema.py`.

## Summary

The current build simulates the data because the PRD explicitly allows it, but the
system is architected so the *logic* and the *data source* are separate. Point a
collector at a live server, probe the decoy with the same collector, and the existing
engine, correction loop, verdicts and proof work unchanged. The recency design (90-day
window + fresh decoy probe) is precisely what answers "the hacker checks the current
status."