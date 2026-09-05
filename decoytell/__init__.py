"""DecoyTell: bounded deception-surface consistency verification.

Public seam: ``decoytell.engine.run_scenario(config) -> report``.
"""

from .engine import run_scenario

__all__ = ["run_scenario"]
__version__ = "0.1.0"