"""FastAPI web layer (ADR-0005).

Reads the engine, the observation store, and the loop as JSON endpoints.
The live loop itself runs as a separate process (loop_service.py); the API
only reads its persisted events and toggles the loop-control row.
"""

import glob
import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .control import apply as control_apply
from .engine import run_scenario, verify
from .live import run_loop
from .probe import probe
from .store import ObservationStore, psycopg

SCENARIO_DIR = os.environ.get("DECOYTELL_SCENARIO_DIR", "scenarios")
WEB_DIST = os.environ.get("DECOYTELL_WEB_DIST", "web/dist")
DEFAULT_DSN = os.environ.get(
    "DECOYTELL_DSN", "postgres://decoytell:decoytell@localhost:5433/decoytell"
)
REAL_HOST = os.environ.get("DECOYTELL_REAL_HOST", "localhost")
REAL_PORT = int(os.environ.get("DECOYTELL_REAL_PORT", "8443"))
DECOY_HOST = os.environ.get("DECOYTELL_DECOY_HOST", "localhost")
DECOY_PORT = int(os.environ.get("DECOYTELL_DECOY_PORT", "8444"))


def _store():
    if psycopg is None:
        raise HTTPException(status_code=503, detail="psycopg not installed (live layer)")
    store = ObservationStore(psycopg.connect(DEFAULT_DSN))
    store.init_schema()
    return store


def _scenario_ids():
    return sorted(
        os.path.splitext(os.path.basename(path))[0]
        for path in glob.glob(os.path.join(SCENARIO_DIR, "*.json"))
    )


def _load_scenario(sid):
    path = os.path.join(SCENARIO_DIR, sid + ".json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="unknown scenario %r" % sid)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


app = FastAPI(title="DecoyTell API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
def status():
    store = _store()
    scenarios = []
    for sid in _scenario_ids():
        report = run_scenario(_load_scenario(sid))
        scenarios.append(
            {"id": sid, "verdict": report["verdict"],
             "expected": report.get("expected_verdict")}
        )
    return {
        "scenarios": scenarios,
        "loop": {"running": store.loop_running(),
                 "latest_event": store.latest_loop_event()},
    }


@app.get("/api/scenarios")
def scenarios():
    return [run_scenario(_load_scenario(sid)) for sid in _scenario_ids()]


@app.get("/api/scenarios/{sid}")
def scenario(sid: str):
    return run_scenario(_load_scenario(sid))


@app.get("/api/pairs")
def pairs(sid: str = "s3_pair_fingerprint"):
    report = run_scenario(_load_scenario(sid))
    return {"scenario": sid, "pairs": report["pairs"]}


@app.get("/api/observations")
def observations(target: str = "real-asset", days: int = 90):
    store = _store()
    rows = store.recent_window(days=days, target=target)
    return {
        "target": target,
        "days": days,
        "count": len(rows),
        "observations": [
            {field: getattr(obs, field) for field in (
                "days_ago", "service_banner", "patch_cadence_days", "timing_band",
                "account_age_days", "monitoring_behavior")}
            for obs in rows
        ],
    }


@app.get("/api/loop/events")
def loop_events(after: int = 0, limit: int = 100):
    store = _store()
    return {"events": store.loop_events_after(after_id=after, limit=limit)}


@app.post("/api/loop/start")
def loop_start():
    store = _store()
    store.set_loop_running(True)
    return {"running": True}


@app.post("/api/loop/stop")
def loop_stop():
    store = _store()
    store.set_loop_running(False)
    return {"running": False}


@app.post("/api/verify")
def verify_now():
    """One-shot cycle: probe real -> append -> probe decoy -> verify -> apply
    fixes -> re-verify, persisting the loop event."""
    store = _store()
    events = run_loop(
        probe,
        store,
        lambda changes: control_apply(DECOY_HOST, DECOY_PORT, changes),
        (REAL_HOST, REAL_PORT),
        (DECOY_HOST, DECOY_PORT),
        interval=0.0,
        cycles=1,
        log=lambda event: None,
    )
    return events[0]


if os.path.isdir(WEB_DIST):
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")