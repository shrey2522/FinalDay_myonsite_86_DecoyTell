"""Live integration verification: compose up -> seed -> short live loop -> green.

Runs the full containerized workflow against the real Docker stack and exits
non-zero on any failure. Requires: Docker running, psycopg installed, and the
stack built (docker compose build).

Usage:
    python verify_live.py
"""

import os
import subprocess
import sys
import time


def _sh(args):
    return subprocess.run(args, capture_output=True, text=True)


def check(name, fn):
    try:
        fn()
        print("PASS  %s" % name)
    except AssertionError as exc:
        print("FAIL  %s: %s" % (name, exc))
        raise SystemExit(1)


def main():
    import psycopg

    from decoytell.control import apply as control_apply
    from decoytell.live import run_loop
    from decoytell.probe import probe
    from decoytell.store import ObservationStore

    dsn = os.environ.get(
        "DECOYTELL_DSN", "postgres://decoytell:decoytell@localhost:5433/decoytell"
    )
    REAL_HOST, REAL_PORT = "localhost", 8443
    DECOY_HOST, DECOY_PORT = "localhost", 8444

    def containers_up():
        result = _sh(["docker", "compose", "ps", "--format", "json"])
        assert result.returncode == 0, "docker compose ps failed: %s" % result.stderr
        names = []
        for line in result.stdout.strip().splitlines():
            entry = _sh(["python", "-c", "import json,sys;d=json.loads(sys.argv[1]);print(d['Name']+' '+d['State']+' '+(d.get('Health') or '-'))", line])
            names.append(entry.stdout.strip())
        joined = "\n".join(names)
        for needle in ("real-asset-1 running", "decoy-1 running", "postgres-1 running"):
            assert needle in joined, "missing container state: %s\n%s" % (needle, joined)
        assert "postgres-1 running healthy" in joined, "postgres not healthy"

    def store_reachable_and_seedable():
        store = ObservationStore(psycopg.connect(dsn))
        store.init_schema()
        with store.conn.cursor() as cur:
            cur.execute("DELETE FROM observations WHERE target NOT LIKE 'test-%'")
        store.conn.commit()
        from decoytell.generator import generate_history

        store.seed(generate_history(7001), target="real-asset")
        window = store.recent_window(days=90, target="real-asset")
        assert len(window) >= 100, "seeded window too small: %d" % len(window)

    def decoy_probe_reflects_identity():
        broken = control_apply(DECOY_HOST, DECOY_PORT, {
            "banner": "Apache/2.4.29 (Debian)", "timing_ms": 1500,
            "monitoring": "immediate", "account_age_days": 800,
        })
        assert broken, "control plane refused the break"
        time.sleep(0.3)
        obs = probe(DECOY_HOST, DECOY_PORT)
        assert obs["service_banner"] == "Apache/2.4.29 (Debian)", "decoy banner not applied: %r" % obs["service_banner"]
        assert obs["timing_band"] == "slow", "decoy timing not applied: %s" % obs["timing_band"]

    def loop_catches_and_corrects():
        from decoytell.generator import generate_history
        store = ObservationStore(psycopg.connect(dsn))
        store.init_schema()

        events = run_loop(
            probe,
            store,
            lambda changes: control_apply(DECOY_HOST, DECOY_PORT, changes),
            (REAL_HOST, REAL_PORT),
            (DECOY_HOST, DECOY_PORT),
            interval=0.0,
            cycles=3,
            log=lambda e: None,
        )
        assert events[0]["verdict"] == "CORRECTED", "cycle 1 not CORRECTED: %s" % events[0]["verdict"]
        assert events[0]["recheck"] == "PASS", "cycle 1 recheck not PASS: %s" % events[0]["recheck"]
        assert all(e["verdict"] == "PASS" for e in events[1:]), "post-fix cycles not PASS"

    def decoy_now_matches_real():
        obs = probe(DECOY_HOST, DECOY_PORT)
        assert obs["service_banner"] == "Apache/2.4.54 (Debian)", "decoy banner not corrected: %r" % obs["service_banner"]
        assert obs["timing_band"] == "fast", "decoy timing not corrected: %s" % obs["timing_band"]
        real = probe(REAL_HOST, REAL_PORT)
        assert real["service_banner"] == "Apache/2.4.54 (Debian)", "real-asset banner unexpected: %r" % real["service_banner"]
        assert real["account_age_days"] > 700, "real-asset account age unexpected: %s" % real["account_age_days"]

    print("DecoyTell live integration verification")
    print("Honest framing: real probing of containerized servers in an isolated Docker")
    print("environment; timing/scan attributes are measured against engineered")
    print("container configuration, not a production network.")
    print("-" * 60)
    check("containers up (real-asset, decoy, postgres healthy)", containers_up)
    check("store reachable, seeded window >= 100 obs", store_reachable_and_seedable)
    check("decoy probe reflects the flawed identity", decoy_probe_reflects_identity)
    check("loop catches drift and corrects to green", loop_catches_and_corrects)
    check("decoy now matches the real asset", decoy_now_matches_real)
    print("-" * 60)
    print("ALL LIVE CHECKS PASSED")


if __name__ == "__main__":
    main()