# ADR-0005: Web/API layer + loop-as-service architecture

The monitoring dashboard needs a web layer and a way to observe and control the live
loop. The web layer is a FastAPI application (uvicorn) exposing the engine, the
observation store, and the loop as JSON endpoints; it extends the ADR-0003 v2 carve-out
(fastapi/uvicorn join psycopg in the live/web layer, isolated; the core engine remains
pure stdlib + in-memory). The live loop runs as its **own standalone process**, not a
thread inside the API: each cycle it persists a loop event to PostgreSQL and polls a
loop-control row; the API only reads events and toggles the control row. This keeps the
loop alive across API restarts and the API alive across loop crashes — PostgreSQL is the
single source of truth for both.