"""The declared comparison surface and thresholds.

The declared surface is the finite, fixed set of observable attributes the
comparison covers -- never an open-ended guess. Every threshold lives here so
the model is explicit and adjustable in one place.
"""

ATTRIBUTES = [
    {
        "name": "service_banner",
        "kind": "categorical",
        "correctable": True,
        "fix_action": "reconfigure server header/banner",
    },
    {
        "name": "patch_cadence_days",
        "kind": "numeric",
        "unit": "days",
        "correctable": True,
        "fix_action": "apply upstream security patch",
    },
    {
        "name": "timing_band",
        "kind": "categorical",
        "values": ["fast", "nominal", "slow"],
        "correctable": True,
        "fix_action": "adjust response throttling",
    },
    {
        "name": "account_age_days",
        "kind": "numeric",
        "unit": "days",
        "correctable": True,
        "fix_action": "update cert/account-age metadata",
    },
    {
        "name": "monitoring_behavior",
        "kind": "categorical",
        "values": ["immediate", "rate_limited", "silent"],
        "correctable": False,
        "fix_action": "host-level change, not editable",
    },
]

# Known limitation: reachability/uptime is deliberately NOT a 6th declared
# attribute. A decoy that keeps answering while the real asset is dark is
# itself an attacker-visible fingerprint; the live loop surfaces it as the
# MIRRORING_REQUIRED verdict (see decoytell/live.py) instead of silently
# passing it as part of the comparison model.
#
# Known limitation: the identity servers expose the management plane
# (POST /admin/identity) on the same public port as the probed surface. It is
# identical on real-asset and decoy, so it is an environment-level tell, not
# a decoy-vs-real inconsistency; separating it onto an internal port/interface
# is deferred (touches server.py + compose networking + all control-plane
# callers).

THRESHOLDS = {
    "recent_window_days": 90,
    "min_window_observations": 100,
    # History is sampled densely (~1.9 obs/day) on purpose: the 90-day recent
    # window must retain >= 100 observations for certification, so a sparse
    # history of a few hundred observations over 730 days would never certify.
    "numeric_lower_percentile": 0.05,
    "numeric_upper_percentile": 0.95,
    "categorical_min_count": 2,
    "categorical_min_share": 0.05,
    "joint_expected_min": 1.0,
    "joint_under_ratio": 0.3,
    # Certification requires the real asset to have been observed within this
    # many days; beyond it the window is stale and verify() returns
    # STALE_DATA. Resolution is capped at ~0.1 day by days_ago rounding;
    # sub-hour staleness detection would need wall-clock timestamps in the
    # engine (production version).
    "stale_window_max_days": 1.0,
    "correction_budget": 50,
    "default_observations": 1400,
    "history_span_days": 730,
}

SCHEMA_VERSION = "1.0"

ALLOWED_VERDICTS = {"PASS", "CORRECTED", "UNSAFE", "INSUFFICIENT_DATA"}


def attribute_names():
    return [a["name"] for a in ATTRIBUTES]


def get_attribute(name):
    for a in ATTRIBUTES:
        if a["name"] == name:
            return a
    raise KeyError("unknown attribute %r" % (name,))


def kind_of(name):
    return get_attribute(name)["kind"]