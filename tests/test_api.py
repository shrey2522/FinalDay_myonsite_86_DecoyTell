"""Web/API tests through the FastAPI TestClient seam (DSN-guarded)."""

import os
import unittest

from decoytell import api
from decoytell.store import psycopg

DSN = os.environ.get("DECOYTELL_TEST_DSN", "")


@unittest.skipUnless(psycopg and DSN, "requires psycopg and DECOYTELL_TEST_DSN")
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._prev_dsn = os.environ.get("DECOYTELL_DSN")
        os.environ["DECOYTELL_DSN"] = DSN
        from fastapi.testclient import TestClient

        cls.client = TestClient(api.app)
        cls._saved_running = None
        try:
            cls._saved_running = cls._control_state()
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        if cls._saved_running is not None:
            try:
                cls._set_control(cls._saved_running)
            except Exception:
                pass
        if cls._prev_dsn is None:
            os.environ.pop("DECOYTELL_DSN", None)
        else:
            os.environ["DECOYTELL_DSN"] = cls._prev_dsn

    @classmethod
    def _control_state(cls):
        return api._store().loop_running()

    @classmethod
    def _set_control(cls, value):
        api._store().set_loop_running(value)

    def test_status_shape(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["scenarios"]), 5)
        self.assertIn("running", body["loop"])
        self.assertTrue(all("verdict" in s for s in body["scenarios"]))

    def test_scenarios_list_has_five_reports(self):
        response = self.client.get("/api/scenarios")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 5)

    def test_scenario_report_by_id(self):
        response = self.client.get("/api/scenarios/s2_single_drift")
        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertEqual(report["verdict"], "CORRECTED")
        self.assertEqual(report["corrections"][0]["attribute"], "patch_cadence_days")

    def test_unknown_scenario_is_404(self):
        self.assertEqual(self.client.get("/api/scenarios/nope").status_code, 404)

    def test_pair_matrix_for_s3(self):
        response = self.client.get("/api/pairs?sid=s3_pair_fingerprint")
        self.assertEqual(response.status_code, 200)
        pairs = response.json()["pairs"]
        self.assertEqual(len(pairs), 10)
        fingerprints = [p for p in pairs if p["fingerprint"]]
        self.assertEqual(len(fingerprints), 1)
        self.assertGreaterEqual(fingerprints[0]["expected"], 1.0)
        self.assertEqual(fingerprints[0]["observed"], 0)

    def test_observations_window_shape(self):
        response = self.client.get("/api/observations?target=real-asset&days=90")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("count", body)
        self.assertIsInstance(body["observations"], list)

    def test_loop_events_tail_shape(self):
        response = self.client.get("/api/loop/events?after=0&limit=10")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json()["events"], list)

    def test_loop_start_stop_toggles_control(self):
        self.client.post("/api/loop/stop")
        self.assertFalse(self._control_state())
        self.client.post("/api/loop/start")
        self.assertTrue(self._control_state())
        self.client.post("/api/loop/stop")
        self.assertFalse(self._control_state())

    def test_verify_endpoint_runs_one_cycle(self):
        response = self.client.post("/api/verify")
        self.assertEqual(response.status_code, 200)
        event = response.json()
        self.assertEqual(event["cycle"], 1)
        self.assertIn(event["verdict"], ("CORRECTED", "PASS", "UNSAFE", "UNREACHABLE"))
        self.assertIn("timestamp", event)


if __name__ == "__main__":
    unittest.main()