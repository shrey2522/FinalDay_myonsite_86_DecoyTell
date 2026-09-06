# DecoyTell — Mentor Guide & Comprehensive Project Report

> **Read this before your demo.** It walks from the attacker's world → why this project
> exists → what the core does → what the new recon layer adds → how to present it live,
> using **one worked example throughout** so you can tell a single, coherent story.

**Repo**: `FinalDay_myonsite_86_DecoyTell` — **Stack**: Python 3.12 (stdlib-first),
PostgreSQL 16, Docker Compose, FastAPI dashboard. **Tests**: 71 passing + 13 env-gated.

---

## 1. Why this project exists — the deception problem

### 1.1 The attacker's world: how a hacker finds a decoy

A real-world attack follows a predictable pipeline. DecoyTell's whole design is built
around **stage 1 and stage 2**:

| Stage | What the hacker does | What they look for |
|---|---|---|
| **1. Reconnaissance** | Passive: DNS/subdomain enumeration, OSINT, search engines, port scans of the perimeter | Exposed hosts, `admin`, `legacy`, `staging`, `backup` subdomains — anything that *looks* old and unmaintained |
| **2. Fingerprinting** | Active: grab service banners, TLS certificates, response timing, probe auth layers | Software version (→ known CVEs), account/cert age (maturity), timing bands (infrastructure class), monitoring behavior (are they defended?) |
| **3. Enumeration** | Map the app: endpoints, auth, patch level | Weak auth, exposed admin panels, outdated frameworks |
| **4. Exploitation** | Attack the juiciest target | Old version + no auth + exposed = easy win |

**The motive for finding decoys is that attackers don't know they're decoys.** An
attacker doesn't hunt for "honeypots" — they hunt for *easy targets*. A decoy server
mocked as a real server is **designed to win the attractiveness contest** at stages 1–2:
it looks like an unpatched, auth-less admin panel, so the attacker's own decision logic
picks it. The recon layer of this project *simulates exactly that decision logic*.

### 1.2 What a decoy does — and the make-or-break requirement

A decoy (honeypot) is a fake server that:
1. **Attracts** the attacker away from real assets,
2. **Keeps them engaged** — the longer they stay, the more intelligence we collect
   (tools, tactics, procedures — their TTPs),
3. **Alerts us** that we're being targeted.

The **make-or-break requirement** is *indistinguishability*: the decoy must look
statistically identical to the real asset it impersonates. The moment any observable
property drifts — a banner the real asset never serves, a version/cadence mismatch, a
timing/monitoring combination that real servers never exhibit — the attacker spots the
trap, leaves instantly, and the honeypot is worthless (and the attacker now *knows*
where your honeypots are).

> **The core problem DecoyTell solves:** keep the decoy's observable surface consistent
> with the real asset across a fixed, declared set of attributes — automatically,
> continuously, and with proof.

---

## 2. What DecoyTell's core does (the verification engine)

### 2.1 The declared comparison surface — exactly 5 attributes

| Attribute | Kind | Tolerance rule | Correctable? |
|---|---|---|---|
| `service_banner` | categorical | seen in real window (count ≥ 2, share ≥ 5%) | yes |
| `patch_cadence_days` | numeric | inside window `[Q05, Q95]` | yes |
| `timing_band` (fast/nominal/slow) | categorical | seen in window | yes |
| `account_age_days` | numeric | inside window `[Q05, Q95]` | yes |
| `monitoring_behavior` (immediate/rate_limited/silent) | categorical | seen in window | **no** (host-level) |

All thresholds live in `decoytell/schema.py`. **No open-ended guessing** — this fixed
surface is the entire comparison model.

### 2.2 The three checks

1. **Marginal (individual) checks** — numeric values must land inside the real asset's
   `[Q05, Q95]` percentile band; categorical values must actually *appear* in the real
   window with a minimum count and share.
2. **Joint check (the "aha")** — all 10 attribute pairs are tested: a combination is a
   **fingerprint** when the real asset *should* have produced it (expected ≥ 1) but the
   decoy's combination is far rarer than chance (`observed < 0.3 × expected`). This
   catches two individually-fine attributes whose *pair* is structurally impossible
   (e.g. `slow timing + immediate monitoring` — real immediate-monitored boxes are never
   slow).
3. **Staleness gate** — certification is refused (`STALE_DATA`) if the real asset hasn't
   been observed within 1 day. A crashed collector must never certify anything.

### 2.3 Verdicts & correction

- **PASS** — decoy indistinguishable from the real asset.
- **CORRECTED** — drift found and repaired (bounded 50-iteration fix loop, one attribute
  at a time, targeting the real window's *conditional mode*; full check-set re-run after
  every fix).
- **UNSAFE** — drift is not correctable into tolerance (e.g. `monitoring_behavior` is
  non-correctable); the decoy must NOT be exposed.
- **INSUFFICIENT_DATA / STALE_DATA** — refuses to certify rather than guessing.
- Live-layer extras: **CORRECTED_PARTIAL** (a fix couldn't be applied on the live
  container), **UNREACHABLE**, **MIRRORING_REQUIRED** (real asset is down while the decoy
  answers — differential availability is itself a fingerprint).

### 2.4 The live loop (how the decoy state is maintained)

```
probe real asset ──► append to store (target="real-asset")
probe decoy      ──► observation dict
read 90-day real window from Postgres
verify(window, decoy_obs)          ← the single engine seam
if CORRECTED: map each fix → identity change → POST /admin/identity (token-protected)
re-probe decoy → re-verify         ← prove the fix landed
persist loop event
```

This runs **continuously on its own schedule** (not in response to probes), keeping the
decoy's resting state statistically identical to the real asset — which is what keeps a
hacker engaged long enough to be monitored.

---

## 3. The PRD and what it asked us to build

**Original PRD (already done before this session):** a verification engine comparing a
decoy against a real asset across the 5 declared attributes, a corrector with a 50-
iteration budget, a live loop, a store, and a Docker environment — plus hardening
(joint fingerprints, live escalation, outage handling, staleness gate, distinct TLS
CNs, gitignored control token, load-correlated delay). 60/60 tests, full demo working.

**New PRD (this session): an attacker-reconnaissance & target-selection simulation
layer** — simulate *why* an attacker picks this decoy and what they check once they
did, then feed the selection into the existing verification flow. **Scoping decision
(do not deviate):** no real routing, no multi-decoy fleet — the candidate pool is
constructed so the decoy *always* wins (decoys are designed to look most attractive).
The recon layer is narrative + scoring on top of the existing, unchanged engine.

| PRD requirement | Built as | Notes |
|---|---|---|
| Candidate generator (4–6 fake targets) | `recon/candidates.py` | Decoy candidate state **pulled live via `probe.py`**, never hardcoded; 4 synthetic fakes hardened by design (auth present, banner hidden, fresh patches) |
| Scoring function (weighted rules, human-readable reasons) | `recon/scoring.py` | No ML: banner +1, no auth +3, patch age +1/+2/+3 (>90/>180/>365 days), unreachable −1000 |
| Pre-attack observation (the 5 declared attributes) | `recon/observe.py` | Calls the **existing** `probe.py` — no second probing mechanism |
| Narrated CLI (3 phases) | `recon/demo_recon.py` | Phase 3 calls `engine.verify` exactly as `live.py` does |
| Tests: scoring determinism + end-to-end flow | `tests/test_recon.py` | 15 tests + 8 audit edge-case tests |
| Guard rails: don't modify core | honored | `engine.py`, `corrector.py`, `store.py` semantics untouched |

**The invariant that keeps everything in sync:** one baseline (the store's real-asset
window), one probe (`probe.py`), one verification seam (`engine.verify`) — every layer
converges on the same three.

---

## 4. The worked example (use this story throughout)

> **Setting:** a company runs `corp-web.internal` — its real, production web server.
> Next to it sits a honeypot: `old-admin-panel.internal`, a decoy mocking the same
> service. The decoy starts **deliberately drifted** (as if an operator misconfigured
> it): it serves an **old** Apache banner and slow responses.

### The real asset (baseline, from the store's 90-day window)

- Banner: `Apache/2.4.54 (Debian)` — seen constantly
- Patch cadence: within `[4, 187]` days
- Timing: fast/nominal, account age ~800 days, monitoring: immediate (and immediate
  boxes are *never* slow — structural constraint)

### The decoy as the attacker first sees it (drifted)

| Recon signal | Decoy | Real asset | Verdict |
|---|---|---|---|
| service_banner | `Apache/2.4.29` | `2.4.54` | **DRIFT** (seen 0/707 times) |
| patch_cadence_days | 730 | [4, 187] | **DRIFT** |
| timing_band | slow | fast/nominal | OK marginally… |
| JOINT fingerprint | slow + immediate | **never occurs** (observed 0, expected ~35) | **DRIFT** |
| account_age / monitoring | ~800 / immediate | in tolerance | OK |

### The full story in 4 acts (this is your demo)

**Act 1 — Reconnaissance (why the decoy wins).** The attacker enumerates 5 candidates.
The decoy scores **7** (banner exposed +1, no auth +3, outdated patch +3) vs **0** for
the hardened fakes. Reasons printed in plain English: *"outdated patch (>365 days)
suggests unmaintained asset; no authentication layer detected; service banner exposed."*
**Selected target: `old-admin-panel.internal`.** This is the *attractiveness design*
working as intended.

**Act 2 — Observation.** The attacker probes and records the 5 attributes — exactly
what `probe.py` measures: banner, timing, patch age, account age, monitoring.

**Act 3 — DecoyTell verification.** The engine compares the decoy against the real
window: the banner is unseen, the cadence is out of band, and `slow + immediate` is a
**joint fingerprint** (individually fine, structurally impossible). The engine proposes
three fixes that all read as an **upgrade**: banner `2.4.29 → 2.4.54`, cadence
`730 → 25.2` *(apply upstream security patch)*, timing `slow → fast`.

**Act 4 — Repair & re-verification.** The loop applies the fixes through the
token-protected control plane, re-probes, re-verifies → **PASS**. The attacker's *next*
recon run scores the decoy **4** (patch reason gone) and sees a stable, consistent
server. **Result: the attacker stays engaged with a server that is attractive enough to
attack and indistinguishable enough to not be detected — which is the entire point of a
honeypot.**

**Why "upgrade" matters:** the fix direction was deliberately flipped (decoy drifts
*old*, fixes patch it *up* to the real asset's current version) so a correction never
looks like an impossible downgrade to an observer.

---

## 5. The approach we followed

1. **Additive, not refactoring** — the recon layer is a wrapper; core modules were
   never rewritten. The PRD's instruction: *if you need to touch the engine, stop and
   report* — we never did.
2. **One probe, one seam, one baseline** — no competing probing logic, no second
   verification path, no hardcoded decoy state (pulled live).
3. **Transparency over cleverness** — rule-based scoring with human-readable reasons,
   not ML. Every point is explainable.
4. **Audit-driven hardening** — we actively attacked our own new layer: exit codes lied
   for failed verdicts (fixed), reachability semantics diverged from `live.py` (fixed),
   crafted `inf/nan` observations crashed the candidate builder (fixed), control token
   had a known fallback default (now fail-closed), no determinism test (added). Each
   flaw got a failing test first, then the fix — 8 new audit tests.
5. **Test discipline** — full suite after every change; zero regressions (60 original →
   71 now).

---

## 6. How we use Docker — and for what

| Purpose | How |
|---|---|
| **Isolate real vs decoy** | Two containers, same identity image: `real-asset` (port 8443, healthy identity) and `decoy` (port 8444, starts **deliberately drifted**) |
| **Engineer the observable surface** | The identity server reads `BANNER`, `TIMING_MS`, `MONITORING` env — so we can *create* a banner, a latency band, a monitoring profile that the probe then genuinely measures |
| **Backdated TLS certs** | The Dockerfile generates self-signed certs via `openssl ca -startdate`, giving real `notBefore` timestamps that the probe decodes into `account_age_days` |
| **Control plane** | `POST /admin/identity` on the container, token-protected (`.env`, fail-closed) — where the loop applies fixes to the served identity at runtime |
| **Baseline store** | `postgres:16` holds the rolling observation window (the ground truth for verification) |
| **Always-on services** | `api` (FastAPI dashboard on 8000) + `loop` (the scheduled verification loop) — robust to restarts, polls a control row |
| **Reproducible demo** | `docker compose up -d` → identical environment every time |

The containers are also the *honest framing*: banner, TLS-cert age and latency are
**genuine measurements** of engineered containers, not simulations inside the code.

---

## 7. The demo — how to present it

### Setup (once)

```powershell
docker compose up -d
python collect_live.py --seed        # seed the real-asset baseline into Postgres
docker compose restart decoy         # ensure decoy is in its drifted state (old banner, slow)
```

### The 4-act script (≈5 minutes) — say the bolded lines

```powershell
python recon/demo_recon.py           # ACT 1+2+3a
```
> **"An attacker enumerates candidates and scores them by attractiveness. The decoy
> wins — score 7, because it looks like an unpatched, auth-less admin panel. That's by
> design: decoys are meant to be the most attractive target. The attacker now observes
> it and finds: banner the real asset never serves, an unpatched cadence, and a joint
> fingerprint — slow timing with immediate monitoring, a combination the real asset can
> never produce. DecoyTell says CORRECTED — all fixes are upgrades."**

```powershell
python live_demo.py --cycles 1 --interval 5    # ACT 3b
```
> **"The loop applies those fixes through the token-protected control plane and
> re-verifies: CORRECTED → PASS. The decoy now matches the real asset."**

```powershell
python recon/demo_recon.py           # ACT 4
```
> **"Same attack, same selection — but now the decoy scores 4, everything is OK, no
> fingerprints. PASS. The attacker sees a stable, consistent server and stays engaged —
> exactly what we want from a honeypot."**

Optional live re-break (shows it's real, not scripted):
```powershell
python -c "from decoytell.control import apply; print(apply('localhost', 8444, {'banner': 'Apache/2.4.29 (Debian)', 'timing_ms': 1500}))"
python recon/demo_recon.py           # catches it again
```

### The hard questions — answer these honestly

| Question | Answer |
|---|---|
| "The correction is visible — wouldn't the attacker notice?" | Yes — that's why the posture is *consistent at scan time*. The loop repairs on its own schedule; the demo prints this note explicitly. Probing during a drift window would reveal the change — a known limitation, mitigated by keeping the window tiny and the loop fast. |
| "2.4.29 → 2.4.54 looks like a downgrade?" | It's the opposite — the decoy drifts **old** and gets **upgraded** to the real asset's current version, exactly what a real admin would do. |
| "The fake candidates don't exist on the network" | Correct — by PRD scope. The enumeration is a *simulation of the attacker's decision process* (attractiveness scoring), not real routing. |
| "The API has no auth" | Known limitation, deferred; the CLI demo flow (the one shown) doesn't use the API. Same honest-limitation style as `schema.py`. |
| "Why is `has_auth` not measured?" | It's a declared recon signal (the probed surface answers without challenge); documented in `candidates.py`. |
| "Why rule-based scoring, not ML?" | Reproducibility and transparency — the PRD demands the exact attributes responsible for disclosure. |

---

## 8. Where everything lives (code map)

| File | Role |
|---|---|
| `decoytell/schema.py` | The declared surface + all thresholds (the model) |
| `decoytell/generator.py` | Seeded synthesis of the real asset's observation history |
| `decoytell/engine.py` | `analyze` / `verify` / `run_scenario` — the pure verification seam |
| `decoytell/corrector.py` | Bounded 50-iteration scoped fix loop |
| `decoytell/probe.py` | The ONE probing instrument (banner, cadence, timing, cert age, monitoring) |
| `decoytell/store.py` | PostgreSQL rolling window + loop events/control |
| `decoytell/live.py` | The continuous verify→fix→re-verify loop |
| `decoytell/control.py` | Control-plane client (token, fail-closed) |
| `containers/identity/server.py` | The engineered identity server + `/admin/identity` |
| `recon/candidates.py` | Candidate pool (decoy from live probe + fakes) |
| `recon/scoring.py` | Rule-based attractiveness scoring + selection |
| `recon/observe.py` | Pre-attack observation (reuses probe.py) |
| `recon/demo_recon.py` | The narrated 3-phase demo + `run_demo` core |
| `tests/test_recon.py` | 23 tests: determinism, invariants, edge cases, end-to-end |

### Key commands

```powershell
python -m pytest tests/ -q            # 71 passed + 13 env-gated, 0 regressions
python recon/demo_recon.py            # recon → select → observe → verify
python live_demo.py --cycles 1 --interval 5
python demo.py                        # scripted core scenarios (s1–s5)
python verify_live.py                 # full live integration check
```

---

## 9. Summary in one paragraph

DecoyTell exists because a honeypot is only useful while an attacker believes it is
real. Attackers find targets by reconnaissance — scanning for old, unmaintained,
auth-less, exposed servers — and a decoy is deliberately designed to *win* that
selection (the new recon layer simulates and shows exactly why). Once engaged, the
attacker must never see the decoy drift from the real asset's observable behavior, or
they leave. DecoyTell's core verifies the decoy against the real asset across 5
declared attributes — individually and as joint fingerprints — auto-corrects drift as
an *upgrade*, refuses to certify unsafe or stale states, and runs continuously through
a live loop against real containers. The result: an attacker who stays on the decoy
long enough to be monitored, and a system that proves — with reasons, not guesses —
that the trap looks real.