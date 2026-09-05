"""Reset the stack to the canonical demo state in one command.

Clears the store (observations + loop events, keeping test rows), seeds the
mock history for the real asset, stops the loop control, and breaks the decoy
back into its flawed identity — so the next "Start loop" in the dashboard
catches the drift live.

Usage:
    docker compose up -d --build
    python demo_prep.py
"""

import argparse
import os

from decoytell.control import apply as control_apply
from decoytell.generator import generate_history
from decoytell.store import ObservationStore, psycopg

DEFAULT_DSN = os.environ.get(
    "DECOYTELL_DSN", "postgres://decoytell:decoytell@localhost:5433/decoytell"
)
SEED = 7001


def main(argv=None):
    parser = argparse.ArgumentParser(description="prepare the canonical demo state")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--decoy-host", default="localhost")
    parser.add_argument("--decoy-port", type=int, default=8444)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)

    if psycopg is None:
        raise SystemExit("psycopg not installed (pip install -r requirements-live.txt)")

    store = ObservationStore(psycopg.connect(args.dsn))
    store.init_schema()
    with store.conn.cursor() as cur:
        cur.execute("DELETE FROM observations WHERE target NOT LIKE 'test-%'")
        cur.execute("DELETE FROM loop_events")
        cur.execute("UPDATE loop_control SET running = false WHERE id = 1")
    store.conn.commit()

    history = generate_history(args.seed)
    store.seed(history, target="real-asset")

    broken = control_apply(
        args.decoy_host,
        args.decoy_port,
        {"banner": "Apache/2.4.55 (Debian)", "timing_ms": 1500, "monitoring": "immediate"},
    )

    print("demo state prepared:")
    print("  store reset + seeded mock history (%d observations)" % len(history))
    print("  loop control stopped")
    print("  decoy broken (flawed identity served): %s" % broken)


if __name__ == "__main__":
    main()