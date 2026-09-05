"""Prober behavior tests: pure classification + a live in-process endpoint."""

import os
import socket
import ssl
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from decoytell import probe as P

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class ClassificationTests(unittest.TestCase):
    def test_timing_band_thresholds(self):
        self.assertEqual(P.timing_band(50.0), "fast")
        self.assertEqual(P.timing_band(300.0), "nominal")
        self.assertEqual(P.timing_band(1200.0), "slow")

    def test_patch_cadence_from_banner(self):
        self.assertEqual(P.patch_cadence("Apache/2.4.54 (Debian)"), 60.0)
        self.assertEqual(P.patch_cadence("nginx/1.18.0"), 999.0)

    def test_account_age_from_cert_time(self):
        cert = {"notBefore": "Jan  1 00:00:00 2019 GMT"}
        self.assertGreater(P.account_age_days(cert), 2500.0)

    def test_monitoring_classification(self):
        ok = {"banner": "Apache/2.4.54 (Debian)"}
        self.assertEqual(P.classify_monitoring([ok] * 6, 6), "immediate")
        self.assertEqual(P.classify_monitoring([ok] * 3, 6), "rate_limited")
        self.assertEqual(P.classify_monitoring([None] * 6, 6), "silent")


class _Handler(BaseHTTPRequestHandler):
    server_version = "Apache/2.4.54 (Debian)"
    sys_version = ""

    def do_GET(self):
        body = b"<html>decoytell identity</html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@unittest.skipUnless(
    os.path.exists(os.path.join(FIXTURE_DIR, "cert.pem")),
    "fixture TLS cert not present (generate via containers/identity build)",
)
class LiveEndpointTests(unittest.TestCase):
    def test_probe_returns_full_observation_from_live_endpoint(self):
        port = _free_port()
        server = HTTPServer(("127.0.0.1", port), _Handler)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(
            os.path.join(FIXTURE_DIR, "cert.pem"), os.path.join(FIXTURE_DIR, "key.pem")
        )
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.2)
        try:
            obs = P.probe("127.0.0.1", port)
            self.assertEqual(obs["service_banner"], "Apache/2.4.54 (Debian)")
            self.assertEqual(obs["patch_cadence_days"], 60.0)
            self.assertEqual(obs["timing_band"], "fast")
            self.assertGreater(obs["account_age_days"], 0.0)
            self.assertEqual(obs["monitoring_behavior"], "immediate")
        finally:
            server.shutdown()


class ContainerProbeTests(unittest.TestCase):
    """The prober against the real Docker containers (skipped when the stack
    is down or psycopg/Docker is unavailable)."""

    LIVE_HOST = os.environ.get("DECOYTELL_LIVE_HOST", "localhost")
    REAL_PORT = 8443
    DECOY_PORT = 8444

    @classmethod
    def setUpClass(cls):
        try:
            cls.real = P.probe(cls.LIVE_HOST, cls.REAL_PORT)
            cls.decoy = P.probe(cls.LIVE_HOST, cls.DECOY_PORT)
            cls.available = cls.real["service_banner"] is not None and cls.decoy["service_banner"] is not None
        except Exception:
            cls.available = False

    def test_probe_returns_observation_shape_from_real_container(self):
        if not self.available:
            self.skipTest("live containers not reachable (docker compose up -d)")
        for key in ("service_banner", "patch_cadence_days", "timing_band",
                    "account_age_days", "monitoring_behavior"):
            self.assertIn(key, self.real)
        self.assertEqual(self.real["service_banner"], "Apache/2.4.54 (Debian)")
        self.assertGreater(self.real["account_age_days"], 700)

    def test_probe_returns_observation_shape_from_decoy_container(self):
        if not self.available:
            self.skipTest("live containers not reachable (docker compose up -d)")
        for key in ("service_banner", "patch_cadence_days", "timing_band",
                    "account_age_days", "monitoring_behavior"):
            self.assertIn(key, self.decoy)
        self.assertIsNotNone(self.decoy["service_banner"])


if __name__ == "__main__":
    unittest.main()