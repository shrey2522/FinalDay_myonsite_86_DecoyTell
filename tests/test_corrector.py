"""Corrector behavior tests at the single verification seam."""

import unittest

from decoytell.engine import run_scenario

DECOY_BASE = {
    "service_banner": "Apache/2.4.54 (Debian)",
    "patch_cadence_days": 300,
    "timing_band": "fast",
    "account_age_days": 810,
    "monitoring_behavior": "immediate",
}


def _config(**overrides):
    base = {
        "id": "corrector",
        "seed": 2001,
        "decoy": dict(DECOY_BASE),
        "expected_verdict": "CORRECTED",
    }
    base.update(overrides)
    return base


class CorrectorTests(unittest.TestCase):
    def test_single_drift_is_corrected_and_named(self):
        report = run_scenario(_config())
        self.assertEqual(report["verdict"], "CORRECTED")
        self.assertTrue(report["corrections"])
        fix = report["corrections"][0]
        self.assertEqual(fix["attribute"], "patch_cadence_days")
        self.assertEqual(fix["before"], 300)
        self.assertTrue(fix["re_verified"])

        before = {a["name"]: a for a in report["attributes"]}
        self.assertFalse(before["patch_cadence_days"]["in_tolerance"])

        self.assertTrue(all(a["in_tolerance"] for a in report["final"]["attributes"]))
        self.assertFalse(any(p["fingerprint"] for p in report["final"]["pairs"]))

    def test_fix_emits_full_shape(self):
        fix = run_scenario(_config())["corrections"][0]
        for key in ("attribute", "before", "after", "action", "re_verified"):
            self.assertIn(key, fix)
        self.assertTrue(fix["action"])

    def test_passing_decoy_is_not_corrected(self):
        report = run_scenario(
            _config(
                id="ok",
                seed=1001,
                decoy={
                    "service_banner": "Apache/2.4.54 (Debian)",
                    "patch_cadence_days": 12,
                    "timing_band": "fast",
                    "account_age_days": 810,
                    "monitoring_behavior": "immediate",
                },
                expected_verdict="PASS",
            )
        )
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["corrections"], [])

    def test_non_correctable_drift_is_unsafe_and_named(self):
        decoy = {
            "service_banner": "Apache/2.4.54 (Debian)",
            "patch_cadence_days": 12,
            "timing_band": "slow",
            "account_age_days": 810,
            "monitoring_behavior": "immediate",
        }
        report = run_scenario(
            _config(decoy=decoy, expected_verdict="UNSAFE", correctable={"timing_band": False})
        )
        self.assertEqual(report["verdict"], "UNSAFE")
        self.assertEqual(report["corrections"], [])
        self.assertIn("timing_band", report.get("blocked_attributes", []))
        self.assertIn("monitoring_behavior", report.get("blocked_attributes", []))

    def test_fingerprint_pair_resolved_via_conditional_mode(self):
        decoy = {
            "service_banner": "Apache/2.4.54 (Debian)",
            "patch_cadence_days": 12,
            "timing_band": "slow",
            "account_age_days": 810,
            "monitoring_behavior": "immediate",
        }
        report = run_scenario(_config(decoy=decoy, expected_verdict="CORRECTED"))
        self.assertEqual(report["verdict"], "CORRECTED")
        fix = report["corrections"][0]
        self.assertEqual(fix["attribute"], "timing_band")
        self.assertEqual(fix["after"], "fast")


if __name__ == "__main__":
    unittest.main()