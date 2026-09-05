"""Seeded, parametric synthesis of a matched real asset's observation history.

The real asset is a time-ordered series of observations over a span of days.
The generator encodes the dependencies that make the joint check meaningful:
a new banner implies a short patch cadence; immediate boxes are never slow and
silent boxes are never fast; account age tracks the asset's birth.
"""

import random
from dataclasses import dataclass

from .schema import THRESHOLDS

# (earliest_days_ago, latest_days_ago, banner, release_days_ago)
BANNER_PHASES = [
    (730, 365, "Apache/2.4.29 (Debian)", 730),
    (365, 60, "Apache/2.4.41 (Debian)", 365),
    (60, 0, "Apache/2.4.54 (Debian)", 60),
]

ACCOUNT_AGE_BIRTH = 800
ACCOUNT_AGE_JITTER = (-15.0, 45.0)

# Marginal distributions for the observation-level attributes.
P_MONITORING = (("immediate", 0.60), ("rate_limited", 0.30), ("silent", 0.10))
# timing_band sampled conditional on monitoring_behavior: the structural
# constraint that produces joint fingerprints.
TIMING_GIVEN_MONITORING = {
    "immediate": (("fast", 0.80), ("nominal", 0.20)),
    "rate_limited": (("fast", 0.30), ("nominal", 0.50), ("slow", 0.20)),
    "silent": (("nominal", 0.40), ("slow", 0.60)),
}


@dataclass(frozen=True)
class Observation:
    days_ago: float
    service_banner: str
    patch_cadence_days: float
    timing_band: str
    account_age_days: float
    monitoring_behavior: str


def _phase_for(days_ago):
    for earliest, latest, banner, release in BANNER_PHASES:
        if earliest >= days_ago > latest:
            return banner, release
    raise ValueError("observation outside the declared span: %r" % (days_ago,))


def _sample_categorical(rng, pairs):
    draw = rng.random()
    cumulative = 0.0
    for value, weight in pairs:
        cumulative += weight
        if draw < cumulative:
            return value
    return pairs[-1][0]


def generate_history(seed, observations=None, span_days=None):
    if observations is None:
        observations = THRESHOLDS["default_observations"]
    if span_days is None:
        span_days = THRESHOLDS["history_span_days"]
    rng = random.Random(seed)

    history = []
    for i in range(observations):
        days_ago = span_days * (observations - i - 0.5) / observations
        banner, release = _phase_for(days_ago)

        account_age = ACCOUNT_AGE_BIRTH + rng.uniform(*ACCOUNT_AGE_JITTER)

        monitoring = _sample_categorical(rng, P_MONITORING)
        timing = _sample_categorical(rng, TIMING_GIVEN_MONITORING[monitoring])

        # Newer banner => shorter time since the last security patch.
        patch_cadence = 1.0 + rng.uniform(0.0, release * 0.6)

        history.append(
            Observation(
                days_ago=round(days_ago, 1),
                service_banner=banner,
                patch_cadence_days=round(patch_cadence, 1),
                timing_band=timing,
                account_age_days=round(account_age, 1),
                monitoring_behavior=monitoring,
            )
        )
    return history