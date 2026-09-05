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

THRESHOLDS = {
    "recent_window_days": 90,
    "min_window_observations": 100,
    "numeric_lower_percentile": 0.05,
    "numeric_upper_percentile": 0.95,
    "categorical_min_count": 2,
    "joint_expected_min": 1.0,
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