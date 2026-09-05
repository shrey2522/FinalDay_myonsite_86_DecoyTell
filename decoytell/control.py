"""Management-plane client for the identity server (live layer).

Applies identity changes (banner / timing / monitoring) to a running identity
container over its control endpoint — the live analogue of the corrector's
fix actions.
"""

import http.client
import json
import ssl


def _context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def apply(host, port, changes, timeout=5.0):
    conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=_context())
    body = json.dumps(changes)
    conn.request(
        "POST",
        "/admin/identity",
        body=body,
        headers={"Content-Type": "application/json"},
    )
    resp = conn.getresponse()
    resp.read()
    conn.close()
    return resp.status == 200