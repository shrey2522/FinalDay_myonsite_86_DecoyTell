"""Observation-store tests. Requires a reachable PostgreSQL (DSN via env).

Skipped when psycopg or a DSN is unavailable, so the core suite stays green
with no live-layer dependencies.
"""

import datetime
import os
import unittest

from decoytell.generator import Observation
from decoytell.store import ObservationStore, psycopg

DSN = os.environ.get("DECOYTELL_TEST_DSN", "")


@unittest.skipUnless(psycopg and DSN, "requires psycopg and DECOYTELL_TEST_DSN")
class StoreTests(unittest.TestCase):
    REAL = "test-real-asset"
    DECOY = "test-decoy"

    def setUp(self):
        self.store = ObservationStore(psycopg.connect(DSN))
        self.store.init_schema()
        # Isolate tests: only ever touch rows that carry the test prefix, so
        # the demo store's seeded history and live observations are untouched.
        with self.store.conn.cursor() as cur:
            cur.execute("DELETE FROM observations WHERE target LIKE 'test-%%'")
            cur.execute("SELECT COALESCE(MAX(id), 0) FROM loop_events")
            self._baseline_event_id = cur.fetchone()[0]
        self._saved_running = self.store.loop_running()
        self.store.conn.commit()

    def tearDown(self):
        with self.store.conn.cursor() as cur:
            cur.execute("DELETE FROM loop_events WHERE id > %s", (self._baseline_event_id,))
        self.store.set_loop_running(self._saved_running)
        self.store.conn.commit()
        self.store.conn.close()

    def test_seed_append_and_recent_window_round_trip(self):
        self.store.seed(
            [
                Observation(days_ago=10.0, service_banner="Apache/2.4.55 (Debian)",
                            patch_cadence_days=5.0, timing_band="fast",
                            account_age_days=800.0, monitoring_behavior="immediate"),
                Observation(days_ago=200.0, service_banner="Apache/2.4.41 (Debian)",
                            patch_cadence_days=180.0, timing_band="slow",
                            account_age_days=500.0, monitoring_behavior="silent"),
            ],
            target=self.REAL,
        )
        self.store.append(
            {"service_banner": "Apache/2.4.54 (Debian)", "patch_cadence_days": 6.0,
             "timing_band": "fast", "account_age_days": 810.0,
             "monitoring_behavior": "immediate"},
            target=self.DECOY,
        )

        real_only = self.store.recent_window(days=90, target=self.REAL)
        decoy_only = self.store.recent_window(days=90, target=self.DECOY)
        self.assertEqual(len(real_only), 1)
        self.assertEqual(len(decoy_only), 1)
        self.assertEqual(real_only[0].patch_cadence_days, 5.0)
        self.assertEqual(decoy_only[0].monitoring_behavior, "immediate")

    def test_recent_window_respects_days(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        self.store.append(
            {"service_banner": "x", "patch_cadence_days": 1.0, "timing_band": "fast",
             "account_age_days": 1.0, "monitoring_behavior": "immediate"},
            target=self.REAL,
            observed_at=now - datetime.timedelta(days=1),
        )
        self.store.append(
            {"service_banner": "y", "patch_cadence_days": 1.0, "timing_band": "fast",
             "account_age_days": 1.0, "monitoring_behavior": "immediate"},
            target=self.REAL,
            observed_at=now - datetime.timedelta(days=200),
        )
        self.assertEqual(len(self.store.recent_window(days=90, target=self.REAL)), 1)
        self.assertEqual(len(self.store.recent_window(days=300, target=self.REAL)), 2)

    def test_loop_control_toggles(self):
        self.store.set_loop_running(False)
        self.assertFalse(self.store.loop_running())
        self.store.set_loop_running(True)
        self.assertTrue(self.store.loop_running())
        self.store.set_loop_running(False)
        self.assertFalse(self.store.loop_running())

    def test_loop_event_round_trip_and_tail(self):
        event = {
            "cycle": 1,
            "timestamp": "2026-09-05T00:00:00+00:00",
            "verdict": "CORRECTED",
            "recheck": "PASS",
            "fixes": [{"attribute": "service_banner", "before": "A", "after": "B",
                       "action": "reconfigure server header/banner", "applied": True}],
            "real_obs": {"service_banner": "Apache/2.4.54 (Debian)", "patch_cadence_days": 12.0,
                         "timing_band": "fast", "account_age_days": 810.0,
                         "monitoring_behavior": "immediate"},
            "decoy_obs": {"service_banner": "Apache/2.4.54 (Debian)", "patch_cadence_days": 12.0,
                          "timing_band": "fast", "account_age_days": 810.0,
                          "monitoring_behavior": "immediate"},
        }
        self.store.record_loop_event(**event)
        self.store.record_loop_event(**{**event, "cycle": 2, "verdict": "PASS"})

        tail = self.store.loop_events_after(after_id=self._baseline_event_id, limit=10)
        self.assertEqual(len(tail), 2)
        self.assertEqual(tail[0]["cycle"], 1)
        self.assertEqual(tail[0]["verdict"], "CORRECTED")
        self.assertEqual(tail[0]["fixes"][0]["attribute"], "service_banner")
        self.assertEqual(tail[0]["real_obs"]["service_banner"], "Apache/2.4.54 (Debian)")

        latest = self.store.latest_loop_event()
        self.assertEqual(latest["cycle"], 2)
        self.assertEqual(latest["verdict"], "PASS")

        after_first = self.store.loop_events_after(
            after_id=tail[0]["id"], limit=10
        )
        self.assertEqual(len(after_first), 1)
        self.assertEqual(after_first[0]["cycle"], 2)


if __name__ == "__main__":
    unittest.main()