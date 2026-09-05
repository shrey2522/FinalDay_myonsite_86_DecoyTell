"""T4: unsafe / insufficient-data verdicts, scriptable CLI, and JSON proof."""

import contextlib
import io
import json
import os
import tempfile
import unittest

from decoytell.engine import run_scenario
import demo

BASE = os.path.join(os.path.dirname(__file__), "..", "scenarios")


def _load(name):
    with open(os.path.join(BASE, name), encoding="utf-8") as fh:
        return json.load(fh)


class VerdictPathTests(unittest.TestCase):
    def test_s4_uncorrectable_is_unsafe_and_names_blocked_attributes(self):
        report = run_scenario(_load("s4_uncorrectable.json"))
        self.assertEqual(report["verdict"], "UNSAFE")
        self.assertIn("timing_band", report["blocked_attributes"])
        self.assertIn("monitoring_behavior", report["blocked_attributes"])
        self.assertEqual(report["corrections"], [])

    def test_s5_insufficient_data_refuses_to_certify(self):
        report = run_scenario(_load("s5_insufficient_data.json"))
        self.assertEqual(report["verdict"], "INSUFFICIENT_DATA")
        self.assertLess(report["window_size"], 100)


class CliTests(unittest.TestCase):
    def _run(self, argv):
        return demo.main(argv)

    def test_exit_zero_when_all_certifiable(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self._run(["--scenario", "s1"]), 0)
            self.assertEqual(self._run(["--scenario", "s2"]), 0)
            self.assertEqual(self._run(["--scenario", "s3"]), 0)

    def test_exit_one_when_any_unsafe(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self._run(["--scenario", "s4"]), 1)

    def test_exit_two_when_any_insufficient_data(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self._run(["--scenario", "s5"]), 2)

    def test_json_proof_export_is_complete(self):
        with contextlib.redirect_stdout(io.StringIO()):
            with tempfile.TemporaryDirectory() as out:
                self.assertEqual(self._run(["--scenario", "s3", "--json-dir", out]), 0)
                with open(os.path.join(out, "s3_pair_fingerprint.json"), encoding="utf-8") as fh:
                    report = json.load(fh)
        for key in ("thresholds", "window_size", "attributes", "pairs", "corrections", "final", "verdict"):
            self.assertIn(key, report)
        self.assertEqual(report["verdict"], "CORRECTED")

    def test_full_demo_output_is_byte_identical_across_runs(self):
        with tempfile.TemporaryDirectory() as out:
            first = io.StringIO()
            second = io.StringIO()
            with contextlib.redirect_stdout(first):
                self.assertEqual(self._run(["--json-dir", out]), 2)
            with contextlib.redirect_stdout(second):
                self.assertEqual(self._run(["--json-dir", out]), 2)
            self.assertEqual(first.getvalue(), second.getvalue())

    def test_json_exports_are_byte_identical_across_runs(self):
        with tempfile.TemporaryDirectory() as out:
            with contextlib.redirect_stdout(io.StringIO()):
                self._run(["--json-dir", out])
            exports = {}
            for path in os.listdir(out):
                with open(os.path.join(out, path), "rb") as fh:
                    exports[path] = fh.read()
            with contextlib.redirect_stdout(io.StringIO()):
                self._run(["--json-dir", out])
            for path in exports:
                with open(os.path.join(out, path), "rb") as fh:
                    self.assertEqual(exports[path], fh.read(), path)


if __name__ == "__main__":
    unittest.main()