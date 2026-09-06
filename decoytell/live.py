"""Real-time verification + correction loop (live layer).

Each cycle: probe the real asset and append its observation to the store,
probe the decoy, read the real asset's recent window from the store, verify
the decoy via the engine seam, apply any corrections to the decoy's served
identity through the control plane, re-probe and re-verify, and log the
cycle. Engine verdicts and semantics are untouched.
"""

import random
import time
from collections import Counter
from datetime import datetime, timezone

from .engine import verify

TIMING_MS_FOR_BAND = {"fast": 0.0, "nominal": 300.0, "slow": 1500.0}


def map_fix_to_identity(fix, window):
    """Translate an engine correction into identity changes a live server can
    actually apply. Returns None when the fix is not applicable on a live
    container (e.g. account age baked into a certificate, or monitoring
    behavior, which is host-level and declared non-correctable)."""
    attribute = fix["attribute"]
    after = fix["after"]
    if attribute == "service_banner":
        return {"banner": after}
    if attribute == "timing_band":
        return {"timing_ms": TIMING_MS_FOR_BAND[after]}
    if attribute == "patch_cadence_days":
        # Cadence is derived from the served software version on a live
        # server; pick the banner the real asset most commonly serves so the
        # implied cadence lands inside the real band.
        banners = Counter(o.service_banner for o in window)
        if not banners:
            return None
        return {"banner": banners.most_common(1)[0][0]}
    return None


def _unreachable(observation):
    return observation.get("service_banner") is None


def _inter_cycle_sleep(interval):
    """Pause between cycles with jitter so the probe cadence is not perfectly
    predictable to an external observer (I1); a drifted decoy stays exposed
    for at most ~1.5x the nominal interval instead of an exact, timed gap.
    interval <= 0 (tests, one-shot verify) returns immediately."""
    if interval <= 0:
        return
    time.sleep(interval * random.uniform(0.5, 1.5))


def run_loop(probe, store, control, real, decoy, interval=2.0, cycles=None,
             window_days=90, log=print, should_stop=None):
    """Run the scheduled verification loop.

    ``probe(host, port) -> observation dict``
    ``store``: object with append(obs, target), recent_window(days, target) and
        record_loop_event(...) (events are persisted when the store supports it)
    ``control``: callable(changes) -> bool, applying identity changes to the
        decoy's control plane
    ``real`` / ``decoy``: (host, port) tuples
    ``should_stop``: optional callable -> bool, checked before each cycle (the
        loop-service keeps running while the loop-control row says so)
    """
    events = []
    cycle = 0
    while cycles is None or cycle < cycles:
        if should_stop is not None and should_stop():
            break
        cycle += 1
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

        real_obs = probe(*real)
        if _unreachable(real_obs):
            # The real asset is dark while the decoy keeps answering:
            # differential availability is itself an attacker-visible
            # fingerprint. We do not mirror the outage here (out of scope);
            # we surface it loudly so it can never read as a clean pass.
            event = {"cycle": cycle, "timestamp": timestamp, "verdict": "MIRRORING_REQUIRED",
                     "recheck": "MIRRORING_REQUIRED", "fixes": [], "analysis": None}
            events.append(event)
            log(event)
            if cycles is None or cycle < cycles:
                _inter_cycle_sleep(interval)
            continue

        store.append(real_obs, target="real-asset")
        decoy_obs = probe(*decoy)

        if _unreachable(decoy_obs):
            event = {"cycle": cycle, "timestamp": timestamp, "verdict": "UNREACHABLE",
                     "recheck": "UNREACHABLE", "fixes": [], "analysis": None}
            events.append(event)
            log(event)
            if cycles is None or cycle < cycles:
                _inter_cycle_sleep(interval)
            continue

        # Persist the decoy observation too, so the store documents both
        # streams (real vs decoy) for the dashboard.
        store.append(decoy_obs, target="decoy")

        history = store.recent_window(days=window_days, target="real-asset")
        verdict, corrections, _analysis = verify(history, decoy_obs)

        applied = []
        if verdict == "CORRECTED":
            for fix in corrections:
                changes = map_fix_to_identity(fix, history)
                if changes is None:
                    applied.append({**fix, "applied": False,
                                    "reason": "not applicable on live container"})
                    continue
                ok = bool(control(changes))
                applied.append({**fix, "applied": ok})

        if applied:
            fresh = probe(*decoy)
            if _unreachable(fresh):
                recheck = "UNREACHABLE"
            else:
                recheck, _corrections2, _analysis2 = verify(
                    store.recent_window(days=window_days, target="real-asset"), fresh
                )
        else:
            recheck = verdict

        # A "CORRECTED" verdict is only trustworthy when every fix actually
        # landed on the live decoy. Un-applicable fixes (cert-baked account
        # age, host-level monitoring) leave the decoy drifted: escalate to
        # CORRECTED_PARTIAL so the state is never mistaken for a clean pass.
        if verdict == "CORRECTED" and any(not f.get("applied") for f in applied):
            verdict = "CORRECTED_PARTIAL"

        event = {"cycle": cycle, "timestamp": timestamp, "verdict": verdict,
                 "recheck": recheck, "fixes": applied, "analysis": _analysis}
        events.append(event)
        log(event)

        if hasattr(store, "record_loop_event"):
            store.record_loop_event(
                cycle=cycle, timestamp=timestamp, verdict=verdict,
                recheck=recheck, fixes=applied,
                real_obs=real_obs, decoy_obs=decoy_obs,
            )

        if cycles is None or cycle < cycles:
            _inter_cycle_sleep(interval)
    return events