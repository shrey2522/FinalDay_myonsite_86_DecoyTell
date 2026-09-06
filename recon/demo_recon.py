"""Narrated reconnaissance -> selection -> observation -> verification demo.

PHASE 1  reconnaissance: enumerate the candidate pool, score each candidate
         with human-readable reasons, pick the most attractive reachable one.
PHASE 2  pre-attack observation: the attacker probes the selected target with
         the existing prober (decoytell.probe.probe - the only probing that
         exists in this codebase).
PHASE 3  DecoyTell verification: the existing engine seam (decoytell.engine
         .verify) is called as-is against the real-asset baseline - the store
         window when a live store is available (the same call live.py makes),
         or a generated history otherwise. No core module is modified.

Usage:
    python recon/demo_recon.py                 # store-backed when reachable
    python recon/demo_recon.py --no-store      # generated-baseline offline mode

Tests exercise ``run_demo`` directly with an injected prober and window.
"""

import argparse
import os

if __package__ in (None, ""):
    # Run as a script: python recon/demo_recon.py. Make the project root
    # importable, then load the same modules through their package names.
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decoytell.engine import verify
from decoytell.generator import generate_history
from decoytell.probe import probe as default_probe
from decoytell.store import ObservationStore, psycopg

from recon.candidates import build_candidates
from recon.observe import observe_target
from recon.scoring import rank_candidates, score_of, select_target

DEFAULT_DSN = os.environ.get(
    "DECOYTELL_DSN", "postgres://decoytell:decoytell@localhost:5433/decoytell"
)

RESULT_TEXT = {
    "PASS": "held up under DecoyTell verification",
    "CORRECTED": "was corrected back into tolerance",
    "UNSAFE": "flagged unsafe - do not expose as-is",
    "INSUFFICIENT_DATA": "could not be certified (insufficient baseline)",
    "STALE_DATA": "could not be certified (baseline window is stale)",
}

_PHASE_SEP = "-" * 70

OBSERVED_KEYS = (
    "service_banner",
    "patch_cadence_days",
    "timing_band",
    "account_age_days",
    "monitoring_behavior",
)

# Verdicts that count as a successful outcome, matching live_demo.py's
# semantics: anything else means the decoy was NOT certified.
OK_VERDICTS = {"PASS", "CORRECTED"}


def _unreachable(observation):
    return observation.get("service_banner") is None


def _render_candidates(ranked, log):
    log("  %-24s %-7s %-9s %-9s %-5s %-9s %-6s %s"
        % ("candidate", "banner", "patch_age", "reach", "auth", "style",
           "score", "reasons"))
    for candidate, score, reasons in ranked:
        patch = "-" if candidate.patch_age_days is None else str(candidate.patch_age_days)
        log("  %-24s %-7s %-9s %-9s %-5s %-9s %-6s %s"
            % (candidate.name,
               "yes" if candidate.banner_visible else "no",
               patch,
               "yes" if candidate.reachable else "no",
               "yes" if candidate.has_auth else "no",
               candidate.subdomain_style,
               score,
               "; ".join(reasons)))


def _render_verification(verdict, corrections, analysis, log):
    if not analysis or analysis.get("insufficient"):
        log("  baseline window too small to certify (insufficient data)")
        return
    log("  baseline window: %d observations" % analysis["window_size"])
    for r in analysis["attributes"]:
        if r["kind"] == "numeric":
            lo, hi = r["band"]
            real_col = "[%s, %s]" % (lo, hi)
        else:
            real_col = "seen %d/%d" % (r["count"], r["window_size"])
        status = "OK" if r["in_tolerance"] else "DRIFT"
        log("    %-20s real %-24s decoy %-24s %s"
            % (r["name"], real_col, str(r["decoy_value"]), status))
    fingerprints = [p for p in analysis.get("pairs", []) if p["fingerprint"]]
    if fingerprints:
        for p in fingerprints:
            log("    JOINT fingerprint: %s=%s + %s=%s -> observed %d, expected %s"
                % (p["attr_a"], p["value_a"], p["attr_b"], p["value_b"],
                   p["observed"], p["expected"]))
    for fix in corrections:
        log("    fix %s: %s -> %s (%s)" % (fix["attribute"], fix["before"],
                                           fix["after"], fix["action"]))


def run_demo(probe_fn=None, real_window=None, store=None,
             decoy_host="localhost", decoy_port=8444,
             real_host="localhost", real_port=8443, log=print):
    """Run the full narrated flow. Returns a result dict with ``exit_code``.

    ``probe_fn(host, port) -> observation`` defaults to the existing prober.
    Exactly one of ``real_window`` (list of engine Observations) or ``store``
    (recent_window/append adapter) must be provided for Phase 3.
    """
    probe_fn = probe_fn or default_probe
    if real_window is None and store is None:
        raise ValueError("run_demo requires real_window or store for Phase 3")

    result = {"phases": [], "exit_code": 0}

    log("PHASE 1: RECONNAISSANCE")
    log("  Enumerating candidates...")
    candidates = build_candidates(None, probe=probe_fn,
                                  decoy_host=decoy_host, decoy_port=decoy_port)
    ranked = rank_candidates(candidates)
    _render_candidates(ranked, log)
    selected, _ = select_target(candidates)
    if selected is None:
        log("  -> no reachable candidate to attack")
        result["exit_code"] = 1
        return result
    score, reasons = score_of(ranked, selected)
    log("  -> Selected target: %s (score: %s)" % (selected.name, score))
    log("    Reasons: %s" % "; ".join(reasons))
    result["selected"] = selected
    result["phases"].append("recon")

    log("")
    log("PHASE 2: PRE-ATTACK OBSERVATION")
    log("  Attacker probing selected target...")
    observation = observe_target(decoy_host, decoy_port, probe=probe_fn, log=log)
    result["observation"] = observation
    result["phases"].append("observe")
    if _unreachable(observation):
        log("  Selected target is UNREACHABLE - nothing to verify")
        result["verdict"] = "UNREACHABLE"
        result["exit_code"] = 1
        return result
    missing = [k for k in OBSERVED_KEYS if k not in observation]
    if missing:
        log("  Observation missing fields %s - cannot verify" % missing)
        result["verdict"] = "MALFORMED_OBSERVATION"
        result["exit_code"] = 1
        return result

    log("")
    log("PHASE 3: DECOYTELL VERIFICATION (existing engine, called as-is)")
    log("  Running consistency verification against real-asset baseline...")
    if store is not None:
        real_obs = probe_fn(real_host, real_port)
        if _unreachable(real_obs):
            log("  MIRRORING_REQUIRED: real asset is DOWN while the selected")
            log("  target answers - differential availability is a fingerprint")
            log("  (outage mirroring not implemented); no verification run.")
            result["verdict"] = "MIRRORING_REQUIRED"
            result["exit_code"] = 1
            return result
        store.append(real_obs, target="real-asset")
        window = store.recent_window(days=90, target="real-asset")
    else:
        window = real_window
    verdict, corrections, analysis = verify(window, observation)
    log("  VERDICT: %s" % verdict)
    if verdict == "CORRECTED":
        log("  note: this repair is scheduled loop maintenance (live.py), not a")
        log("  response to the probe above - a target probed DURING the drift")
        log("  window would see the change, and that is a real tell. The")
        log("  operational posture is a decoy that is already consistent, so no")
        log("  change is ever observable (see the PASS case).")
    _render_verification(verdict, corrections, analysis, log)
    result["verdict"] = verdict
    result["corrections"] = corrections
    result["analysis"] = analysis
    result["phases"].append("verify")
    if verdict not in OK_VERDICTS:
        result["exit_code"] = 1

    log("")
    log("RESULT: attacker's reconnaissance-selected target (%s) %s"
        % (selected.name, RESULT_TEXT.get(verdict, "status: %s" % verdict)))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="recon -> select -> observe -> verify")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--no-store", action="store_true",
                        help="use a generated baseline instead of the live store")
    parser.add_argument("--real-host", default=os.environ.get("DECOYTELL_REAL_HOST", "localhost"))
    parser.add_argument("--real-port", type=int, default=int(os.environ.get("DECOYTELL_REAL_PORT", "8443")))
    parser.add_argument("--decoy-host", default=os.environ.get("DECOYTELL_DECOY_HOST", "localhost"))
    parser.add_argument("--decoy-port", type=int, default=int(os.environ.get("DECOYTELL_DECOY_PORT", "8444")))
    parser.add_argument("--seed", type=int, default=3001,
                        help="seed for the generated baseline (offline mode)")
    args = parser.parse_args(argv)

    store = None
    if not args.no_store:
        if psycopg is None:
            print("psycopg not installed - falling back to generated baseline")
        else:
            try:
                store = ObservationStore(psycopg.connect(args.dsn))
                store.init_schema()
            except Exception as exc:
                print("store unreachable (%s) - falling back to generated baseline" % exc)

    result = run_demo(
        store=store,
        real_window=None if store is not None else generate_history(args.seed),
        decoy_host=args.decoy_host,
        decoy_port=args.decoy_port,
        real_host=args.real_host,
        real_port=args.real_port,
    )
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())