"""Run the real-time verification + correction loop against the Docker stack.

The decoy container is started as a flawed clone (banner the real asset never
shows + a joint fingerprint); the loop catches the drift in cycle 1, applies
corrections to the decoy's served identity via the management plane, and
stays green afterwards.

With ``--rebreak-every N`` the demo injects a scripted drift into the decoy
every N cycles (simulating an operator misconfiguring the decoy over time);
the loop catches, names, and fixes each drift in turn, so the terminal shows
the full catch -> correct -> re-verify story repeatedly.

Usage:
    docker compose up -d
    python collect_live.py --seed
    python live_demo.py --cycles 6 --interval 5
    python live_demo.py --cycles 12 --interval 3 --rebreak-every 3
"""

import argparse
import os

from decoytell.control import apply as control_apply
from decoytell.live import run_loop
from decoytell.probe import probe
from decoytell.schema import THRESHOLDS
from decoytell.store import ObservationStore, psycopg

DEFAULT_DSN = os.environ.get(
    "DECOYTELL_DSN", "postgres://decoytell:decoytell@localhost:5433/decoytell"
)

DRIFT_SEQUENCE = [
    (
        "banner drift (unpatched Apache/2.4.29, implied cadence 730 days) - "
        "fix reads as an upgrade to the real asset's current version",
        {"banner": "Apache/2.4.29 (Debian)"},
    ),
    (
        "timing drift (slow) - joint fingerprint with monitoring",
        {"timing_ms": 1500},
    ),
    (
        "mid-life banner (Apache/2.4.41, implied cadence 365 days) - "
        "fix again reads as an upgrade",
        {"banner": "Apache/2.4.41 (Debian)"},
    ),
    (
        "cert-age drift (fresh cert, account_age ~10 days) - NOT auto-fixable",
        {"account_age_days": 10},
    ),
    (
        "human repair: cert re-issued with correct age (~800 days)",
        {"account_age_days": 800},
    ),
]


def _render_analysis(analysis):
    """Build the real-vs-decoy comparison lines from one cycle's analysis."""
    if not analysis or analysis.get("insufficient"):
        return []
    lines = []
    n = analysis["window_size"]
    lines.append("  real-asset window: %d observations (last %d days)"
                 % (n, THRESHOLDS["recent_window_days"]))
    lines.append("  %-20s %-32s %-24s %s"
                 % ("attribute", "real asset (window)", "decoy (observed)", "status"))
    for r in analysis["attributes"]:
        name = r["name"]
        if r["kind"] == "numeric":
            lo, hi = r["band"]
            unit = (" " + r["unit"]) if r.get("unit") else ""
            real_col = "[%s, %s]%s" % (lo, hi, unit)
        else:
            real_col = "seen %d/%d" % (r["count"], r["window_size"])
        status = "OK" if r["in_tolerance"] else "DRIFT"
        lines.append("  %-20s %-32s %-24s %s"
                     % (name, real_col, str(r["decoy_value"]), status))
    fingerprints = [p for p in analysis.get("pairs", []) if p["fingerprint"]]
    if fingerprints:
        for p in fingerprints:
            lines.append(
                "  JOINT fingerprint: %s=%s + %s=%s -> observed %d, expected %s"
                % (p["attr_a"], p["value_a"], p["attr_b"], p["value_b"],
                   p["observed"], p["expected"])
            )
    else:
        lines.append("  JOINT check: no fingerprints across %d pairs"
                     % len(analysis.get("pairs", [])))
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="real-time verification + correction loop")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--real-host", default=os.environ.get("DECOYTELL_REAL_HOST", "localhost"))
    parser.add_argument("--real-port", type=int, default=int(os.environ.get("DECOYTELL_REAL_PORT", "8443")))
    parser.add_argument("--decoy-host", default=os.environ.get("DECOYTELL_DECOY_HOST", "localhost"))
    parser.add_argument("--decoy-port", type=int, default=int(os.environ.get("DECOYTELL_DECOY_PORT", "8444")))
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between cycles")
    parser.add_argument("--cycles", type=int, default=None, help="run forever if omitted")
    parser.add_argument(
        "--rebreak-every", type=int, default=0,
        help="inject a scripted drift into the decoy every N cycles (0 = off)",
    )
    args = parser.parse_args(argv)

    if psycopg is None:
        raise SystemExit("psycopg not installed (pip install -r requirements-live.txt)")

    print("DecoyTell live loop - real probing of containerized servers in an isolated")
    print("Docker environment. Banner, TLS-cert account age and latency are genuine")
    print("measurements; patch cadence is inferred from a version->release map; timing")
    print("and scan behavior are measured against engineered container configuration.")
    if args.rebreak_every:
        print("-" * 70)
        print("re-break mode: every %d cycles the demo injects a scripted drift into" % args.rebreak_every)
        print("the decoy (an operator misconfiguring it over time); the loop catches")
        print("and fixes each drift. Drift queue:")
        for i, (label, _changes) in enumerate(DRIFT_SEQUENCE, 1):
            print("    #%d %s" % (i, label))
    print("-" * 70)

    store = ObservationStore(psycopg.connect(args.dsn))
    store.init_schema()

    def control(changes):
        return control_apply(args.decoy_host, args.decoy_port, changes)

    drift_index = [0]

    def inject_next_drift(cycle):
        label, changes = DRIFT_SEQUENCE[drift_index[0] % len(DRIFT_SEQUENCE)]
        drift_index[0] += 1
        ok = control(changes)
        print(">> cycle %d done: DRIFT INJECTED #%d: %s [%s]"
              % (cycle, drift_index[0], label, "applied" if ok else "FAILED"))
        print(">> next cycle will catch it...")

    def log_event(event):
        if event["verdict"] in ("UNREACHABLE", "MIRRORING_REQUIRED"):
            print("cycle %-3d @ %s  %s" % (event["cycle"], event["timestamp"], event["verdict"]))
            if event["verdict"] == "MIRRORING_REQUIRED":
                print("    real asset is DOWN but the decoy keeps answering -")
                print("    differential availability is a fingerprint (outage mirroring not implemented)")
        else:
            print("cycle %-3d @ %s" % (event["cycle"], event["timestamp"]))
            for line in _render_analysis(event.get("analysis")):
                print(line)
            if event["verdict"] == "PASS":
                print("    VERDICT: PASS -> %s  (all 5 attributes + 10 pairs within tolerance)"
                      % event["recheck"])
            else:
                print("    VERDICT: %s -> %s" % (event["verdict"], event["recheck"]))
            for fix in event["fixes"]:
                state = "applied" if fix.get("applied") else "cannot apply"
                print("    fix %s: %s -> %s (%s) [%s]"
                      % (fix["attribute"], fix["before"], fix["after"],
                         fix["action"], state))
            if event["verdict"] == "UNSAFE":
                print("    >> HUMAN INTERVENTION REQUIRED: drift is not correctable")
                print("       into tolerance - decoy must NOT be exposed as-is")
            if event["verdict"] == "CORRECTED_PARTIAL":
                print("    >> HUMAN INTERVENTION REQUIRED: a fix could not be applied")
                print("       on the live container (cert-baked account age / host-level")
                print("       monitoring) - the loop cannot repair this on its own")
        if (args.rebreak_every and event["cycle"] % args.rebreak_every == 0
                and (args.cycles is None or event["cycle"] < args.cycles)):
            inject_next_drift(event["cycle"])
        print()

    events = run_loop(
        probe,
        store,
        control,
        (args.real_host, args.real_port),
        (args.decoy_host, args.decoy_port),
        interval=args.interval,
        cycles=args.cycles,
        log=log_event,
    )
    ok_states = {"PASS", "CORRECTED"}
    return 0 if all(
        e["verdict"] in ok_states and e["recheck"] in ok_states for e in events
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())