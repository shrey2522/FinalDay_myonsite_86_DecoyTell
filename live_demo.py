"""Run the real-time verification + correction loop against the Docker stack.

The decoy container is started as a flawed clone (banner the real asset never
shows + a joint fingerprint); the loop catches the drift in cycle 1, applies
corrections to the decoy's served identity via the management plane, and
stays green afterwards.

Usage:
    docker compose up -d
    python collect_live.py --seed
    python live_demo.py --cycles 6 --interval 5
"""

import argparse
import os

from decoytell.control import apply as control_apply
from decoytell.live import run_loop
from decoytell.probe import probe
from decoytell.store import ObservationStore, psycopg

DEFAULT_DSN = os.environ.get(
    "DECOYTELL_DSN", "postgres://decoytell:decoytell@localhost:5433/decoytell"
)


def main(argv=None):
    parser = argparse.ArgumentParser(description="real-time verification + correction loop")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--real-host", default="localhost")
    parser.add_argument("--real-port", type=int, default=8443)
    parser.add_argument("--decoy-host", default="localhost")
    parser.add_argument("--decoy-port", type=int, default=8444)
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between cycles")
    parser.add_argument("--cycles", type=int, default=None, help="run forever if omitted")
    args = parser.parse_args(argv)

    if psycopg is None:
        raise SystemExit("psycopg not installed (pip install -r requirements-live.txt)")

    store = ObservationStore(psycopg.connect(args.dsn))
    store.init_schema()

    def control(changes):
        return control_apply(args.decoy_host, args.decoy_port, changes)

    def log_event(event):
        print(
            "cycle %-3d @ %s  %-12s -> %s"
            % (event["cycle"], event["timestamp"], event["verdict"], event["recheck"])
        )
        for fix in event["fixes"]:
            state = "applied" if fix.get("applied") else "cannot apply"
            print(
                "    fix %s: %s -> %s (%s) [%s]"
                % (fix["attribute"], fix["before"], fix["after"], fix["action"], state)
            )

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
    return 0 if all(e["recheck"] in ("PASS", "CORRECTED", "UNREACHABLE") for e in events) else 1


if __name__ == "__main__":
    raise SystemExit(main())