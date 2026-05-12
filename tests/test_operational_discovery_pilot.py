from __future__ import annotations

"""Tests for Operational Discovery Pilot Orchestrator (v2.12 item 7).

Covers: preflight/source scope, pipeline execution, traceability,
artifact writing, determinism. No live APIs. unittest convention.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

from oos.operational_discovery_pilot import (
    OperationalDiscoveryPilotInput,
    OperationalDiscoveryPilotResult,
    PilotRunValidationResult,
    _build_run_id,
    _derive_minimal_candidate_signals,
    _is_valid_http_url,
    _is_placeholder_url,
    _validate_source_scope,
    _validate_source_url,
    build_pilot_run_id,
    run_operational_discovery_pilot,
    validate_pilot_run_result,
    write_pilot_run_artifacts,
)
from oos.pain_cluster_dedupe import normalize_evidence_source


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_FIXED_TS = "2026-05-12T10:00:00Z"


def _make_hn_evidence(
    evidence_id: str = "hn_001",
    source_url: str = "https://news.ycombinator.com/item?id=40000001",
    title: str = "Ask HN: What's your biggest pain with CI/CD?",
    body: str = "We spend hours debugging flaky pipelines. It's costing us real money.",
    evidence_kind: str = "pain_signal_candidate",
) -> dict:
    return {
        "evidence_id": evidence_id,
        "source_id": "hacker_news",
        "source_type": "discussion",
        "source_url": source_url,
        "title": title,
        "body": body,
        "evidence_kind": evidence_kind,
        "created_at": "2026-05-10T12:00:00Z",
        "collected_at": "2026-05-12T10:00:00Z",
        "fetched_at": "2026-05-12T10:00:00Z",
        "topic_id": "ci_cd",
        "query_kind": "pilot_fixture",
        "quality_flags": [],
        "raw_metadata": {"target_user": "developer"},
    }


def _make_gh_evidence(
    evidence_id: str = "gh_001",
    source_url: str = "https://github.com/owner/repo/issues/100",
    title: str = "Flaky test runner on Windows",
    body: str = "The test runner fails intermittently on Windows CI. Affects whole team.",
    evidence_kind: str = "bug_report",
) -> dict:
    return {
        "evidence_id": evidence_id,
        "source_id": "github_issues",
        "source_type": "issue_tracker",
        "source_url": source_url,
        "title": title,
        "body": body,
        "evidence_kind": evidence_kind,
        "created_at": "2026-05-09T08:00:00Z",
        "collected_at": "2026-05-12T10:00:00Z",
        "fetched_at": "2026-05-12T10:00:00Z",
        "topic_id": "ci_cd",
        "query_kind": "pilot_fixture",
        "quality_flags": [],
        "raw_metadata": {"repo": "owner/repo", "target_user": "developer"},
    }


# =========================================================================
# Run ID tests
# =========================================================================


class TestBuildRunId(unittest.TestCase):
    def test_format(self):
        run_id = build_pilot_run_id(_FIXED_TS)
        self.assertTrue(run_id.startswith("pilot_run_2026-05-12_"))
        parts = run_id.split("_")
        self.assertEqual(len(parts), 4)  # pilot, run, date, 8char_hex
        self.assertEqual(len(parts[-1]), 8)

    def test_deterministic(self):
        a = build_pilot_run_id(_FIXED_TS)
        b = build_pilot_run_id(_FIXED_TS)
        self.assertEqual(a, b)

    def test_different_timestamps_different_ids(self):
        a = build_pilot_run_id("2026-05-12T10:00:00Z")
        b = build_pilot_run_id("2026-05-13T10:00:00Z")
        self.assertNotEqual(a, b)

    def test_supplied_run_id_preserved(self):
        supplied = "my_custom_run_42"
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence()],
            discovery_run_id=supplied,
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertEqual(result.discovery_run_id, supplied)


# =========================================================================
# URL validation tests
# =========================================================================


class TestUrlValidation(unittest.TestCase):
    def test_http_passes(self):
        self.assertTrue(_is_valid_http_url("https://news.ycombinator.com/item?id=123"))
        self.assertTrue(_is_valid_http_url("http://example.com"))

    def test_ftp_fails(self):
        self.assertFalse(_is_valid_http_url("ftp://files.example.com"))

    def test_github_fallback_fails(self):
        self.assertFalse(_is_valid_http_url("github://owner/repo/issues/1"))

    def test_urn_is_placeholder(self):
        self.assertTrue(_is_placeholder_url("urn:oos:placeholder"))
        self.assertTrue(_is_placeholder_url("URN:example"))

    def test_http_is_not_placeholder(self):
        self.assertFalse(_is_placeholder_url("https://example.com"))

    def test_validate_source_url_clean(self):
        ev = {"evidence_id": "x", "source_url": "https://example.com"}
        self.assertEqual(_validate_source_url(ev), [])

    def test_validate_source_url_missing(self):
        ev = {"evidence_id": "x", "source_url": ""}
        errs = _validate_source_url(ev)
        self.assertEqual(len(errs), 1)
        self.assertIn("missing source_url", errs[0])

    def test_validate_source_url_placeholder(self):
        ev = {"evidence_id": "x", "source_url": "urn:oos:placeholder"}
        errs = _validate_source_url(ev)
        self.assertEqual(len(errs), 1)
        self.assertIn("placeholder", errs[0].lower())

    def test_validate_source_url_github_fallback(self):
        ev = {"evidence_id": "x", "source_url": "github://owner/repo/issues/1"}
        errs = _validate_source_url(ev)
        self.assertEqual(len(errs), 1)
        self.assertIn("github://", errs[0])

    def test_validate_source_url_ftp(self):
        ev = {"evidence_id": "x", "source_url": "ftp://example.com"}
        errs = _validate_source_url(ev)
        self.assertEqual(len(errs), 1)
        self.assertIn("non-http", errs[0])


# =========================================================================
# Source scope / preflight tests
# =========================================================================


class TestSourceScopeValidation(unittest.TestCase):
    def test_hn_accepted(self):
        errors, warnings = _validate_source_scope(
            [_make_hn_evidence()], stretch_allowed=False
        )
        self.assertEqual(len(errors), 0)

    def test_github_accepted(self):
        errors, warnings = _validate_source_scope(
            [_make_gh_evidence()], stretch_allowed=False
        )
        self.assertEqual(len(errors), 0)

    def test_hn_and_github_accepted(self):
        errors, warnings = _validate_source_scope(
            [_make_hn_evidence(), _make_gh_evidence()],
            stretch_allowed=False,
        )
        self.assertEqual(len(errors), 0)

    def test_legacy_hn_normalized(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "hacker_news_algolia"
        ev_norm = normalize_evidence_source(ev)
        errors, warnings = _validate_source_scope([ev_norm], stretch_allowed=False)
        self.assertEqual(len(errors), 0)

    def test_legacy_source_type_normalized(self):
        ev = _make_gh_evidence()
        ev["source_type"] = "github_issues"  # legacy
        ev_norm = normalize_evidence_source(ev)
        errors, warnings = _validate_source_scope([ev_norm], stretch_allowed=False)
        self.assertEqual(len(errors), 0)

    def test_product_hunt_rejected(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "product_hunt"
        errors, warnings = _validate_source_scope([ev])
        self.assertGreaterEqual(len(errors), 1)
        self.assertTrue(any("product_hunt" in e for e in errors))

    def test_pimenov_ai_rejected(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "pimenov_ai"
        errors, warnings = _validate_source_scope([ev])
        self.assertGreaterEqual(len(errors), 1)
        self.assertTrue(any("pimenov_ai" in e for e in errors))

    def test_reddit_rejected(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "reddit"
        errors, warnings = _validate_source_scope([ev])
        self.assertGreaterEqual(len(errors), 1)
        self.assertTrue(any("reddit" in e for e in errors))

    def test_discord_rejected(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "discord"
        errors, warnings = _validate_source_scope([ev])
        self.assertGreaterEqual(len(errors), 1)

    def test_slack_rejected(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "slack"
        errors, warnings = _validate_source_scope([ev])
        self.assertGreaterEqual(len(errors), 1)

    def test_x_twitter_rejected(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "x_twitter"
        errors, warnings = _validate_source_scope([ev])
        self.assertGreaterEqual(len(errors), 1)

    def test_stack_exchange_rejected_by_default(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "stack_exchange"
        errors, warnings = _validate_source_scope([ev], stretch_allowed=False)
        self.assertGreaterEqual(len(errors), 1)
        self.assertTrue(any("stretch" in e.lower() for e in errors))

    def test_stack_exchange_allowed_with_stretch(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "stack_exchange"
        errors, warnings = _validate_source_scope([ev], stretch_allowed=True)
        self.assertEqual(len(errors), 0)

    def test_stack_overflow_rejected_by_default(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "stack_overflow"
        errors, warnings = _validate_source_scope([ev], stretch_allowed=False)
        self.assertGreaterEqual(len(errors), 1)

    def test_stack_overflow_allowed_with_stretch(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "stack_overflow"
        errors, warnings = _validate_source_scope([ev], stretch_allowed=True)
        self.assertEqual(len(errors), 0)

    def test_unknown_source_warns_not_errors(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "some_unknown_source"
        errors, warnings = _validate_source_scope([ev])
        self.assertEqual(len(errors), 0)

    def test_multiple_deferred_sources(self):
        evidence = [
            {"evidence_id": "a", "source_id": "product_hunt", "source_type": "discussion",
             "source_url": "https://example.com"},
            {"evidence_id": "b", "source_id": "reddit", "source_type": "discussion",
             "source_url": "https://example.com"},
        ]
        errors, warnings = _validate_source_scope(evidence)
        self.assertEqual(len(errors), 2)


# =========================================================================
# Pipeline tests — HN only
# =========================================================================


class TestPipelineHNOnly(unittest.TestCase):
    def test_hn_only_fixture(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[
                _make_hn_evidence("hn_001"),
                _make_hn_evidence(
                    "hn_002",
                    source_url="https://news.ycombinator.com/item?id=40000002",
                    title="Ask HN: How do you handle secrets in CI?",
                    body="Managing secrets across environments is painful.",
                ),
            ],
            created_at=_FIXED_TS,
            discovery_run_id="test_hn_only",
        )
        result = run_operational_discovery_pilot(inp)
        self.assertEqual(result.discovery_run_id, "test_hn_only")
        self.assertEqual(result.raw_evidence_count, 2)
        self.assertEqual(result.candidate_signal_count, 2)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

    def test_hn_only_creates_pain_clusters(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[
                _make_hn_evidence("hn_001"),
                _make_hn_evidence(
                    "hn_002",
                    source_url="https://news.ycombinator.com/item?id=40000002",
                ),
            ],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertGreaterEqual(result.pain_cluster_count, 1)
        for pc in result.pain_clusters:
            self.assertIn("cluster_id", pc)
            self.assertIn("pain_pattern", pc)
            self.assertIn("source_evidence_list", pc)
            self.assertIn("scoring", pc)

    def test_hn_only_creates_source_quality_report(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence("hn_001")],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertIsNotNone(result.source_quality_report)
        sqr = result.source_quality_report
        self.assertEqual(sqr["artifact_type"], "source_quality_report")
        self.assertIn("source_metrics", sqr)
        self.assertEqual(sqr["raw_evidence_total"], 1)

    def test_hn_only_creates_founder_review_package(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[
                _make_hn_evidence(
                    "hn_001",
                    body="This CI pipeline is broken and costs us $5000/month.",
                )
            ],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertIsNotNone(result.founder_review_package)
        frp = result.founder_review_package
        self.assertEqual(frp["artifact_type"], "founder_review_package")
        self.assertIn("review_items", frp)


# =========================================================================
# Pipeline tests — GitHub only
# =========================================================================


class TestPipelineGitHubOnly(unittest.TestCase):
    def test_github_only_fixture(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[
                _make_gh_evidence("gh_001"),
                _make_gh_evidence(
                    "gh_002",
                    source_url="https://github.com/owner/repo/issues/200",
                    title="Deployment takes 45 minutes",
                    body="Our deployment pipeline is way too slow.",
                    evidence_kind="performance_pain",
                ),
            ],
            created_at=_FIXED_TS,
            discovery_run_id="test_gh_only",
        )
        result = run_operational_discovery_pilot(inp)
        self.assertEqual(result.discovery_run_id, "test_gh_only")
        self.assertEqual(result.raw_evidence_count, 2)
        self.assertEqual(result.candidate_signal_count, 2)
        self.assertTrue(result.is_valid)

    def test_github_only_creates_pain_clusters(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[
                _make_gh_evidence("gh_001"),
                _make_gh_evidence(
                    "gh_002",
                    source_url="https://github.com/owner/repo/issues/200",
                ),
            ],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertGreaterEqual(result.pain_cluster_count, 1)


# =========================================================================
# Pipeline tests — HN + GitHub
# =========================================================================


class TestPipelineHNPlusGitHub(unittest.TestCase):
    def test_combined_fixture(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence("hn_001"), _make_gh_evidence("gh_001")],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertEqual(result.raw_evidence_count, 2)
        self.assertEqual(result.candidate_signal_count, 2)
        self.assertTrue(result.is_valid)
        sqr = result.source_quality_report
        self.assertIsNotNone(sqr)
        source_ids = [m["source_id"] for m in sqr.get("source_metrics", [])]
        self.assertIn("hacker_news", source_ids)
        self.assertIn("github_issues", source_ids)

    def test_validation_summary_is_valid(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence("hn_001"), _make_gh_evidence("gh_001")],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        vs = result.validation_summary
        self.assertTrue(vs["is_valid"])
        self.assertTrue(vs["preflight_passed"])

    def test_candidate_signals_supplied(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence("hn_001")],
            candidate_signals=[
                {
                    "signal_id": "cs_manual_001",
                    "evidence_id": "hn_001",
                    "source_id": "hacker_news",
                    "source_type": "discussion",
                    "source_url": "https://news.ycombinator.com/item?id=40000001",
                    "topic_id": "ci_cd",
                    "query_kind": "pilot_fixture",
                    "signal_type": "pain_signal",
                    "pain_summary": "Flaky CI/CD pipelines cause developer pain",
                    "target_user": "developer",
                    "current_workaround": "Re-running failed jobs",
                    "buying_intent_hint": "",
                    "urgency_hint": "",
                    "confidence": 0.8,
                    "measurement_methods": {},
                    "extraction_mode": "manual",
                    "classification": "pain_signal_candidate",
                    "classification_confidence": 0.8,
                    "traceability": {"source_url": "https://news.ycombinator.com/item?id=40000001"},
                }
            ],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertEqual(result.candidate_signal_count, 1)
        self.assertEqual(result.candidate_signals[0]["signal_id"], "cs_manual_001")

    def test_empty_input(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[], created_at=_FIXED_TS
        )
        result = run_operational_discovery_pilot(inp)
        self.assertEqual(result.raw_evidence_count, 0)
        self.assertEqual(result.candidate_signal_count, 0)
        self.assertEqual(result.pain_cluster_count, 0)
        self.assertIsNotNone(result.source_quality_report)
        self.assertIsNotNone(result.founder_review_package)

    def test_founder_review_package_includes_items(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[
                _make_hn_evidence(
                    "hn_001",
                    body="This is costing us thousands per month in lost productivity.",
                ),
            ],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        frp = result.founder_review_package
        self.assertIsNotNone(frp)
        if result.pain_cluster_count > 0:
            self.assertGreater(frp.get("total_review_items", 0), 0)


# =========================================================================
# Traceability tests
# =========================================================================


class TestTraceability(unittest.TestCase):
    def test_missing_source_url_fails_validation(self):
        ev = _make_hn_evidence("hn_bad")
        ev["source_url"] = ""
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[ev], created_at=_FIXED_TS
        )
        result = run_operational_discovery_pilot(inp)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("missing source_url" in e.lower() for e in result.errors))

    def test_urn_placeholder_fails(self):
        ev = _make_hn_evidence("hn_bad")
        ev["source_url"] = "urn:oos:placeholder_123"
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[ev], created_at=_FIXED_TS
        )
        result = run_operational_discovery_pilot(inp)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("placeholder" in e.lower() for e in result.errors))

    def test_github_fallback_url_fails(self):
        ev = _make_gh_evidence("gh_bad")
        ev["source_url"] = "github://owner/repo/issues/1"
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[ev], created_at=_FIXED_TS
        )
        result = run_operational_discovery_pilot(inp)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("github://" in e for e in result.errors))

    def test_ftp_url_fails(self):
        ev = _make_hn_evidence("hn_bad")
        ev["source_url"] = "ftp://files.example.com/data"
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[ev], created_at=_FIXED_TS
        )
        result = run_operational_discovery_pilot(inp)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("non-http" in e.lower() for e in result.errors))

    def test_clean_urls_pass(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence("hn_001"), _make_gh_evidence("gh_001")],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertTrue(result.is_valid)

    def test_good_url_with_https_passes(self):
        ev = _make_hn_evidence("hn_ok")
        ev["source_url"] = "https://news.ycombinator.com/item?id=123456"
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[ev], created_at=_FIXED_TS
        )
        result = run_operational_discovery_pilot(inp)
        self.assertTrue(result.is_valid)

    def test_traceability_errors_in_validation_summary(self):
        ev = _make_hn_evidence("hn_bad")
        ev["source_url"] = ""
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[ev], created_at=_FIXED_TS
        )
        result = run_operational_discovery_pilot(inp)
        vs = result.validation_summary
        self.assertGreaterEqual(len(vs["url_validation_errors"]), 1)


# =========================================================================
# Derivation tests
# =========================================================================


class TestDeriveCandidateSignals(unittest.TestCase):
    def test_derives_from_hn_evidence(self):
        ev = _make_hn_evidence()
        candidates = _derive_minimal_candidate_signals([ev], _FIXED_TS)
        self.assertEqual(len(candidates), 1)
        cs = candidates[0]
        self.assertEqual(cs["source_id"], "hacker_news")
        self.assertEqual(cs["source_type"], "discussion")
        self.assertIn("_derived", cs)
        self.assertTrue(cs["_derived"])

    def test_derives_from_github_evidence(self):
        ev = _make_gh_evidence()
        candidates = _derive_minimal_candidate_signals([ev], _FIXED_TS)
        self.assertEqual(len(candidates), 1)
        cs = candidates[0]
        self.assertEqual(cs["source_id"], "github_issues")
        self.assertEqual(cs["source_type"], "issue_tracker")

    def test_derives_signal_type_from_evidence_kind(self):
        ev = _make_hn_evidence(evidence_kind="bug_report")
        candidates = _derive_minimal_candidate_signals([ev])
        self.assertEqual(candidates[0]["signal_type"], "pain_signal")

    def test_derives_workaround_signal(self):
        ev = _make_hn_evidence(evidence_kind="workaround")
        candidates = _derive_minimal_candidate_signals([ev])
        self.assertEqual(candidates[0]["signal_type"], "workaround")

    def test_derived_signals_have_unique_ids(self):
        ev1 = _make_hn_evidence("hn_001")
        ev2 = _make_hn_evidence("hn_002")
        candidates = _derive_minimal_candidate_signals([ev1, ev2], _FIXED_TS)
        self.assertEqual(len(candidates), 2)
        self.assertNotEqual(candidates[0]["signal_id"], candidates[1]["signal_id"])

    def test_empty_evidence_returns_empty(self):
        candidates = _derive_minimal_candidate_signals([])
        self.assertEqual(candidates, [])

    def test_inherits_source_url(self):
        ev = _make_hn_evidence(source_url="https://news.ycombinator.com/item?id=42")
        candidates = _derive_minimal_candidate_signals([ev])
        self.assertEqual(candidates[0]["source_url"], "https://news.ycombinator.com/item?id=42")


# =========================================================================
# Artifact writing tests
# =========================================================================


class TestArtifactWriting(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="oos_pilot_test_")

    def tearDown(self):
        if os.path.isdir(self._tmpdir):
            shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_no_output_dir_no_writes(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence()],
            created_at=_FIXED_TS,
            output_dir=None,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertEqual(result.artifact_paths, {})

    def test_output_dir_writes_json_artifacts(self):
        output_dir = os.path.join(self._tmpdir, "pilot_output")
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence()],
            created_at=_FIXED_TS,
            output_dir=output_dir,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertGreater(len(result.artifact_paths), 0)

        run_dir = Path(output_dir) / result.discovery_run_id
        self.assertTrue(run_dir.is_dir())

        required_files = [
            "raw_evidence.json",
            "candidate_signals.json",
            "pain_clusters.json",
            "source_quality_report.json",
            "source_quality_report.md",
            "founder_review_package.json",
            "founder_review_package.md",
            "validation_summary.json",
            "pilot_run_manifest.json",
        ]
        for fname in required_files:
            fpath = run_dir / fname
            self.assertTrue(fpath.exists(), f"Missing required artifact: {fname}")

    def test_markdown_artifacts_exist(self):
        output_dir = os.path.join(self._tmpdir, "pilot_output_md")
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence()],
            created_at=_FIXED_TS,
            output_dir=output_dir,
        )
        result = run_operational_discovery_pilot(inp)
        run_dir = Path(output_dir) / result.discovery_run_id

        sqr_md = run_dir / "source_quality_report.md"
        frp_md = run_dir / "founder_review_package.md"
        self.assertTrue(sqr_md.exists())
        self.assertTrue(frp_md.exists())

        sqr_content = sqr_md.read_text(encoding="utf-8")
        self.assertIn("# Source Quality Report", sqr_content)
        frp_content = frp_md.read_text(encoding="utf-8")
        self.assertIn("# Founder Review Package", frp_content)

    def test_manifest_includes_artifact_paths(self):
        output_dir = os.path.join(self._tmpdir, "pilot_output_manifest")
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence()],
            created_at=_FIXED_TS,
            output_dir=output_dir,
        )
        result = run_operational_discovery_pilot(inp)
        run_dir = Path(output_dir) / result.discovery_run_id
        manifest_path = run_dir / "pilot_run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertIn("artifact_paths", manifest)
        self.assertGreater(len(manifest["artifact_paths"]), 0)
        self.assertTrue(manifest["is_valid"])

    def test_json_roundtrip_readable(self):
        output_dir = os.path.join(self._tmpdir, "pilot_output_roundtrip")
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence(), _make_gh_evidence()],
            created_at=_FIXED_TS,
            output_dir=output_dir,
        )
        result = run_operational_discovery_pilot(inp)
        run_dir = Path(output_dir) / result.discovery_run_id

        for fname in [
            "raw_evidence.json", "candidate_signals.json", "pain_clusters.json",
            "source_quality_report.json", "founder_review_package.json",
            "validation_summary.json", "pilot_run_manifest.json",
        ]:
            fpath = run_dir / fname
            data = json.loads(fpath.read_text(encoding="utf-8"))
            self.assertIsInstance(data, (dict, list))

    def test_opportunity_candidates_written_if_supplied(self):
        output_dir = os.path.join(self._tmpdir, "pilot_output_oc")
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence()],
            opportunity_candidates=[
                {
                    "opportunity_id": "oppc_abcd1234",
                    "source_pain_cluster_id": "pc_0000000000000001",
                    "actor": "developer",
                    "problem_statement": "Flaky CI pipelines waste developer time",
                    "evidence_summary": "Evidence from HN",
                    "source_evidence_links": [],
                    "score": 0.75,
                    "uncertainty": "moderate",
                    "suggested_validation_action": "interview",
                    "founder_review_status": "pending_review",
                }
            ],
            created_at=_FIXED_TS,
            output_dir=output_dir,
        )
        result = run_operational_discovery_pilot(inp)
        run_dir = Path(output_dir) / result.discovery_run_id
        oc_path = run_dir / "opportunity_candidates.json"
        self.assertTrue(oc_path.exists())
        oc_data = json.loads(oc_path.read_text(encoding="utf-8"))
        self.assertEqual(len(oc_data), 1)
        self.assertEqual(oc_data[0]["opportunity_id"], "oppc_abcd1234")

    def test_duplicates_written_if_present(self):
        ev1 = _make_hn_evidence("hn_dup")
        ev2 = _make_hn_evidence("hn_dup")
        ev2["source_url"] = "https://news.ycombinator.com/item?id=40000003"

        output_dir = os.path.join(self._tmpdir, "pilot_output_dup")
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[ev1, ev2],
            created_at=_FIXED_TS,
            output_dir=output_dir,
        )
        result = run_operational_discovery_pilot(inp)
        if result.duplicates:
            run_dir = Path(output_dir) / result.discovery_run_id
            dup_path = run_dir / "duplicates.json"
            self.assertTrue(dup_path.exists())

    def test_write_pilot_run_artifacts_function(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence()],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertEqual(result.artifact_paths, {})

        output_dir = os.path.join(self._tmpdir, "pilot_output_separate")
        paths = write_pilot_run_artifacts(result, output_dir)
        self.assertGreater(len(paths), 0)

        run_dir = Path(output_dir) / result.discovery_run_id
        self.assertTrue(run_dir.is_dir())
        self.assertTrue((run_dir / "raw_evidence.json").exists())


# =========================================================================
# Determinism tests
# =========================================================================


class TestDeterminism(unittest.TestCase):
    def test_same_input_same_output(self):
        evidence = [_make_hn_evidence(), _make_gh_evidence()]
        rid = "deterministic_test_run"

        a = run_operational_discovery_pilot(
            OperationalDiscoveryPilotInput(
                raw_evidence=evidence, created_at=_FIXED_TS, discovery_run_id=rid
            )
        )
        b = run_operational_discovery_pilot(
            OperationalDiscoveryPilotInput(
                raw_evidence=evidence, created_at=_FIXED_TS, discovery_run_id=rid
            )
        )
        self.assertEqual(a.discovery_run_id, b.discovery_run_id)
        self.assertEqual(a.raw_evidence_count, b.raw_evidence_count)
        self.assertEqual(a.candidate_signal_count, b.candidate_signal_count)
        self.assertEqual(a.pain_cluster_count, b.pain_cluster_count)
        self.assertEqual(a.is_valid, b.is_valid)
        self.assertEqual(a.errors, b.errors)

    def test_stable_run_id(self):
        a = build_pilot_run_id(_FIXED_TS)
        b = build_pilot_run_id(_FIXED_TS)
        self.assertEqual(a, b)

    def test_created_at_injection(self):
        ts = "2026-01-15T12:00:00Z"
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence()], created_at=ts
        )
        result = run_operational_discovery_pilot(inp)
        self.assertEqual(result.created_at, ts)

    def test_output_json_deterministic(self):
        output_dir = os.path.join(tempfile.mkdtemp(prefix="oos_det_"), "out")
        evidence = [_make_hn_evidence()]

        inp = OperationalDiscoveryPilotInput(
            raw_evidence=evidence,
            created_at=_FIXED_TS,
            output_dir=output_dir,
        )
        result1 = run_operational_discovery_pilot(inp)

        shutil.rmtree(output_dir, ignore_errors=True)
        result2 = run_operational_discovery_pilot(inp)

        self.assertEqual(result1.discovery_run_id, result2.discovery_run_id)
        self.assertEqual(result1.pain_cluster_count, result2.pain_cluster_count)


# =========================================================================
# No-live-API / constraint tests
# =========================================================================


class TestNoLiveAPI(unittest.TestCase):
    def test_no_source_collector_calls(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence()],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertTrue(result.is_valid)

    def test_no_deferred_source_usage(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[
                {
                    "evidence_id": "bad_001",
                    "source_id": "product_hunt",
                    "source_type": "discussion",
                    "source_url": "https://producthunt.com/posts/123",
                    "title": "Test",
                    "body": "Test",
                }
            ],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("product_hunt" in e for e in result.errors))

    def test_no_founder_decision_mutation(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence()],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        frp = result.founder_review_package
        if frp and frp.get("review_items"):
            for item in frp["review_items"]:
                self.assertEqual(item.get("founder_final_decision", ""), "")


# =========================================================================
# validate_pilot_run_result tests
# =========================================================================


class TestValidatePilotRunResult(unittest.TestCase):
    def test_valid_result_validates(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence()],
            created_at=_FIXED_TS,
        )
        result = run_operational_discovery_pilot(inp)
        vr = validate_pilot_run_result(result)
        self.assertTrue(vr.is_valid)

    def test_invalid_result_fails_validation(self):
        ev = _make_hn_evidence("bad")
        ev["source_url"] = ""
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[ev], created_at=_FIXED_TS
        )
        result = run_operational_discovery_pilot(inp)
        vr = validate_pilot_run_result(result)
        self.assertFalse(vr.is_valid)


# =========================================================================
# Edge cases
# =========================================================================


class TestEdgeCases(unittest.TestCase):
    def test_single_evidence_with_many_quality_flags(self):
        ev = _make_hn_evidence()
        ev["quality_flags"] = ["low_text_context", "suspected_self_promo", "launch_hype"]
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[ev], created_at=_FIXED_TS
        )
        result = run_operational_discovery_pilot(inp)
        self.assertIsNotNone(result)

    def test_very_long_body(self):
        ev = _make_hn_evidence()
        ev["body"] = "x" * 10000
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[ev], created_at=_FIXED_TS
        )
        result = run_operational_discovery_pilot(inp)
        self.assertIsNotNone(result)

    def test_non_ascii_content(self):
        ev = _make_hn_evidence()
        ev["body"] = "Developpeurs francais ne peuvent pas deployer - c'est frustrant!"
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[ev], created_at=_FIXED_TS
        )
        result = run_operational_discovery_pilot(inp)
        self.assertIsNotNone(result)
        # UTF-8 content should be preserved
        found = False
        for r in result.raw_evidence:
            if "francais" in str(r.get("body", "")):
                found = True
                break
        self.assertTrue(found)

    def test_max_review_items_respected(self):
        evidence = []
        for i in range(20):
            evidence.append(_make_hn_evidence(
                f"hn_{i:03d}",
                source_url=f"https://news.ycombinator.com/item?id={40000000 + i}",
            ))
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=evidence,
            created_at=_FIXED_TS,
            max_review_items=5,
        )
        result = run_operational_discovery_pilot(inp)
        frp = result.founder_review_package
        if frp:
            self.assertLessEqual(frp.get("total_review_items", 0), 5)

    def test_stretch_allowed_input(self):
        ev = _make_hn_evidence()
        ev["source_id"] = "stack_exchange"
        ev["source_url"] = "https://stackoverflow.com/questions/123/test"
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[ev],
            created_at=_FIXED_TS,
            stretch_allowed=True,
        )
        result = run_operational_discovery_pilot(inp)
        self.assertTrue(result.validation_summary["preflight_passed"])
        self.assertTrue(result.is_valid)

    def test_source_local_summaries_passed_through(self):
        inp = OperationalDiscoveryPilotInput(
            raw_evidence=[_make_hn_evidence()],
            created_at=_FIXED_TS,
            source_local_summaries={
                "hacker_news": {
                    "records_seen": 50,
                    "records_emitted": 45,
                    "records_rejected": 5,
                }
            },
        )
        result = run_operational_discovery_pilot(inp)
        self.assertIsNotNone(result.source_quality_report)
        sqr = result.source_quality_report
        hn_metric = None
        for m in sqr.get("source_metrics", []):
            if m["source_id"] == "hacker_news":
                hn_metric = m
                break
        self.assertIsNotNone(hn_metric)
        self.assertEqual(hn_metric["records_seen"], 50)
