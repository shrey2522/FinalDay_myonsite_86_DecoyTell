"""T3: the pair-fingerprint path — the judging centerpiece.

Asserts that the s3 scenario is caught by the pairwise joint check (not by a
hand-written rule, and not by the individual checks), that both responsible
attributes are named with expected-vs-observed counts, and that the decoy is
corrected and re-verified into a passing state.
"""

import json
import os
import unittest

from decoytell.engine import run_scenario

SCENARIO_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scenarios", "s3_pair_fingerprint.json"
)


def _load_s3():
    with open(SCENARIO_PATH, encoding="utf-8") as fh:
        return json.load(fh)


class PairFingerprintTests(unittest.TestCase):
    def test_individual_checks_pass_before_correction(self):
        report = run_scenario(_load_s3())
        by_name = {a["name"]: a for a in report["attributes"]}
        self.assertTrue(by_name["timing_band"]["in_tolerance"])
        self.assertTrue(by_name["monitoring_behavior"]["in_tolerance"])
        self.assertTrue(all(a["in_tolerance"] for a in report["attributes"]))

    def test_pair_is_caught_by_joint_check_and_named(self):
        report = run_scenario(_load_s3())
        fingerprints = [p for p in report["pairs"] if p["fingerprint"]]
        self.assertTrue(fingerprints)
        pair = fingerprints[0]
        self.assertEqual(sorted([pair["attr_a"], pair["attr_b"]]), ["monitoring_behavior", "timing_band"])
        self.assertEqual(pair["observed"], 0)
        self.assertGreaterEqual(pair["expected"], 1.0)

    def test_pair_fingerprint_is_corrected_and_reverified(self):
        report = run_scenario(_load_s3())
        self.assertEqual(report["verdict"], "CORRECTED")
        self.assertTrue(report["corrections"])
        fix = report["corrections"][0]
        self.assertEqual(fix["attribute"], "timing_band")
        self.assertEqual(fix["after"], "fast")
        self.assertTrue(fix["re_verified"])
        self.assertTrue(all(a["in_tolerance"] for a in report["final"]["attributes"]))
        self.assertFalse(any(p["fingerprint"] for p in report["final"]["pairs"]))


if __name__ == "__main__":
    unittest.main()