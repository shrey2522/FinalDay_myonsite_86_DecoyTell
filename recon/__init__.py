"""Attacker reconnaissance & target-selection simulation layer.

Additive wrapper on DecoyTell: simulates why an attacker would pick the decoy
out of a candidate pool and what they would check once they did. Purely
narrative + scoring; the only real probing/verification that runs is the
existing ``decoytell.probe`` / ``decoytell.engine`` machinery.

Public seams: ``candidates.build_candidates``, ``scoring.select_target``,
``observe.observe_target``, ``demo_recon.run_demo``.
"""

from .candidates import build_candidates
from .observe import observe_target
from .scoring import rank_candidates, select_target

__all__ = ["build_candidates", "rank_candidates", "select_target", "observe_target"]