"""Scoped auto-correction of drifted attributes.

Correction touches only failing attributes, one at a time, and re-verifies the
full check set after every fix (ADR-0004). Each correction targets the real
window's conditional mode given the decoy's other attributes, so the decoy is
made to look like a real box of its type -- never a full rebuild.
"""

import statistics
from collections import Counter

from .schema import THRESHOLDS, attribute_names, kind_of


def failing_attributes(analysis):
    """The attributes responsible for drift, in declared-surface order."""
    failing = set()
    for result in analysis["attributes"]:
        if not result["in_tolerance"]:
            failing.add(result["name"])
    for finding in analysis["pairs"]:
        if finding["fingerprint"]:
            failing.add(finding["attr_a"])
            failing.add(finding["attr_b"])
    return [name for name in attribute_names() if name in failing]


def _mode(values):
    counts = Counter(values)
    top = max(counts.values())
    return min(v for v, c in counts.items() if c == top)


def _fingerprint_partner(analysis, target):
    for finding in analysis["pairs"]:
        if finding["fingerprint"] and target in (finding["attr_a"], finding["attr_b"]):
            return finding["attr_b"] if finding["attr_a"] == target else finding["attr_a"]
    return None


def _conditioning_pool(window, decoy, target, partner, passing_categoricals):
    """Progressive relaxation: exact other-passing-categorical match, then
    partner, then the whole window. Each level must have enough observations
    to be a meaningful reference. Only attributes that are currently passing
    marginally are used for the exact match, so the correction target is not
    biased by attributes that are themselves still drifted."""
    exact = []
    for obs in window:
        if partner is not None and getattr(obs, partner) != decoy[partner]:
            continue
        matched = True
        for name in passing_categoricals:
            if name == target or name == partner:
                continue
            if getattr(obs, name) != decoy[name]:
                matched = False
                break
        if matched:
            exact.append(obs)
    if len(exact) >= 2:
        return exact

    if partner is not None:
        partner_pool = [obs for obs in window if getattr(obs, partner) == decoy[partner]]
        if len(partner_pool) >= 2:
            return partner_pool

    return window


def correction_target(analysis, window, decoy, target):
    partner = _fingerprint_partner(analysis, target)
    failing_marginal = {
        result["name"]
        for result in analysis["attributes"]
        if result["in_tolerance"] is False
    }
    passing_categoricals = [
        name
        for name in attribute_names()
        if kind_of(name) == "categorical" and name not in failing_marginal
    ]
    pool = _conditioning_pool(window, decoy, target, partner, passing_categoricals)
    values = [getattr(obs, target) for obs in pool]
    if not values:
        return None
    if kind_of(target) == "numeric":
        return statistics.median(values)
    return _mode(values)


def _recent_window(history):
    return [obs for obs in history if obs.days_ago <= THRESHOLDS["recent_window_days"]]


def correct(attributes, history, decoy, analysis, analyze_fn, correctable_overrides=None):
    """Repair drift in place. Returns (verdict, corrections, final_decoy,
    blocked_attributes).

    ``analyze_fn`` is injected to avoid a circular import; it re-runs the full
    check set after every fix.
    """
    overrides = correctable_overrides or {}
    current = dict(decoy)
    corrections = []
    window = _recent_window(history)
    budget = THRESHOLDS["correction_budget"]

    for _ in range(budget):
        analysis = analyze_fn(attributes, history, current)
        if analysis["insufficient"]:
            return "INSUFFICIENT_DATA", corrections, current, []
        if not analysis["has_drift"]:
            return ("CORRECTED" if corrections else "PASS"), corrections, current, []

        failing = failing_attributes(analysis)
        by_name = {a["name"]: a for a in attributes}
        target = None
        for name in failing:
            if overrides.get(name, by_name[name]["correctable"]):
                target = name
                break
        if target is None:
            return "UNSAFE", corrections, current, failing

        new_value = correction_target(analysis, window, current, target)
        before = current[target]
        if new_value is None or new_value == before:
            return "UNSAFE", corrections, current, [target]

        current[target] = new_value
        post = analyze_fn(attributes, history, current)
        re_verified = (not post["insufficient"]) and (not post["has_drift"])
        corrections.append(
            {
                "attribute": target,
                "before": before,
                "after": new_value,
                "action": by_name[target]["fix_action"],
                "re_verified": re_verified,
            }
        )

    return "UNSAFE", corrections, current, failing_attributes(analysis)