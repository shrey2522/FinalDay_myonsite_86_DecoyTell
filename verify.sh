#!/bin/sh
# Containerized verification: the full test suite, then the demo.
# Exits non-zero on any test failure or any UNSAFE / INSUFFICIENT_DATA verdict.
set -e

python -m unittest discover tests
echo "== TESTS PASSED =="
python demo.py --json-dir out