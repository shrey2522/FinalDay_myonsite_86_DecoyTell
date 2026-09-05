"""CLI entry point: run the declared scenarios through the verification seam.

Exit codes (scriptable gate):
  0  all scenarios certified (PASS or CORRECTED)
  1  any scenario UNSAFE (unsafe to expose)
  2  any scenario INSUFFICIENT_DATA (cannot certify on available evidence)

Every scenario also writes a complete JSON proof export.
"""

import argparse
import glob
import json
import os
import sys

from decoytell.engine import run_scenario
from decoytell.report import render_text, to_json

SCENARIO_DIR = "scenarios"
DEFAULT_JSON_DIR = "out"


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
        "--scenario", default=None, help="run a single scenario by id/prefix (default: all)"
    )
    parser.add_argument(
        "--json-dir", default=DEFAULT_JSON_DIR,
        help="directory for JSON proof exports (default: %s)" % DEFAULT_JSON_DIR,
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

    os.makedirs(args.json_dir, exist_ok=True)
    for report in reports:
        print(render_text(report))
        print()
        export_path = os.path.join(args.json_dir, report["scenario_id"] + ".json")
        with open(export_path, "w", encoding="utf-8") as fh:
            fh.write(to_json(report))

    if any(r["verdict"] == "INSUFFICIENT_DATA" for r in reports):
        return 2
    if any(r["verdict"] == "UNSAFE" for r in reports):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())