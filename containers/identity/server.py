"""Engineered HTTPS identity server used by both the real-asset and decoy
containers. Serves a Server banner, configurable latency, and a configurable
monitoring response profile (immediate / rate_limited / silent) so the
prober can measure the declared surface from a live endpoint.

The management plane is exposed at POST /admin/identity so the live loop can
apply corrections to the served identity at runtime (banner / timing /
monitoring). It is intentionally separate from the probed surface.
"""

import http.server
import json
import os
import ssl
import threading
import time

PORT = int(os.environ.get("PORT", "8443"))
BANNER = os.environ.get("BANNER", "Apache/2.4.54 (Debian)")
TIMING_MS = float(os.environ.get("TIMING_MS", "0"))
MONITORING = os.environ.get("MONITORING", "immediate")
CERT = os.environ.get("CERT", "/srv/cert.pem")
KEY = os.environ.get("KEY", "/srv/key.pem")

_lock = threading.Lock()
_recent = []


class IdentityHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = BANNER
    sys_version = ""

    def _rate_limited(self):
        now = time.time()
        with _lock:
            _recent[:] = [t for t in _recent if now - t < 10]
            _recent.append(now)
            return len(_recent) > 5

    def _send_identity(self, body=b"<html><body>decoytell identity</body></html>"):
        self.server_version = BANNER
        self.sys_version = ""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if MONITORING == "silent":
            return
        if MONITORING == "rate_limited" and self._rate_limited():
            time.sleep(2.0)
        if TIMING_MS:
            time.sleep(TIMING_MS / 1000.0)
        self._send_identity()

    def do_POST(self):
        global BANNER, TIMING_MS, MONITORING
        if self.path != "/admin/identity":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            changes = json.loads(raw or b"{}")
        except ValueError:
            self.send_response(400)
            self.end_headers()
            return
        if "banner" in changes:
            BANNER = str(changes["banner"])
        if "timing_ms" in changes:
            TIMING_MS = float(changes["timing_ms"])
        if "monitoring" in changes:
            MONITORING = str(changes["monitoring"])
        payload = json.dumps({"banner": BANNER, "timing_ms": TIMING_MS,
                              "monitoring": MONITORING}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def main():
    server = http.server.HTTPServer(("0.0.0.0", PORT), IdentityHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT, KEY)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print("identity server on :%d banner=%r monitoring=%s timing=%sms" % (PORT, BANNER, MONITORING, TIMING_MS), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()