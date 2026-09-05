"""Collect live observations from a running container into PostgreSQL.

Usage:
    python collect_live.py --seed --host localhost --port 8443 --target real-asset
"""

import argparse
import os

from decoytell.generator import generate_history
from decoytell.probe import probe
from decoytell.store import ObservationStore, psycopg

DEFAULT_DSN = os.environ.get(
    "DECOYTELL_DSN", "postgres://decoytell:decoytell@localhost:5433/decoytell"
)
SEED = 7001


def main(argv=None):
    parser = argparse.ArgumentParser(description="collect a live observation into the store")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--target", default="real-asset", help="real-asset or decoy")
    parser.add_argument("--seed", action="store_true", help="seed the mock history first")
    args = parser.parse_args(argv)

    if psycopg is None:
        raise SystemExit("psycopg not installed (pip install -r requirements-live.txt)")

    store = ObservationStore(psycopg.connect(args.dsn))
    store.init_schema()
    if args.seed:
        store.seed(generate_history(SEED), target="real-asset")
        print("seeded mock history (%d observations)" % 1400)

    observation = probe(args.host, args.port)
    store.append(observation, target=args.target)
    print("probed %s:%d -> appended observation:" % (args.host, args.port))
    for key, value in observation.items():
        print("  %-22s %s" % (key, value))
    window = store.recent_window(days=90, target="real-asset")
    print("real-asset recent window size:", len(window))


if __name__ == "__main__":
    main()