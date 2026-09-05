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
        self.store.conn.commit()

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


if __name__ == "__main__":
    unittest.main()