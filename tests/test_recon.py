"""Recon layer tests: scoring determinism + the narrated flow end-to-end."""

import unittest

from decoytell.generator import generate_history

from recon.candidates import build_candidates
from recon.demo_recon import main, run_demo
from recon.observe import observe_target
from recon.scoring import rank_candidates, score_candidate, select_target

OLD_DECOY_OBS = {
    "service_banner": "Apache/2.4.29 (Debian)",
    "patch_cadence_days": 730.0,
    "timing_band": "slow",
    "account_age_days": 900.0,
    "monitoring_behavior": "silent",
}

FRESH_DECOY_OBS = {
    "service_banner": "Apache/2.4.55 (Debian)",
    "patch_cadence_days": 5.0,
    "timing_band": "fast",
    "account_age_days": 10.0,
    "monitoring_behavior": "immediate",
}

# Matches the generated real-asset window (see tests/test_live.py REAL_OBS).
HEALTHY_DECOY_OBS = {
    "service_banner": "Apache/2.4.54 (Debian)",
    "patch_cadence_days": 12.0,
    "timing_band": "fast",
    "account_age_days": 810.0,
    "monitoring_behavior": "immediate",
}

UNREACHABLE_OBS = {
    "service_banner": None,
    "patch_cadence_days": None,
    "timing_band": None,
    "account_age_days": None,
    "monitoring_behavior": "silent",
}


class FakeProbe:
    def __init__(self, decoy_obs, real_obs=None):
        self.decoy_obs = decoy_obs
        self.real_obs = real_obs if real_obs is not None else decoy_obs

    def __call__(self, host, port):
        if port == 8444:
            return self.decoy_obs
        return self.real_obs


class CandidatePoolTests(unittest.TestCase):
    def test_decoy_candidate_derived_from_live_probe_not_hardcoded(self):
        probe = FakeProbe(OLD_DECOY_OBS)
        candidates = build_candidates(None, probe=probe)
        decoy = next(c for c in candidates if c.is_decoy)
        self.assertTrue(decoy.banner_visible)
        self.assertTrue(decoy.reachable)
        self.assertEqual(decoy.patch_age_days, 730)
        self.assertFalse(decoy.has_auth)

    def test_pool_is_small_and_fixed_with_one_decoy(self):
        candidates = build_candidates(HEALTHY_DECOY_OBS)
        self.assertGreaterEqual(len(candidates), 4)
        self.assertLessEqual(len(candidates), 6)
        self.assertEqual(sum(1 for c in candidates if c.is_decoy), 1)

    def test_fake_candidates_are_less_attractive_by_construction(self):
        candidates = build_candidates(HEALTHY_DECOY_OBS)
        for c in candidates:
            if not c.is_decoy:
                self.assertTrue(c.has_auth)
                self.assertFalse(c.banner_visible)
                self.assertLess(c.patch_age_days, 90)


class ScoringTests(unittest.TestCase):
    def test_decoy_always_wins_for_old_unmaintained_state(self):
        selected, ranked = select_target(build_candidates(OLD_DECOY_OBS))
        self.assertTrue(selected.is_decoy)
        decoy_score = next(s for c, s, _ in ranked if c.is_decoy)
        self.assertEqual(decoy_score, 7)  # banner +1, no auth +3, patch +3
        for c, s, _ in ranked:
            if not c.is_decoy:
                self.assertLess(s, decoy_score)

    def test_decoy_wins_even_when_freshly_patched(self):
        # A freshly patched decoy loses the patch bonus but still wins on
        # banner exposure + missing auth: selection is deterministic.
        selected, ranked = select_target(build_candidates(FRESH_DECOY_OBS))
        self.assertTrue(selected.is_decoy)
        decoy_score = next(s for c, s, _ in ranked if c.is_decoy)
        self.assertEqual(decoy_score, 4)  # banner +1, no auth +3, patch 0
        for c, s, _ in ranked:
            if not c.is_decoy:
                self.assertLess(s, decoy_score)

    def test_unreachable_decoy_is_deprioritized(self):
        selected, ranked = select_target(build_candidates(UNREACHABLE_OBS))
        self.assertIsNotNone(selected)
        self.assertFalse(selected.is_decoy)
        decoy_score = next(s for c, s, _ in ranked if c.is_decoy)
        self.assertLess(decoy_score, 0)

    def test_reasons_are_human_readable(self):
        candidates = build_candidates(OLD_DECOY_OBS)
        decoy = next(c for c in candidates if c.is_decoy)
        score, reasons = score_candidate(decoy)
        self.assertEqual(score, 7)
        self.assertIn("outdated patch (>365 days) suggests unmaintained asset", reasons)
        self.assertIn("no authentication layer detected", reasons)
        self.assertIn("service banner exposed, easy fingerprinting", reasons)


class ObserveTests(unittest.TestCase):
    def test_observe_reuses_probe_and_returns_observation(self):
        probe = FakeProbe(HEALTHY_DECOY_OBS)
        lines = []
        obs = observe_target("localhost", 8444, probe=probe, log=lines.append)
        self.assertEqual(obs, HEALTHY_DECOY_OBS)
        self.assertTrue(any("attacker is now observing" in line for line in lines))
        for name in ("service_banner", "timing_band", "patch_cadence_days",
                     "account_age_days", "monitoring_behavior"):
            self.assertIn(name, obs)


class NarrationTests(unittest.TestCase):
    def _run(self, decoy_obs, **kwargs):
        return run_demo(probe_fn=FakeProbe(decoy_obs),
                        real_window=generate_history(3001), **kwargs)

    def test_full_flow_selects_decoy_verifies_and_passes(self):
        lines = []
        result = self._run(HEALTHY_DECOY_OBS, log=lines.append)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["phases"], ["recon", "observe", "verify"])
        self.assertEqual(result["verdict"], "PASS")
        text = "\n".join(lines)
        for header in ("PHASE 1: RECONNAISSANCE", "PHASE 2: PRE-ATTACK OBSERVATION",
                       "PHASE 3: DECOYTELL VERIFICATION"):
            self.assertIn(header, text)
        self.assertIn("Selected target: old-admin-panel.internal", text)
        self.assertIn("no authentication layer detected", text)
        self.assertIn("RESULT: attacker's reconnaissance-selected target",
                      text)

    def test_flow_reports_correction_when_decoy_is_drifted(self):
        result = self._run(OLD_DECOY_OBS, log=lambda line: None)
        self.assertEqual(result["verdict"], "CORRECTED")
        self.assertGreaterEqual(len(result["corrections"]), 1)

    def test_unreachable_target_ends_flow_without_verification(self):
        result = self._run(UNREACHABLE_OBS, log=lambda line: None)
        self.assertEqual(result["verdict"], "UNREACHABLE")
        self.assertEqual(result["exit_code"], 1)
        self.assertNotIn("verify", result["phases"])

    def test_store_backed_flow_mirrors_live_loop_semantics(self):
        class FakeStore:
            def __init__(self, history):
                self.history = history
                self.appends = []

            def append(self, obs, target="decoy"):
                self.appends.append((target, obs))

            def recent_window(self, days=90, target=None):
                return self.history

        store = FakeStore(generate_history(3001))
        result = run_demo(
            probe_fn=FakeProbe(HEALTHY_DECOY_OBS),
            store=store,
            log=lambda line: None,
        )
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual([t for t, _ in store.appends], ["real-asset"])

    def test_unreachable_real_asset_escalates_in_store_mode(self):
        class FakeStore:
            def append(self, obs, target="decoy"):
                pass

            def recent_window(self, days=90, target=None):
                return generate_history(3001)

        result = run_demo(
            probe_fn=FakeProbe(HEALTHY_DECOY_OBS, real_obs=UNREACHABLE_OBS),
            store=FakeStore(),
            log=lambda line: None,
        )
        self.assertEqual(result["verdict"], "MIRRORING_REQUIRED")
        self.assertEqual(result["exit_code"], 1)

    def test_demo_requires_a_baseline(self):
        with self.assertRaises(ValueError):
            run_demo(probe_fn=FakeProbe(HEALTHY_DECOY_OBS))

    def test_cli_main_runs_end_to_end_offline(self):
        from recon import demo_recon

        original = demo_recon.default_probe
        demo_recon.default_probe = FakeProbe(HEALTHY_DECOY_OBS)
        try:
            self.assertEqual(main(["--no-store", "--seed", "3001"]), 0)
        finally:
            demo_recon.default_probe = original


class EdgeCaseTests(unittest.TestCase):
    """Audit-driven: every flaw below was found by probing the recon layer's
    edge cases; each test documents one defect before its fix."""

    def _run(self, decoy_obs, window=None, **kwargs):
        return run_demo(
            probe_fn=FakeProbe(decoy_obs),
            real_window=window if window is not None else generate_history(3001),
            log=lambda line: None,
            **kwargs
        )

    def test_decoy_wins_for_any_reachable_state(self):
        # The PRD's core promise: construction must make the decoy win for any
        # reachable live state, not just the curated demo one.
        for obs in (OLD_DECOY_OBS, FRESH_DECOY_OBS, HEALTHY_DECOY_OBS,
                    {"service_banner": "custom/1.0", "patch_cadence_days": 999.0,
                     "timing_band": "nominal", "account_age_days": 800.0,
                     "monitoring_behavior": "rate_limited"}):
            selected, _ = select_target(build_candidates(obs))
            self.assertTrue(selected.is_decoy, obs)

    def test_empty_banner_host_is_reachable_but_not_banner_visible(self):
        # live.py treats "no Server header" (banner == "") as reachable; the
        # recon layer must classify identically (flaw 2: truthiness vs None).
        obs = {"service_banner": "", "patch_cadence_days": 400.0,
               "timing_band": "slow", "account_age_days": 900.0,
               "monitoring_behavior": "silent"}
        decoy = next(c for c in build_candidates(obs) if c.is_decoy)
        self.assertTrue(decoy.reachable)
        self.assertFalse(decoy.banner_visible)
        selected, _ = select_target(build_candidates(obs))
        self.assertTrue(selected.is_decoy)

    def test_insufficient_data_exits_nonzero(self):
        small = generate_history(3001)[:10]
        result = self._run(HEALTHY_DECOY_OBS, window=small)
        self.assertEqual(result["verdict"], "INSUFFICIENT_DATA")
        self.assertEqual(result["exit_code"], 1)

    def test_stale_window_exits_nonzero(self):
        stale = [o for o in generate_history(3001) if 1.0 < o.days_ago <= 90]
        self.assertGreaterEqual(len(stale), 100)
        result = self._run(HEALTHY_DECOY_OBS, window=stale)
        self.assertEqual(result["verdict"], "STALE_DATA")
        self.assertEqual(result["exit_code"], 1)

    def test_unsafe_verdict_exits_nonzero(self):
        obs = dict(HEALTHY_DECOY_OBS, monitoring_behavior="weird")
        result = self._run(obs)
        self.assertEqual(result["verdict"], "UNSAFE")
        self.assertEqual(result["exit_code"], 1)

    def test_malformed_observation_is_reported_not_crashing(self):
        malformed = dict(HEALTHY_DECOY_OBS)
        del malformed["monitoring_behavior"]
        result = self._run(malformed)
        self.assertEqual(result["verdict"], "MALFORMED_OBSERVATION")
        self.assertEqual(result["exit_code"], 1)

    def test_narration_is_deterministic_across_runs(self):
        first, second = [], []
        run_demo(probe_fn=FakeProbe(HEALTHY_DECOY_OBS),
                 real_window=generate_history(3001), log=first.append)
        run_demo(probe_fn=FakeProbe(HEALTHY_DECOY_OBS),
                 real_window=generate_history(3001), log=second.append)
        self.assertEqual(first, second)

    def test_score_lookup_survives_reconstructed_candidate_pool(self):
        from recon.demo_recon import run_demo as _rd
        from recon.scoring import score_of

        selected, ranked = select_target(build_candidates(HEALTHY_DECOY_OBS))
        rebuilt_ranked = rank_candidates(build_candidates(HEALTHY_DECOY_OBS))
        score, reasons = score_of(rebuilt_ranked, selected)
        self.assertEqual(score, 4)
        self.assertTrue(reasons)

    def test_non_finite_patch_age_degrades_to_unknown_not_crash(self):
        # Crafted observations with inf/nan patch cadence must not crash the
        # recon layer (int(round(inf)) -> OverflowError, int(round(nan)) ->
        # ValueError before the guard).
        for bad in (float("inf"), float("nan"), "garbage"):
            obs = dict(HEALTHY_DECOY_OBS, patch_cadence_days=bad)
            decoy = next(c for c in build_candidates(obs) if c.is_decoy)
            self.assertIsNone(decoy.patch_age_days, bad)
            selected, _ = select_target(build_candidates(obs))
            self.assertTrue(selected.is_decoy, bad)
            self.assertNotIn("outdated patch", rank_candidates([decoy])[0][2])


if __name__ == "__main__":
    unittest.main()