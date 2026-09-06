# DecoyTell — Judge Demo Runbook

> Follow top to bottom. Each step: **COMMAND → what you say → what you should see.**
> Total time: ~6 minutes. If something looks wrong, use the Fallbacks section — don't
> improvise.

---

## PHASE 0 — Pre-demo check (30 seconds, do this BEFORE judges arrive)

```powershell
docker compose ps --format "{{.Name}} {{.State}}"
```
All 5 containers must say `running` (loop may show `restarting` — that's normal, see guide §8).

If any are down:
```powershell
docker compose up -d
```

---

## PHASE 1 — Reset to the canonical story state (60 seconds)

```powershell
docker compose restart decoy
python collect_live.py --seed
```
**Say:** *"I'm resetting the decoy into its drifted state — it's serving an OLD Apache
banner and slow responses, as if an operator misconfigured it — and seeding the real
asset's baseline observation history into the store."*

**Expect:** decoy restarts; seed prints `real-asset recent window size: <number>`.

> Verify the decoy is actually drifted (if not, rerun the restart):
> ```powershell
> python -c "from decoytell.probe import probe; print(probe('localhost',8444)['service_banner'])"
> # -> Apache/2.4.29 (Debian)
> ```

---

## PHASE 2 — Act 1: Attacker recon selects the decoy; verification catches drift (60 seconds)

```powershell
python recon/demo_recon.py
```

**Say (point at the output as you talk):**
- *"This is the attacker's decision process. Phase 1 — reconnaissance: five candidate
  targets are scored by attractiveness. The decoy wins with score 7: outdated patch,
  no authentication layer, exposed banner. That's by design — a decoy must look like
  the most attractive target."*
- *"Phase 2 — pre-attack observation: the attacker measures exactly the five
  attributes our system tracks."*
- *"Phase 3 — DecoyTell verification against the real asset's baseline: the banner is
  never served by the real asset, the patch cadence is out of band, and there's a
  joint fingerprint — slow timing combined with immediate monitoring never occurs in
  the real asset's history."*

**Expect:** `VERDICT: CORRECTED` with three upgrade fixes:
`Apache/2.4.29 -> Apache/2.4.54`, `730.0 -> 25.2 (apply upstream security patch)`,
`slow -> fast`.

**Emphasize:** *"Every fix is an upgrade — the decoy drifts OLD and gets patched UP to
the real asset's current version, exactly what a real admin would do."*

---

## PHASE 3 — Act 2: The loop applies the fixes (60 seconds)

```powershell
python live_demo.py --cycles 1 --interval 5
```

**Say:** *"This is the continuous loop in action: probe → verify → apply fixes through
the token-protected control plane → re-probe → re-verify."*

**Expect:** `VERDICT: CORRECTED -> PASS`, all fixes marked `[applied]`.

---

## PHASE 4 — Act 3: Re-run the attack — the decoy now holds up (60 seconds)

```powershell
python recon/demo_recon.py
```

**Say:**
- *"Same attack, same selection — but now the decoy scores 4: the outdated-patch
  reason is gone because it was patched."*
- *"Every attribute is OK, no joint fingerprints. VERDICT: PASS. The decoy is
  statistically indistinguishable from the real asset."*
- *"This is the whole point: the attacker picks the decoy because it looks attractive,
  but never discovers it's fake — so they stay engaged and we monitor them."*

**Expect:** `VERDICT: PASS`, all attributes `OK`, `RESULT: ... held up under DecoyTell
verification`.

---

## PHASE 5 — Optional live re-break (proves it's real, not scripted) (60 seconds)

```powershell
python -c "from decoytell.control import apply; print('drift injected:', apply('localhost', 8444, {'banner': 'Apache/2.4.29 (Debian)', 'timing_ms': 1500}))"
python recon/demo_recon.py
```

**Say:** *"I just misconfigured the decoy live through the control plane — watch the
next run catch and name the drift again."*

**Expect:** `drift injected: True`, then `VERDICT: CORRECTED` again.

---

## PHASE 6 — Closing: the credibility line (60 seconds)

```powershell
python -m pytest tests/ -q
```

**Say:** *"71 tests passing, 13 environment-gated, zero regressions — the original 60
tests of the hardened core still pass untouched, plus the new recon layer's tests."*

---

## Fallbacks (if something breaks — do NOT panic, say one of these)

| Symptom | Cause | Fix |
|---|---|---|
| Phase 2 shows `UNREACHABLE` | Decoy container down | `docker compose up -d`, then restart Phase 1 |
| Phase 2 shows `PASS` instead of `CORRECTED` | Decoy wasn't reset to drifted | `docker compose restart decoy` → redo Phase 1 |
| Seed prints a connection error | Postgres not up yet | `docker compose up -d`, wait 10s, retry seed |
| Demo exits with code 1 after UNSAFE | Decoy observation malformed/unreachable | Check `docker compose ps`; restart decoy; redo Phase 1 |
| Judge asks "is this scripted?" | — | Run PHASE 5 — the live re-break is your proof |

---

## One-liner for the judges

> "An attacker finds the decoy because it's designed to look like the juiciest target.
> DecoyTell keeps it looking exactly like the real server — and proves it with reasons,
> not guesses — so the attacker stays engaged and we stay aware."