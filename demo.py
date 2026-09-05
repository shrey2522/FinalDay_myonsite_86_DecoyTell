"""CLI entry point: run the declared scenarios through the verification seam."""

import argparse
import glob
import json
import os
import sys

from decoytell.engine import run_scenario
from decoytell.report import render_text

SCENARIO_DIR = "scenarios"


def load_scenarios(paths):
    configs = []
    for path in sorted(paths):
        with open(path, encoding="utf-8") as fh:
            configs.append(json.load(fh))
    return configs


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="demo.py", description="DecoyTell: bounded deception-surface consistency verification"
    )
    parser.add_argument(
        "--scenario", default=None, help="run a single scenario by id (default: all)"
    )
    args = parser.parse_args(argv)

    paths = glob.glob(os.path.join(SCENARIO_DIR, "*.json"))
    reports = []
    for config in load_scenarios(paths):
        if args.scenario and not config["id"].startswith(args.scenario):
            continue
        reports.append(run_scenario(config))

    if not reports:
        parser.error("no scenarios matched")

    for report in reports:
        print(render_text(report))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())