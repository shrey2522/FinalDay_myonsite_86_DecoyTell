"""Continuous observation loop over a simulated live real asset.

Demonstrates how DecoyTell works against a live server that changes over
time: each cycle advances time (old observations fall out of the recent
window), a new observation of the real asset is collected, the decoy is
verified against the current window, and any drift the robot detects is
corrected in place and re-verified.
"""

import random
from dataclasses import dataclass

from .engine import verify
from .generator import (
    Observation,
    _sample_categorical,
    P_MONITORING,
    TIMING_GIVEN_MONITORING,
)


@dataclass
class LiveDecoy:
    state: dict


class SimulatedLiveAsset:
    """A live real asset: emits one observation per cycle and its observable
    state can change (here: it applies a security patch at ``patch_cycle``)."""

    def __init__(self, seed, patch_cycle=5):
        self.rng = random.Random(seed + 101)
        self.patch_cycle = patch_cycle
        self.cycle = 0
        self.history = _fresh_history(seed)

    def _advance_time(self):
        self.history = [
            Observation(
                days_ago=obs.days_ago + 1,
                service_banner=obs.service_banner,
                patch_cadence_days=obs.patch_cadence_days,
                timing_band=obs.timing_band,
                account_age_days=obs.account_age_days,
                monitoring_behavior=obs.monitoring_behavior,
            )
            for obs in self.history
        ]

    def collect(self):
        """Advance one cycle: time moves, the real asset is observed now.
        Two observations are collected per cycle to keep the recent window at
        or above the minimum (matching the generator's sampling density)."""
        self._advance_time()
        self.history.append(self._next_observation())
        self.history.append(self._next_observation())
        self.cycle += 1

    def _next_observation(self):
        cycle = self.cycle
        if cycle < self.patch_cycle:
            banner = "Apache/2.4.54 (Debian)"
            release = 60
        else:
            banner = "Apache/2.4.55 (Debian)"
            release = max(1, cycle - self.patch_cycle + 1)

        monitoring = _sample_categorical(self.rng, P_MONITORING)
        timing = _sample_categorical(self.rng, TIMING_GIVEN_MONITORING[monitoring])
        return Observation(
            days_ago=0.0,
            service_banner=banner,
            patch_cadence_days=round(1.0 + self.rng.uniform(0.0, release * 0.6), 1),
            timing_band=timing,
            account_age_days=round(800 + self.rng.uniform(-15, 45), 1) + cycle,
            monitoring_behavior=monitoring,
        )


def _fresh_history(seed):
    from .generator import generate_history

    return generate_history(seed)


def observe(seed, decoy_state, duration=100, patch_cycle=5):
    """Run the continuous loop. Returns (final_decoy_state, events) where each
    event records the cycle, verdict, and any corrections the robot applied."""
    asset = SimulatedLiveAsset(seed, patch_cycle=patch_cycle)
    decoy = dict(decoy_state)
    events = []

    for cycle in range(duration):
        asset.collect()
        verdict, corrections, _analysis = verify(asset.history, decoy)
        applied = []
        for fix in corrections:
            decoy[fix["attribute"]] = fix["after"]
            applied.append(fix)
        if applied:
            recheck, _corrections2, _analysis = verify(asset.history, decoy)
        else:
            recheck = verdict
        events.append(
            {
                "cycle": cycle + 1,
                "verdict": verdict,
                "corrections": applied,
                "recheck": recheck,
            }
        )
    return decoy, events