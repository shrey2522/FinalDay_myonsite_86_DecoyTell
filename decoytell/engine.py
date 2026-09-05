"""Comparison engine: individual tolerance checks, the pairwise joint check,
and the single verification seam ``run_scenario``.

The engine is a pure, deterministic function of its inputs. All statistics are
computed over the real asset's recent window.
"""

import math
from collections import Counter
from itertools import combinations

from .schema import (
    ATTRIBUTES,
    THRESHOLDS,
    attribute_names,
    kind_of,
)
from .generator import generate_history
from .validate import validate_scenario
from .report import build_report
from .corrector import correct


def _percentile(sorted_vals, p):
    """Linear-interpolation percentile of an already-sorted sequence."""
    if not sorted_vals:
        return None
    n = len(sorted_vals)
    k = (n - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def _recent_window(history, days):
    return [o for o in history if o.days_ago <= days]


def analyze(attributes, history, decoy):
    """Compare the decoy tuple against the real asset's recent window.

    Returns a dict with per-attribute results, pairwise findings, and drift
    flags. ``insufficient`` is set when the window is too small to certify.
    """
    recent_days = THRESHOLDS["recent_window_days"]
    min_obs = THRESHOLDS["min_window_observations"]
    window = _recent_window(history, recent_days)

    attr_results = []
    pair_findings = []

    if len(window) < min_obs:
        for attr in attributes:
            attr_results.append(
                {
                    "name": attr["name"],
                    "kind": attr["kind"],
                    "unit": attr.get("unit"),
                    "decoy_value": decoy[attr["name"]],
                    "in_tolerance": None,
                    "no_window": True,
                }
            )
        return {
            "window_size": len(window),
            "attributes": attr_results,
            "pairs": pair_findings,
            "insufficient": True,
        }

    for attr in attributes:
        name = attr["name"]
        value = decoy[name]
        if attr["kind"] == "numeric":
            vals = sorted(getattr(o, name) for o in window)
            lo = _percentile(vals, THRESHOLDS["numeric_lower_percentile"])
            hi = _percentile(vals, THRESHOLDS["numeric_upper_percentile"])
            in_tolerance = lo <= value <= hi
            attr_results.append(
                {
                    "name": name,
                    "kind": "numeric",
                    "unit": attr.get("unit"),
                    "decoy_value": value,
                    "in_tolerance": in_tolerance,
                    "band": [round(lo, 1), round(hi, 1)],
                }
            )
        else:
            counts = Counter(getattr(o, name) for o in window)
            count = counts.get(value, 0)
            in_tolerance = count >= THRESHOLDS["categorical_min_count"]
            attr_results.append(
                {
                    "name": name,
                    "kind": "categorical",
                    "decoy_value": value,
                    "in_tolerance": in_tolerance,
                    "count": count,
                    "window_size": len(window),
                }
            )

    counts = {name: Counter(getattr(o, name) for o in window) for name in attribute_names()}
    n = len(window)
    for a, b in combinations(attribute_names(), 2):
        value_a = decoy[a]
        value_b = decoy[b]
        observed = sum(
            1 for o in window if getattr(o, a) == value_a and getattr(o, b) == value_b
        )
        expected = (
            n
            * counts[a].get(value_a, 0)
            / n
            * counts[b].get(value_b, 0)
            / n
        )
        is_fingerprint = observed == 0 and expected >= THRESHOLDS["joint_expected_min"]
        pair_findings.append(
            {
                "attr_a": a,
                "attr_b": b,
                "value_a": value_a,
                "value_b": value_b,
                "observed": observed,
                "expected": round(expected, 2),
                "fingerprint": is_fingerprint,
            }
        )

    has_drift = any(not r["in_tolerance"] for r in attr_results) or any(
        p["fingerprint"] for p in pair_findings
    )
    return {
        "window_size": n,
        "attributes": attr_results,
        "pairs": pair_findings,
        "insufficient": False,
        "has_drift": has_drift,
    }


def run_scenario(config):
    """The single verification seam.

    ``config`` is a scenario declaration (seed, decoy tuple, optional
    observations/expected_verdict). Returns the serializable verification
    report; raises ValueError on a malformed declaration.
    """
    validate_scenario(config)
    history = generate_history(config["seed"], config.get("observations"))
    analysis = analyze(ATTRIBUTES, history, config["decoy"])

    if analysis["insufficient"]:
        verdict = "INSUFFICIENT_DATA"
        corrections = []
        blocked = []
        final_analysis = analysis
    elif analysis["has_drift"]:
        verdict, corrections, final_decoy, blocked = correct(
            ATTRIBUTES, history, config["decoy"], analysis, analyze,
            config.get("correctable", {}),
        )
        final_analysis = analyze(ATTRIBUTES, history, final_decoy)
    else:
        verdict = "PASS"
        corrections = []
        blocked = []
        final_analysis = analysis

    return build_report(
        config, analysis, verdict, corrections, len(history),
        final_analysis=final_analysis, blocked=blocked,
    )