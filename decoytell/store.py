"""PostgreSQL observation store (live layer only, per ADR-0003 v2).

The engine stays pure stdlib + in-memory; this adapter persists observations
so the live loop can read the recent window from a real database. Requires
``psycopg``, installed only in the live/collector environment.
"""

import datetime
import json

from .generator import Observation

try:
    import psycopg
except ImportError:  # pragma: no cover - dependency of the live layer only
    psycopg = None


def _dumps(value):
    return json.dumps(value) if value is not None else None


def _event_row(row):
    return {
        "id": row[0],
        "cycle": row[1],
        "timestamp": row[2].isoformat(),
        "verdict": row[3],
        "recheck": row[4],
        "fixes": row[5],
        "real_obs": row[6],
        "decoy_obs": row[7],
    }

_SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id BIGSERIAL PRIMARY KEY,
    observed_at TIMESTAMPTZ NOT NULL,
    target TEXT NOT NULL,
    service_banner TEXT,
    patch_cadence_days DOUBLE PRECISION,
    timing_band TEXT,
    account_age_days DOUBLE PRECISION,
    monitoring_behavior TEXT
);
CREATE TABLE IF NOT EXISTS loop_events (
    id BIGSERIAL PRIMARY KEY,
    cycle BIGINT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    verdict TEXT NOT NULL,
    recheck TEXT NOT NULL,
    fixes JSONB NOT NULL DEFAULT '[]',
    real_probe JSONB,
    decoy_probe JSONB
);
CREATE TABLE IF NOT EXISTS loop_control (
    id INT PRIMARY KEY CHECK (id = 1),
    running BOOLEAN NOT NULL
);
"""

_INSERT = """
INSERT INTO observations
    (observed_at, target, service_banner, patch_cadence_days,
     timing_band, account_age_days, monitoring_behavior)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

_FIELDS = (
    "service_banner",
    "patch_cadence_days",
    "timing_band",
    "account_age_days",
    "monitoring_behavior",
)


def _as_observation(row, now):
    observed_at = row[0]
    values = row[1:]
    days_ago = round((now - observed_at).total_seconds() / 86400.0, 1)
    return Observation(days_ago=days_ago, **dict(zip(_FIELDS, values)))


class ObservationStore:
    def __init__(self, conn):
        self.conn = conn

    def init_schema(self):
        with self.conn.cursor() as cur:
            cur.execute(_SCHEMA)
            cur.execute(
                "INSERT INTO loop_control (id, running) VALUES (1, false) "
                "ON CONFLICT (id) DO NOTHING"
            )
        self.conn.commit()

    def seed(self, observations, target="real-asset"):
        """Insert a synthetic/mock history as historical observations."""
        now = datetime.datetime.now(datetime.timezone.utc)
        with self.conn.cursor() as cur:
            for obs in observations:
                observed_at = now - datetime.timedelta(days=obs.days_ago)
                cur.execute(
                    _INSERT,
                    (observed_at, target, obs.service_banner, obs.patch_cadence_days,
                     obs.timing_band, obs.account_age_days, obs.monitoring_behavior),
                )
        self.conn.commit()

    def append(self, observation, target="decoy", observed_at=None):
        """Store one live observation (dict or Observation)."""
        now = observed_at or datetime.datetime.now(datetime.timezone.utc)
        with self.conn.cursor() as cur:
            cur.execute(
                _INSERT,
                (now, target, observation["service_banner"], observation["patch_cadence_days"],
                 observation["timing_band"], observation["account_age_days"],
                 observation["monitoring_behavior"]),
            )
        self.conn.commit()

    def recent_window(self, days=90, target=None):
        """The last ``days`` of observations, as engine ``Observation``s."""
        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff = now - datetime.timedelta(days=days)
        columns = ", ".join(_FIELDS)
        sql = "SELECT observed_at, %s FROM observations WHERE observed_at >= %%s" % columns
        params = [cutoff]
        if target is not None:
            sql += " AND target = %s"
            params.append(target)
        sql += " ORDER BY observed_at"
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            result = [_as_observation(row, now) for row in cur.fetchall()]
        return result

    # --- loop events / control (web layer) ---

    def record_loop_event(self, cycle, timestamp, verdict, recheck, fixes,
                          real_obs, decoy_obs):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO loop_events "
                "(cycle, observed_at, verdict, recheck, fixes, real_probe, decoy_probe) "
                "VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)",
                (cycle, timestamp, verdict, recheck,
                 _dumps(fixes), _dumps(real_obs), _dumps(decoy_obs)),
            )
        self.conn.commit()

    def loop_events_after(self, after_id=0, limit=100):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, cycle, observed_at, verdict, recheck, fixes, "
                "real_probe, decoy_probe FROM loop_events "
                "WHERE id > %s ORDER BY id LIMIT %s",
                (after_id, limit),
            )
            return [_event_row(row) for row in cur.fetchall()]

    def latest_loop_event(self):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, cycle, observed_at, verdict, recheck, fixes, "
                "real_probe, decoy_probe FROM loop_events "
                "ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
        return _event_row(row) if row else None

    def set_loop_running(self, running):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO loop_control (id, running) VALUES (1, %s) "
                "ON CONFLICT (id) DO UPDATE SET running = EXCLUDED.running",
                (bool(running),),
            )
        self.conn.commit()

    def loop_running(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT running FROM loop_control WHERE id = 1")
            row = cur.fetchone()
        return bool(row[0]) if row else False