"""PostgreSQL observation store (live layer only, per ADR-0003 v2).

The engine stays pure stdlib + in-memory; this adapter persists observations
so the live loop can read the recent window from a real database. Requires
``psycopg``, installed only in the live/collector environment.
"""

import datetime

from .generator import Observation

try:
    import psycopg
except ImportError:  # pragma: no cover - dependency of the live layer only
    psycopg = None

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
)
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