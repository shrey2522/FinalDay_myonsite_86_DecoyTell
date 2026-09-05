"""Shared TLS helpers for the live layer (prober + control plane)."""

import ssl


def tls_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx