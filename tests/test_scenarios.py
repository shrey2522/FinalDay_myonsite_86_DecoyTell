"""Scenario-driven tests at the single verification seam."""

import glob
import json
import os
import unittest

from decoytell.engine import run_scenario

SCENARIO_DIR = os.path.join(os.path.dirname(__file__), "..", "scenarios")


def load_all_scenarios():
    configs = []
    for path in sorted(glob.glob(os.path.join(SCENARIO_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            configs.append(json.load(fh))
    return configs


class ScenarioTests(unittest.TestCase):
    def test_every_scenario_matches_its_expected_verdict(self):
        for config in load_all_scenarios():
            with self.subTest(scenario=config["id"]):
                report = run_scenario(config)
                self.assertEqual(report["verdict"], config.get("expected_verdict"))

    def test_every_scenario_is_deterministic(self):
        for config in load_all_scenarios():
            with self.subTest(scenario=config["id"]):
                self.assertEqual(run_scenario(config), run_scenario(config))