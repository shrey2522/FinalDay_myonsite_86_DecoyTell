"""Behavioral tests for the engine at the single verification seam."""

import unittest

from decoytell.engine import run_scenario


def _config(**overrides):
    base = {
        "id": "unit",
        "seed": 1001,
        "decoy": {
            "service_banner": "Apache/2.4.54 (Debian)",
            "patch_cadence_days": 12,
            "timing_band": "fast",
            "account_age_days": 810,
            "monitoring_behavior": "immediate",
        },
        "expected_verdict": "PASS",
    }
    base.update(overrides)
    return base


class SeamBehaviorTests(unittest.TestCase):
    def test_harmless_decoy_verifies_as_pass(self):
        report = run_scenario(_config())
        self.assertEqual(report["verdict"], "PASS")
        self.assertTrue(report["window_size"] >= 100)
        self.assertTrue(all(a["in_tolerance"] for a in report["attributes"]))
        self.assertFalse(any(p["fingerprint"] for p in report["pairs"]))

    def test_single_attribute_drift_is_named_and_corrected(self):
        report = run_scenario(_config(decoy={"service_banner": "Apache/2.4.54 (Debian)", "patch_cadence_days": 300, "timing_band": "fast", "account_age_days": 810, "monitoring_behavior": "immediate"}))
        self.assertEqual(report["verdict"], "CORRECTED")
        by_name = {a["name"]: a for a in report["attributes"]}
        self.assertFalse(by_name["patch_cadence_days"]["in_tolerance"])
        self.assertTrue(by_name["service_banner"]["in_tolerance"])
        self.assertEqual(report["corrections"][0]["attribute"], "patch_cadence_days")

    def test_categorical_value_never_seen_is_flagged(self):
        report = run_scenario(_config(decoy={"service_banner": "nginx/1.18.0", "patch_cadence_days": 12, "timing_band": "fast", "account_age_days": 810, "monitoring_behavior": "immediate"}))
        by_name = {a["name"]: a for a in report["attributes"]}
        self.assertFalse(by_name["service_banner"]["in_tolerance"])

    def test_verify_refuses_stale_window(self):
        from decoytell.engine import verify
        from decoytell.generator import Observation, generate_history

        decoy = {
            "service_banner": "Apache/2.4.54 (Debian)",
            "patch_cadence_days": 12,
            "timing_band": "fast",
            "account_age_days": 810,
            "monitoring_behavior": "immediate",
        }
        fresh = generate_history(1001)
        verdict, _, _ = verify(fresh, decoy)
        self.assertEqual(verdict, "PASS")
        stale = [
            Observation(
                days_ago=o.days_ago + 2.0,
                service_banner=o.service_banner,
                patch_cadence_days=o.patch_cadence_days,
                timing_band=o.timing_band,
                account_age_days=o.account_age_days,
                monitoring_behavior=o.monitoring_behavior,
            )
            for o in fresh
        ]
        verdict, _, _ = verify(stale, decoy)
        self.assertEqual(verdict, "STALE_DATA")

    def test_insufficient_history_refuses_to_certify(self):
        report = run_scenario(_config(observations=50))
        self.assertEqual(report["verdict"], "INSUFFICIENT_DATA")
        self.assertLess(report["window_size"], 100)

    def test_validation_rejects_missing_attribute(self):
        decoy = {"service_banner": "Apache/2.4.54 (Debian)", "patch_cadence_days": 12, "timing_band": "fast", "account_age_days": 810}
        with self.assertRaises(ValueError):
            run_scenario(_config(decoy=decoy))

    def test_validation_rejects_undeclared_categorical_value(self):
        decoy = {"service_banner": "Apache/2.4.54 (Debian)", "patch_cadence_days": 12, "timing_band": "glacial", "account_age_days": 810, "monitoring_behavior": "immediate"}
        with self.assertRaises(ValueError):
            run_scenario(_config(decoy=decoy))

    def test_validation_rejects_non_numeric_value(self):
        decoy = {"service_banner": "Apache/2.4.54 (Debian)", "patch_cadence_days": "soon", "timing_band": "fast", "account_age_days": 810, "monitoring_behavior": "immediate"}
        with self.assertRaises(ValueError):
            run_scenario(_config(decoy=decoy))

    def test_validation_rejects_unknown_attribute(self):
        decoy = {"service_banner": "Apache/2.4.54 (Debian)", "patch_cadence_days": 12, "timing_band": "fast", "account_age_days": 810, "monitoring_behavior": "immediate", "tls_version": "1.3"}
        with self.assertRaises(ValueError):
            run_scenario(_config(decoy=decoy))


if __name__ == "__main__":
    unittest.main()