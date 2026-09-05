# ADR-0003 (v2): Core engine stdlib-only; live/collector layer may use a database

The core verification engine uses only the Python standard library: no third-party
packages, no network, no evaluation of data files. This guarantees the comparison,
correction, and certification logic runs anywhere, including offline, and its tests
stay dependency-free.

**v2 amendment (live integration):** the *core engine* remains pure stdlib and
in-memory. The *live/collector layer* — the prober and the observation store that feed
the engine from real servers — may use a database (PostgreSQL) and its client library
(`psycopg`), isolated to that layer and its own tests. The core image stays pip-free;
the 29 core tests run with no live dependencies installed. Data files (scenario
declarations) are parsed, never executed.