# T5 — Test hardening + README + Docker (issue #6)

## Problem statement (from the ticket)

The engine, corrector, scenarios, CLI and JSON proof all exist, but the deliverable
isn't finished until it is **provable and reproducible anywhere**: a hardened
behavioral test suite, operator-facing documentation, a byte-identical reproducibility
guarantee, and — per the decision recorded on this ticket — **containerized
verification** so the whole build runs and is verified inside an isolated,
reproducible environment.

## What we built (coding terms)

| Artifact | Responsibility |
|---|---|
| `README.md` | The declared surface table, the checks (individual + joint), the correction model, verdicts + exit codes, demo commands, JSON proof, testing, Docker |
| `Dockerfile` | `python:3.12-slim`, `WORKDIR /app`, `COPY . .`, `CMD sh /app/verify.sh` — stdlib-only, no pip installs |
| `.dockerignore` | excludes `.git`, `__pycache__`, `*.pyc`, `out/` |
| `verify.sh` | `set -e`; runs `python -m unittest discover tests` then `python demo.py --json-dir out` |
| `tests/test_cli.py` (extended) | Two new determinism tests: full demo stdout byte-identical across runs; JSON exports byte-identical across runs |

**Test suite: 26 tests** at the single `run_scenario` seam — `test_engine` (8),
`test_corrector` (5), `test_joint` (3), `test_cli` (8), `test_scenarios` (2). The
scenario tests load every `scenarios/*.json` and assert verdict == expected_verdict,
so the suite automatically covers all five scenarios (s1–s5).

## What this ticket solves (layman terms)

- **Documentation**: anyone (judge, next engineer) can read the README and understand
  the 5-attribute model, why the joint check matters, and how to run everything.
- **Reproducibility proof**: run the demo twice → byte-identical output. Same seed,
  same history, same verdict — no hidden randomness.
- **Isolated environment**: `docker build` + `docker run` verifies the full test suite
  and the demo inside a clean Linux container, so "works on my machine" becomes "works
  in a reproducible container". The gate fires correctly: non-zero exit on any test
  failure or any `UNSAFE`/`INSUFFICIENT_DATA` verdict.

## Design intent (why this way)

- **Tests at the seam only** (per the TDD skill): everything asserts *behavior* —
  verdicts, named attributes, report values — through `run_scenario` and `demo.main`,
  never internal calls. Refactors that preserve behavior cannot break the suite.
- **Determinism is a test, not a promise**: byte-identical assertions on the full CLI
  output and the JSON exports make reproducibility a checked invariant.
- **Docker mirrors the local gate**: `verify.sh` uses exactly the same commands as the
  local run (`unittest discover` + `demo.py`), so the container and the laptop verify
  the identical thing. `python:3.12-slim` + `COPY . .` keeps it dependency-free
  (ADR-0003 holds inside the container).

## Alternatives considered and rejected

| Alternative | Why rejected |
|---|---|
| README only, no container | The recorded T5 decision explicitly adds containerized verification; the isolated env is the reproducibility guarantee for judging |
| Install pip dependencies in the image | There are none (stdlib-only); adding a package manager step would contradict ADR-0003 |
| A heavy base image (`python:3.12`) | `slim` is smaller and sufficient — nothing needs build tools |
| Determinism "by construction" only (no test) | A claim without a test is unverifiable; the byte-identical assertions make it checkable |
| One giant combined test file | Tests are grouped by behavior (engine/corrector/joint/cli/scenarios) so failures localise |

## How to check

```
python -m unittest discover tests          # 26 tests, OK (locally)
docker build -t decoytell .                # image builds
docker run --rm decoytell                  # tests + demo in-container; exit 2 (gate on s4/s5)
docker run --rm decoytell sh -c "python demo.py --scenario s1"   # clean run, exit 0
python demo.py                             # all five scenarios, verdicts printed
python demo.py --scenario s2               # deterministic single run
```

**Reproducibility:** run `python demo.py` twice (or `python demo.py --scenario s3`
twice) — output is byte-identical; the same holds for the `out/*.json` exports (both
asserted by tests).

## Status

✅ Implemented, tested (26 green locally AND inside the container), committed on `main`
(`T5` commit).