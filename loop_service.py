"""Standalone live-loop service (ADR-0005).

Runs the verification loop as its own process: each cycle probes the real
asset and the decoy, verifies against the recent window from PostgreSQL,
applies corrections to the decoy's served identity, and persists the cycle as
a loop event. Before each cycle it polls the loop-control row — it keeps
running while the API (or operator) has set `running = true`, and stops
cleanly when the row flips. Survives API restarts; the API survives crashes.

Usage:
    python loop_service.py [--interval 5] [--dsn ...]
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
    parser = argparse.ArgumentParser(description="standalone live-loop service")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--real-host", default=os.environ.get("DECOYTELL_REAL_HOST", "localhost"))
    parser.add_argument("--real-port", type=int, default=int(os.environ.get("DECOYTELL_REAL_PORT", "8443")))
    parser.add_argument("--decoy-host", default=os.environ.get("DECOYTELL_DECOY_HOST", "localhost"))
    parser.add_argument("--decoy-port", type=int, default=int(os.environ.get("DECOYTELL_DECOY_PORT", "8444")))
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args(argv)

    if psycopg is None:
        raise SystemExit("psycopg not installed (pip install -r requirements-live.txt)")

    store = ObservationStore(psycopg.connect(args.dsn))
    store.init_schema()

    def control(changes):
        return control_apply(args.decoy_host, args.decoy_port, changes)

    def should_stop():
        return not store.loop_running()

    print("loop service: waiting for control (POST /api/loop/start) ...", flush=True)
    run_loop(
        probe,
        store,
        control,
        (args.real_host, args.real_port),
        (args.decoy_host, args.decoy_port),
        interval=args.interval,
        cycles=None,
        should_stop=should_stop,
    )
    print("loop service: stopped (control row flipped)", flush=True)


if __name__ == "__main__":
    main()