"""Real-time loop behavior tests (fakes for probe/store/control — no Docker)."""

import unittest

from decoytell.engine import verify
from decoytell.generator import generate_history
from decoytell.live import map_fix_to_identity, run_loop

REAL = ("real", 8443)
DECOY = ("decoy", 8444)

REAL_OBS = {
    "service_banner": "Apache/2.4.54 (Debian)",
    "patch_cadence_days": 12.0,
    "timing_band": "fast",
    "account_age_days": 810.0,
    "monitoring_behavior": "immediate",
}

DRIFTED = {
    "service_banner": "Apache/2.4.55 (Debian)",  # unseen in real window
    "patch_cadence_days": 5.0,
    "timing_band": "slow",                       # fingerprint with immediate
    "account_age_days": 810.0,
    "monitoring_behavior": "immediate",
}

CORRECTED = {
    "service_banner": "Apache/2.4.54 (Debian)",
    "patch_cadence_days": 60.0,
    "timing_band": "fast",
    "account_age_days": 810.0,
    "monitoring_behavior": "immediate",
}


class FakeProbe:
    def __init__(self, real_obs, decoy_sequence):
        self.real_obs = real_obs
        self.decoy_sequence = list(decoy_sequence)

    def __call__(self, host, port):
        if port == DECOY[1]:
            return self.decoy_sequence.pop(0)
        return self.real_obs


class FakeStore:
    def __init__(self, history):
        self.history = history
        self.appends = []

    def append(self, obs, target="decoy"):
        self.appends.append((target, obs))

    def recent_window(self, days=90, target=None):
        return self.history


class FakeControl:
    def __init__(self):
        self.applied = []
        self.identity = {}

    def apply(self, changes):
        self.applied.append(dict(changes))
        self.identity.update(changes)
        return True

    def __call__(self, changes):
        return self.apply(changes)


class MapFixTests(unittest.TestCase):
    def test_maps_identity_applicable_fixes(self):
        window = generate_history(3001)
        self.assertEqual(
            map_fix_to_identity({"attribute": "service_banner", "after": "X"}, window),
            {"banner": "X"},
        )
        self.assertEqual(
            map_fix_to_identity({"attribute": "timing_band", "after": "fast"}, window),
            {"timing_ms": 0.0},
        )
        self.assertEqual(
            map_fix_to_identity({"attribute": "monitoring_behavior", "after": "silent"}, window),
            {"monitoring": "silent"},
        )

    def test_cadence_fix_maps_to_modal_banner(self):
        window = [o for o in generate_history(3001) if o.days_ago <= 90]
        result = map_fix_to_identity(
            {"attribute": "patch_cadence_days", "after": 17.4}, window
        )
        self.assertEqual(result, {"banner": "Apache/2.4.54 (Debian)"})

    def test_account_age_is_not_applicable(self):
        self.assertIsNone(
            map_fix_to_identity({"attribute": "account_age_days", "after": 810.0}, [])
        )


class LoopTests(unittest.TestCase):
    def setUp(self):
        self.history = generate_history(3001)
        self.control = FakeControl()
        self.probe = FakeProbe(
            REAL_OBS,
            [DRIFTED, CORRECTED, CORRECTED, CORRECTED, CORRECTED],
        )
        self.store = FakeStore(self.history)

    def test_drift_is_caught_corrected_and_reverified(self):
        events = run_loop(
            self.probe, self.store, self.control, REAL, DECOY,
            interval=0.0, cycles=3, log=lambda e: None,
        )
        first = events[0]
        self.assertEqual(first["verdict"], "CORRECTED")
        self.assertEqual(first["recheck"], "PASS")
        applied = [c["applied"] for c in first["fixes"]]
        self.assertTrue(all(applied))
        self.assertIn({"banner": "Apache/2.4.54 (Debian)"}, self.control.applied)
        self.assertIn({"timing_ms": 0.0}, self.control.applied)

    def test_decoy_stays_green_after_correction(self):
        events = run_loop(
            self.probe, self.store, self.control, REAL, DECOY,
            interval=0.0, cycles=3, log=lambda e: None,
        )
        self.assertEqual(events[1]["verdict"], "PASS")
        self.assertEqual(events[2]["verdict"], "PASS")

    def test_real_observation_appended_every_cycle(self):
        run_loop(
            self.probe, self.store, self.control, REAL, DECOY,
            interval=0.0, cycles=3, log=lambda e: None,
        )
        self.assertEqual(len(self.store.appends), 3)
        self.assertTrue(all(t == "real-asset" for t, _ in self.store.appends))

    def test_events_carry_timestamp_and_cycle(self):
        events = run_loop(
            self.probe, self.store, self.control, REAL, DECOY,
            interval=0.0, cycles=2, log=lambda e: None,
        )
        self.assertEqual([e["cycle"] for e in events], [1, 2])
        self.assertTrue(all(e["timestamp"] for e in events))


if __name__ == "__main__":
    unittest.main()