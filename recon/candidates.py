"""Candidate pool: synthetic fake targets + the one live decoy.

The pool is intentionally constructed so the decoy is the most attractive
reconnaissance target: the fake candidates are hardened by design (auth layer
present, banner hidden, freshly patched) while the decoy's own signals are
derived from its live state via the existing prober, so the demo reflects
whatever the decoy actually looks like right now.

There is exactly ONE real decoy in the fleet (per the scoping decision); the
fake candidates exist purely so the selection step has a narrative pool to
rank against. Nothing here routes real traffic or changes what the decoy
serves.
"""

import dataclasses
import math

from decoytell.probe import probe as default_probe

# (name, banner_visible, patch_age_days, reachable, has_auth, subdomain_style)
# All fakes are reachable but unattractive: fresh patches, auth required,
# banner suppressed. This makes the decoy win on attractiveness alone, never
# on being the only thing that answers.
_FAKE_SPECS = [
    ("api-v1-legacy.internal", False, 21, True, True, "legacy"),
    ("staging-backup.internal", False, 42, True, True, "staging"),
    ("metrics-dashboard.internal", False, 63, True, True, "internal"),
    ("cdn-origin.internal", False, 14, True, True, "internal"),
]

# Narrative subdomain style for the decoy candidate; it is purely cosmetic
# (never scored) but reads plausibly as an unmaintained admin surface.
DECOY_NAME = "old-admin-panel.internal"
DECOY_STYLE = "admin"

RECON_FIELDS = (
    "name",
    "banner_visible",
    "patch_age_days",
    "reachable",
    "has_auth",
    "subdomain_style",
    "is_decoy",
)


@dataclasses.dataclass(frozen=True)
class Candidate:
    """One reconnaissance-visible target in the pool."""

    name: str
    banner_visible: bool
    patch_age_days: int | None
    reachable: bool
    has_auth: bool
    subdomain_style: str
    is_decoy: bool = False


def _to_patch_age(patch_age):
    """Coerce a probed patch cadence to an int, tolerating garbage input.

    A crafted/tampered observation could carry non-finite values (inf/nan);
    ``int(round(inf))`` raises OverflowError and ``int(round(nan))`` raises
    ValueError. Non-finite or non-numeric input degrades to None (unknown
    patch age) instead of crashing the recon layer.
    """
    if patch_age is None:
        return None
    try:
        value = float(patch_age)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return int(round(value))


def _decoy_from_observation(observation):
    """Map a live 5-field probe observation onto recon-visible signals.

    banner_visible / reachable / patch_age_days come straight from the probed
    surface (the only true measurements). Reachability uses the exact same
    semantics as the live loop (live.py's ``_unreachable``: banner is None),
    so a host that answers without a Server header is still reachable. has_auth
    is a declared property of the simulated recon: the probed identity surface
    answers GET / without any challenge, so the attacker records "no
    authentication layer detected".
    """
    banner = observation.get("service_banner")
    return Candidate(
        name=DECOY_NAME,
        banner_visible=bool(banner and str(banner).strip()),
        patch_age_days=_to_patch_age(observation.get("patch_cadence_days")),
        reachable=banner is not None,
        has_auth=False,
        subdomain_style=DECOY_STYLE,
        is_decoy=True,
    )


def build_candidates(observation, probe=None, decoy_host="localhost", decoy_port=8444):
    """Build the fixed pool of 4-6 candidates.

    ``observation`` is a decoy observation already collected by the existing
    prober (dict with the 5 declared attributes). When it is None the decoy
    candidate is built from a live probe of ``(decoy_host, decoy_port)`` using
    ``decoytell.probe.probe``. Returns a list of ``Candidate`` (the decoy
    first, fakes after).
    """
    if observation is None:
        probe = probe or default_probe
        observation = probe(decoy_host, decoy_port)
    decoy = _decoy_from_observation(observation)
    fakes = [
        Candidate(*spec)
        for spec in _FAKE_SPECS
    ]
    return [decoy, *fakes]