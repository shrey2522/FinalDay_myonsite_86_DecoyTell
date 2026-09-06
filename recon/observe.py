"""Pre-attack observation phase.

Once a target is selected, the attacker checks exactly the 5 declared
attributes DecoyTell already tracks. This module is presentational: the actual
measurement is performed by the existing ``decoytell.probe.probe`` — there is
no second, competing probing mechanism here.
"""

from decoytell.probe import probe as default_probe

OBSERVED_ATTRIBUTES = (
    "service_banner",
    "timing_band",
    "patch_cadence_days",
    "account_age_days",
    "monitoring_behavior",
)


def observe_target(host, port, probe=None, log=print):
    """Probe the selected target with the existing prober and narrate it.

    Returns the 5-field observation dict (the same shape the engine's
    ``verify`` consumes), so the caller can hand it straight to Phase 3
    without probing twice.
    """
    probe = probe or default_probe
    observation = probe(host, port)
    log("  attacker is now observing: %s"
        % ", ".join(
            "%s=%s" % (name, observation.get(name))
            for name in OBSERVED_ATTRIBUTES
        ))
    return observation