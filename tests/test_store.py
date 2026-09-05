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
    def setUp(self):
        self.store = ObservationStore(psycopg.connect(DSN))
        self.store.init_schema()
        with self.store.conn.cursor() as cur:
            cur.execute("DELETE FROM observations")
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
            target="real-asset",
        )
        self.store.append(
            {"service_banner": "Apache/2.4.54 (Debian)", "patch_cadence_days": 6.0,
             "timing_band": "fast", "account_age_days": 810.0,
             "monitoring_behavior": "immediate"},
            target="decoy",
        )

        window = self.store.recent_window(days=90)
        self.assertEqual(len(window), 2)
        recent = {o.service_banner: o for o in window}
        self.assertEqual(recent["Apache/2.4.55 (Debian)"].patch_cadence_days, 5.0)

        real_only = self.store.recent_window(days=90, target="real-asset")
        self.assertEqual(len(real_only), 1)
        decoy_only = self.store.recent_window(days=90, target="decoy")
        self.assertEqual(len(decoy_only), 1)
        self.assertEqual(decoy_only[0].monitoring_behavior, "immediate")

    def test_recent_window_respects_days(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        self.store.append(
            {"service_banner": "x", "patch_cadence_days": 1.0, "timing_band": "fast",
             "account_age_days": 1.0, "monitoring_behavior": "immediate"},
            target="real-asset",
            observed_at=now - datetime.timedelta(days=1),
        )
        self.store.append(
            {"service_banner": "y", "patch_cadence_days": 1.0, "timing_band": "fast",
             "account_age_days": 1.0, "monitoring_behavior": "immediate"},
            target="real-asset",
            observed_at=now - datetime.timedelta(days=200),
        )
        self.assertEqual(len(self.store.recent_window(days=90)), 1)
        self.assertEqual(len(self.store.recent_window(days=300)), 2)


if __name__ == "__main__":
    unittest.main()