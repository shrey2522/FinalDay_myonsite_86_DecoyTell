"""Management-plane client for the identity server (live layer).

Applies identity changes (banner / timing / monitoring) to a running identity
container over its control endpoint — the live analogue of the corrector's
fix actions.
"""

import http.client
import json
import os

from .netutil import tls_context


def _load_local_env():
    """Minimal .env loader (no third-party dep): KEY=VALUE lines from the
    repo-local .env file, without overriding variables already set in the
    environment (compose-injected values win)."""
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
        return


_load_local_env()
# Fail closed: no usable default token. An unset DECOYTELL_CONTROL_TOKEN makes
# apply() refuse to run, so a misconfigured environment can never act against
# the control plane with a known fallback secret.
CONTROL_TOKEN = os.environ.get("DECOYTELL_CONTROL_TOKEN") or ""


def apply(host, port, changes, timeout=5.0):
    if not CONTROL_TOKEN:
        raise RuntimeError(
            "DECOYTELL_CONTROL_TOKEN is not set - refusing to call the control "
            "plane (fail-closed). Set it in .env or the environment."
        )
    conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=tls_context())
    body = json.dumps(changes)
    conn.request(
        "POST",
        "/admin/identity",
        body=body,
        headers={"Content-Type": "application/json",
                 "X-Decoytell-Token": CONTROL_TOKEN},
    )
    resp = conn.getresponse()
    resp.read()
    conn.close()
    return resp.status == 200