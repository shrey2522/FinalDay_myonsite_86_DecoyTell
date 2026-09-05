"""Continuous-observation loop behavior at the verification seam."""

import unittest

from decoytell.observe import observe


class ObserveTests(unittest.TestCase):
    DECOY = {
        "service_banner": "Apache/2.4.54 (Debian)",
        "patch_cadence_days": 12,
        "timing_band": "fast",
        "account_age_days": 810,
        "monitoring_behavior": "immediate",
    }

    def test_decoy_stays_green_until_real_server_patches(self):
        final_decoy, events = observe(6001, self.DECOY, duration=100, patch_cycle=5)
        corrected_cycles = [e["cycle"] for e in events if e["corrections"]]
        self.assertTrue(corrected_cycles, "the robot must catch the drift at some cycle")
        self.assertEqual(events[0]["verdict"], "PASS")
        self.assertEqual(events[-1]["recheck"], "PASS")
        self.assertEqual(final_decoy["service_banner"], "Apache/2.4.55 (Debian)")

    def test_loop_is_deterministic(self):
        final_a, events_a = observe(6001, self.DECOY, duration=50, patch_cycle=5)
        final_b, events_b = observe(6001, self.DECOY, duration=50, patch_cycle=5)
        self.assertEqual(final_a, final_b)
        self.assertEqual(events_a, events_b)

    def test_never_patched_asset_keeps_decoy_pass(self):
        final_decoy, events = observe(6001, self.DECOY, duration=20, patch_cycle=999)
        self.assertTrue(all(e["verdict"] == "PASS" for e in events))


if __name__ == "__main__":
    unittest.main()