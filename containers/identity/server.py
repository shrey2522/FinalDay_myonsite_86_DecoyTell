"""Engineered HTTPS identity server used by both the real-asset and decoy
containers. Serves a Server banner, configurable latency, and a configurable
monitoring response profile (immediate / rate_limited / silent) so the
prober can measure the declared surface from a live endpoint.

The management plane is exposed at POST /admin/identity so the live loop can
apply corrections to the served identity at runtime (banner / timing /
monitoring). It is intentionally separate from the probed surface.

The control plane can also re-issue the TLS certificate with a backdated
notBefore (``account_age_days``), which is the live analogue of a decoy
operator installing a fresh or re-issued certificate -- the resulting
account-age drift is NOT auto-correctable by the loop (the cert is baked at
build time in the real flow), so the loop must flag it for human
intervention. The new cert is swapped into the live SSLContext via
``load_cert_chain``; no listener restart is needed.
"""

import http.server
import json
import os
import ssl
import subprocess
import tempfile
import threading
import time

PORT = int(os.environ.get("PORT", "8443"))
BANNER = os.environ.get("BANNER", "Apache/2.4.54 (Debian)")
TIMING_MS = float(os.environ.get("TIMING_MS", "0"))
MONITORING = os.environ.get("MONITORING", "immediate")
CERT = os.environ.get("CERT", "/srv/cert.pem")
KEY = os.environ.get("KEY", "/srv/key.pem")
ACCOUNT_AGE_DAYS = 800.0
# Fail closed: no default token. When unset, every /admin/identity request is
# rejected (401), so a misconfigured deployment can never be taken over with a
# known fallback secret.
CONTROL_TOKEN = os.environ.get("DECOYTELL_CONTROL_TOKEN") or ""
CERT_CN = os.environ.get("CERT_CN", "www.example.com")

_lock = threading.Lock()
_recent = []
_in_flight = 0
_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
LOAD_DELAY_MS_PER_CONN = float(os.environ.get("LOAD_DELAY_MS_PER_CONN", "50"))
LOAD_DELAY_CAP_MS = float(os.environ.get("LOAD_DELAY_CAP_MS", "400"))

_CA_CONFIG = """\
[ ca ]
default_ca = ca_default
[ ca_default ]
database = {ca}/index.txt
serial = {ca}/serial
new_certs_dir = {ca}
private_key = {key}
certificate = {cert}
default_md = sha256
policy = policy_any
[ policy_any ]
commonName = supplied
[ req ]
distinguished_name = dn
prompt = no
[ dn ]
CN = {cn}
"""


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
        global _in_flight
        with _lock:
            _in_flight += 1
        try:
            if MONITORING == "silent":
                return
            if MONITORING == "rate_limited" and self._rate_limited():
                time.sleep(2.0)
            if TIMING_MS:
                time.sleep(TIMING_MS / 1000.0)
            else:
                # Synthetic load-correlated delay: LOAD_DELAY_MS_PER_CONN per
                # concurrent connection beyond the first, capped at
                # LOAD_DELAY_CAP_MS, so the server degrades plausibly under
                # concurrent load instead of answering at constant speed.
                # The prober is sequential (in_flight == 1), so the declared
                # idle timing band is unaffected by this delay.
                concurrent = max(0, _in_flight - 1)
                extra_ms = min(concurrent,
                               LOAD_DELAY_CAP_MS / LOAD_DELAY_MS_PER_CONN) \
                    * LOAD_DELAY_MS_PER_CONN
                if extra_ms > 0:
                    time.sleep(extra_ms / 1000.0)
            self._send_identity()
        finally:
            with _lock:
                _in_flight -= 1

    def do_POST(self):
        global BANNER, TIMING_MS, MONITORING, ACCOUNT_AGE_DAYS
        if self.path != "/admin/identity":
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.headers.get("X-Decoytell-Token") != CONTROL_TOKEN:
            self.send_response(401)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            changes = json.loads(raw or b"{}")
        except ValueError:
            self.send_response(400)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        try:
            if "banner" in changes:
                BANNER = str(changes["banner"])
            if "timing_ms" in changes:
                TIMING_MS = float(changes["timing_ms"])
            if "monitoring" in changes:
                MONITORING = str(changes["monitoring"])
        except Exception:
            self.send_response(400)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if "account_age_days" in changes:
            try:
                age = float(changes["account_age_days"])
                _reissue_cert(age)
                ACCOUNT_AGE_DAYS = age
            except Exception:
                self.send_response(500)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
        payload = json.dumps({"banner": BANNER, "timing_ms": TIMING_MS,
                              "monitoring": MONITORING,
                              "account_age_days": ACCOUNT_AGE_DAYS}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def _reissue_cert(age_days):
    """Regenerate the self-signed cert with a backdated notBefore so the
    served TLS account age reflects ``age_days``. New key/cert are written to
    a temp dir and swapped in atomically, then loaded into the live
    SSLContext (future handshakes present the new cert)."""
    now = time.time()
    start = time.strftime("%y%m%d%H%M%S", time.gmtime(now - age_days * 86400)) + "Z"
    end = time.strftime("%y%m%d%H%M%S", time.gmtime(now + 3650 * 86400)) + "Z"
    with tempfile.TemporaryDirectory() as workdir:
        ca_dir = os.path.join(workdir, "ca")
        os.makedirs(ca_dir)
        with open(os.path.join(ca_dir, "index.txt"), "w"):
            pass
        with open(os.path.join(ca_dir, "serial"), "w") as fh:
            fh.write("1000\n")
        cnf = os.path.join(workdir, "ca.cnf")
        with open(cnf, "w") as fh:
            fh.write(_CA_CONFIG.format(ca=ca_dir, key=KEY, cert=CERT, cn=CERT_CN))
        new_key = os.path.join(workdir, "key.pem")
        new_cert = os.path.join(workdir, "cert.pem")
        req = os.path.join(workdir, "req.pem")
        subprocess.run(
            ["openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes",
             "-keyout", new_key, "-out", req, "-subj", "/CN=%s" % CERT_CN,
             "-config", cnf],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["openssl", "ca", "-selfsign", "-config", cnf, "-keyfile", new_key,
             "-in", req, "-out", new_cert, "-startdate", start,
             "-enddate", end, "-batch"],
            check=True, capture_output=True,
        )
        os.replace(new_cert, CERT)
        os.replace(new_key, KEY)
    _CONTEXT.load_cert_chain(CERT, KEY)


def _start_server():
    """Serve once on PORT with the cert currently on disk. Threading server so
    concurrent requests actually overlap (the load-correlated delay and the
    monitoring rate-limiter are meaningful only under concurrency). Module
    globals (banner/timing/monitoring) live in the process and survive any
    later certificate swap."""
    _CONTEXT.load_cert_chain(CERT, KEY)
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), IdentityHandler)
    server.socket = _CONTEXT.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()


def main():
    _start_server()
    print("identity server on :%d banner=%r monitoring=%s timing=%sms"
          % (PORT, BANNER, MONITORING, TIMING_MS), flush=True)
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()