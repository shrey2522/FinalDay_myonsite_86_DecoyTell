"""Report assembly: the CLI table and the JSON proof artifact."""

import json

from .schema import THRESHOLDS, SCHEMA_VERSION

_REPORTED_THRESHOLDS = (
    "recent_window_days",
    "min_window_observations",
    "numeric_lower_percentile",
    "numeric_upper_percentile",
    "categorical_min_count",
    "joint_expected_min",
    "correction_budget",
)


def build_report(config, analysis, verdict, corrections, history_size=None,
                 final_analysis=None, blocked=None):
    return {
        "scenario_id": config["id"],
        "note": config.get("note", ""),
        "seed": config["seed"],
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
        "expected_verdict": config.get("expected_verdict"),
        "thresholds": {k: THRESHOLDS[k] for k in _REPORTED_THRESHOLDS},
        "history_size": history_size,
        "window_size": analysis["window_size"],
        "attributes": analysis["attributes"],
        "pairs": analysis["pairs"],
        "corrections": corrections,
        "blocked_attributes": blocked or [],
        "final": _analysis_summary(final_analysis),
    }


def _analysis_summary(analysis):
    if analysis is None:
        return None
    return {
        "window_size": analysis["window_size"],
        "attributes": analysis["attributes"],
        "pairs": analysis["pairs"],
    }


def _fmt(value):
    if isinstance(value, float):
        return ("%.1f" % value).rstrip("0").rstrip(".")
    return str(value)


def render_text(report):
    lines = []
    lines.append("=" * 64)
    lines.append("Scenario: %s" % report["scenario_id"])
    if report.get("note"):
        lines.append("Note:     %s" % report["note"])
    lines.append("-" * 64)
    lines.append(
        "Real asset: %d observations (seed %d); recent window = %d days -> %d obs"
        % (
            report["history_size"],
            report["seed"],
            report["thresholds"]["recent_window_days"],
            report["window_size"],
        )
    )
    lines.append("Decoy state (observed now):")

    for attr in report["attributes"]:
        name = attr["name"]
        value = _fmt(attr["decoy_value"])
        if attr.get("no_window"):
            mark = "--"
            detail = "no window data (cannot certify)"
        elif attr["kind"] == "numeric":
            lo, hi = _fmt(attr["band"][0]), _fmt(attr["band"][1])
            unit = " " + attr["unit"] if attr.get("unit") else ""
            detail = "in [%s, %s]%s" % (lo, hi, unit)
            mark = "OK " if attr["in_tolerance"] else "DRIFT"
        else:
            detail = "seen %d/%d" % (attr["count"], attr["window_size"])
            mark = "OK " if attr["in_tolerance"] else "DRIFT"
        lines.append(
            "  %-22s %-24s  %s  %s"
            % (name, value, mark, detail)
        )

    fingerprint_pairs = [p for p in report["pairs"] if p["fingerprint"]]
    if fingerprint_pairs:
        lines.append("JOINT check: fingerprint(s) detected")
        for p in fingerprint_pairs:
            lines.append(
                "  PAIR (%s=%s, %s=%s): observed %d, expected %.2f -> structurally absent"
                % (
                    p["attr_a"],
                    p["value_a"],
                    p["attr_b"],
                    p["value_b"],
                    p["observed"],
                    p["expected"],
                )
            )
    else:
        lines.append("JOINT check: no fingerprints across %d pairs" % len(report["pairs"]))

    for fix in report["corrections"]:
        lines.append("FIX %s: %s -> %s (%s)" % (fix["attribute"], fix["before"], fix["after"], fix["action"]))
        lines.append("  re-verified: %s" % fix["re_verified"])

    for name in report.get("blocked_attributes", []):
        lines.append("BLOCKED: %s is not correctable into tolerance" % name)

    final = report.get("final")
    if report["verdict"] == "INSUFFICIENT_DATA":
        lines.append(
            "INSUFFICIENT DATA: recent window has %d observations (< %d minimum) - cannot certify"
            % (report["window_size"], report["thresholds"]["min_window_observations"])
        )
    elif final is not None:
        final_failures = [a["name"] for a in final["attributes"] if not a["in_tolerance"]]
        final_pairs = [p for p in final["pairs"] if p["fingerprint"]]
        if not final_failures and not final_pairs:
            lines.append(
                "RE-VERIFY: all %d individual checks and all %d pairs OK -> PASSING"
                % (len(final["attributes"]), len(final["pairs"]))
            )

    lines.append("-" * 64)
    verdict = report["verdict"]
    expected = report.get("expected_verdict")
    suffix = " (expected: %s)" % expected if expected else ""
    lines.append("VERDICT: %s%s" % (verdict, suffix))
    lines.append("=" * 64)
    return "\n".join(lines)


def to_json(report):
    return json.dumps(report, indent=2)