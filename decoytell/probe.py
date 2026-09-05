"""Real collector (live layer): measure the declared surface from a live endpoint.

Probes an HTTPS endpoint the way an attacker would and returns the 5-field
observation the engine already consumes. Stdlib-only.

Honest framing: banner, TLS-cert account age, and latency are real
measurements; patch cadence is inferred from a version->release timeline; the
monitoring profile is read from a controlled scan burst.
"""

import http.client
import os
import ssl
import tempfile
import time

from .netutil import tls_context

VERSION_RELEASE_DAYS = {
    "Apache/2.4.29": 730,
    "Apache/2.4.41": 365,
    "Apache/2.4.54": 60,
    "Apache/2.4.55": 5,
}

TIMING_FAST_MS = 150.0
TIMING_NOMINAL_MS = 900.0
DEFAULT_TIMEOUT = 3.0
DEFAULT_BURST = 6


def _decode_cert(sock):
    """Decode the peer certificate without verification (CERT_NONE).

    ``getpeercert()`` returns {} under CERT_NONE, so we take the binary DER
    form, convert it to PEM, and decode it via the stdlib certificate decoder
    (which expects a file path).
    """
    try:
        der = sock.getpeercert(binary_form=True)
        if not der:
            return {}
        pem = ssl.DER_cert_to_PEM_cert(der)
        path = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as fh:
                fh.write(pem)
                path = fh.name
            from ssl import _ssl

            return _ssl._test_decode_cert(path)
        finally:
            if path is not None:
                os.unlink(path)
    except Exception:
        return {}


def _request(host, port, timeout=DEFAULT_TIMEOUT):
    conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=tls_context())
    start = time.perf_counter()
    conn.request("GET", "/", headers={"User-Agent": "decoytell-probe/1.0"})
    try:
        cert = _decode_cert(conn.sock) if conn.sock is not None else {}
    except Exception:
        cert = {}
    resp = conn.getresponse()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    resp.read()
    conn.close()
    return {
        "banner": (resp.getheader("Server") or "").strip(),
        "elapsed_ms": elapsed_ms,
        "cert": cert,
    }


def timing_band(elapsed_ms):
    if elapsed_ms < TIMING_FAST_MS:
        return "fast"
    if elapsed_ms < TIMING_NOMINAL_MS:
        return "nominal"
    return "slow"


def patch_cadence(banner, version_map=None):
    version_map = version_map or VERSION_RELEASE_DAYS
    for version, days in version_map.items():
        if version in (banner or ""):
            return float(days)
    return 999.0


def account_age_days(cert):
    not_before = (cert or {}).get("notBefore")
    if not not_before:
        return 0.0
    issued = ssl.cert_time_to_seconds(not_before)
    return max(0.0, (time.time() - issued) / 86400.0)


def classify_monitoring(results, burst_size=DEFAULT_BURST):
    responded = sum(1 for r in results if r is not None and r.get("banner"))
    if responded == 0:
        return "silent"
    if responded >= burst_size:
        return "immediate"
    return "rate_limited"


def probe(host, port, version_map=None, burst_size=DEFAULT_BURST, timeout=DEFAULT_TIMEOUT):
    results = []
    for _ in range(burst_size):
        try:
            results.append(_request(host, port, timeout=timeout))
        except Exception:
            results.append(None)

    responses = [r for r in results if r is not None]
    monitoring = classify_monitoring(results, burst_size)
    if not responses:
        return {
            "service_banner": None,
            "patch_cadence_days": None,
            "timing_band": None,
            "account_age_days": None,
            "monitoring_behavior": monitoring,
        }

    first = responses[0]
    banner = first["banner"]
    best_latency = min(r["elapsed_ms"] for r in responses)
    return {
        "service_banner": banner,
        "patch_cadence_days": patch_cadence(banner, version_map),
        "timing_band": timing_band(best_latency),
        "account_age_days": round(account_age_days(first["cert"]), 1),
        "monitoring_behavior": monitoring,
    }