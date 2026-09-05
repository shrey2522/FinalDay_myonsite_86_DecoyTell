"""Input guards for scenario declarations.

A malformed declared model must never silently pass or mislead: it is
rejected loudly with a clear message.
"""

from .schema import attribute_names, get_attribute, kind_of, ALLOWED_VERDICTS


def validate_scenario(scenario):
    errors = []
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be a JSON object")

    if "id" not in scenario or not isinstance(scenario["id"], str):
        errors.append("missing string 'id'")

    seed = scenario.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        errors.append("'seed' must be an integer")

    decoy = scenario.get("decoy")
    if not isinstance(decoy, dict):
        errors.append("missing 'decoy' object")
    else:
        known = set(attribute_names())
        for name in known:
            if name not in decoy:
                errors.append("decoy is missing attribute %r" % (name,))
        for name, value in decoy.items():
            if name not in known:
                errors.append("decoy has unknown attribute %r" % (name,))
                continue
            kind = kind_of(name)
            if kind == "numeric":
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    errors.append("attribute %r must be numeric" % (name,))
            else:
                if not isinstance(value, str):
                    errors.append("attribute %r must be a string" % (name,))
                elif "values" in get_attribute(name) and value not in get_attribute(name)["values"]:
                    errors.append(
                        "attribute %r has undeclared value %r" % (name, value)
                    )

    observations = scenario.get("observations")
    if observations is not None:
        if not isinstance(observations, int) or observations < 1:
            errors.append("'observations' must be a positive integer")

    expected = scenario.get("expected_verdict")
    if expected is not None and expected not in ALLOWED_VERDICTS:
        errors.append("'expected_verdict' must be one of %s" % sorted(ALLOWED_VERDICTS))

    if errors:
        raise ValueError("invalid scenario: " + "; ".join(errors))