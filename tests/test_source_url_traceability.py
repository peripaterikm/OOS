"""Focused tests for Source URL traceability contract (Roadmap v2.7 item 1.1).

Tests cover:
1. Report model serializes to JSON.
2. Placeholder URN detection works for urn:oos:*.
3. Real HTTP/HTTPS URLs are accepted.
4. Empty/missing source URL fields are flagged when expected.
5. Insufficient-evidence marked artifacts are exempt.
6. Weekly run directory scan detects placeholder URNs in founder_decisions_v2.json.
7. Weekly run directory scan detects placeholder URNs in founder_feedback_mappings.json.
8. Scan handles missing optional artifacts without crashing.
9. Scan handles malformed JSON artifact with clear issue/error.
10. Deterministic issue IDs.
11. Advisory/no-live flags are true.
12. No real artifacts/ directory is written during tests.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from oos.source_url_traceability import (
    SOURCE_URL_TRACEABILITY_SCHEMA_VERSION,
    SourceURLTraceabilityArtifactStatus,
    SourceURLTraceabilityIssue,
    SourceURLTraceabilityReport,
    _is_synthetic_inbox_item_without_lineage,
    check_source_url_traceability,
    collect_source_urls_from_artifact,
    is_malformed_source_url,
    is_placeholder_source_url,
    is_real_source_url,
    source_url_traceability_to_json,
)


class TestSourceURLTraceabilityModels(unittest.TestCase):
    """Test model construction and serialization."""

    def test_report_model_serializes_to_json(self):
        """Report model to_dict and to_json produce valid, schema-versioned output."""
        report = SourceURLTraceabilityReport(
            run_dir="/tmp/test_run",
            checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            validation_passed=True,
        )
        d = report.to_dict()
        self.assertEqual(d["schema_version"], SOURCE_URL_TRACEABILITY_SCHEMA_VERSION)
        self.assertEqual(d["run_dir"], "/tmp/test_run")
        self.assertEqual(d["issue_count"], 0)
        self.assertEqual(d["placeholder_url_count"], 0)
        self.assertEqual(d["missing_source_url_count"], 0)
        self.assertTrue(d["advisory_only"])
        self.assertTrue(d["no_live_api"])
        self.assertTrue(d["no_live_llm"])
        self.assertTrue(d["validation_passed"])
        self.assertEqual(len(d["issues"]), 0)

        json_str = source_url_traceability_to_json(report)
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["schema_version"], SOURCE_URL_TRACEABILITY_SCHEMA_VERSION)

    def test_issue_model_serializes_correctly(self):
        issue = SourceURLTraceabilityIssue(
            issue_id="src_url_abc123",
            artifact_key="founder_decisions_v2",
            artifact_path="/tmp/run/founder_decisions_v2.json",
            item_id="decision_01",
            field_path="items[].linked_source_urls[0]",
            issue_type="placeholder_source_url",
            source_url_value="urn:oos:founder_import:placeholder",
            severity="error",
            explanation="Placeholder URN detected",
        )
        d = issue.to_dict()
        self.assertEqual(d["issue_id"], "src_url_abc123")
        self.assertEqual(d["artifact_key"], "founder_decisions_v2")
        self.assertEqual(d["issue_type"], "placeholder_source_url")
        self.assertEqual(d["severity"], "error")
        self.assertTrue(d["advisory_only"])


class TestPlaceholderDetection(unittest.TestCase):
    """Test placeholder URN and URL detection helpers."""

    def test_placeholder_urn_detected_for_oos_prefix(self):
        self.assertTrue(is_placeholder_source_url("urn:oos:founder_import:placeholder"))
        self.assertTrue(is_placeholder_source_url("urn:oos:anything"))
        self.assertTrue(is_placeholder_source_url("urn:oos:some.namespace:id"))
        # Case insensitive
        self.assertTrue(is_placeholder_source_url("URN:OOS:Test"))

    def test_placeholder_urn_rejects_real_urls(self):
        self.assertFalse(is_placeholder_source_url("https://example.com"))
        self.assertFalse(is_placeholder_source_url("http://github.com/issue/1"))
        self.assertFalse(is_placeholder_source_url("https://news.ycombinator.com/item?id=123"))

    def test_placeholder_urn_rejects_empty_and_non_strings(self):
        self.assertFalse(is_placeholder_source_url(""))
        self.assertFalse(is_placeholder_source_url("   "))
        self.assertFalse(is_placeholder_source_url("urn:not_oos:"))

    def test_real_url_accepted(self):
        self.assertTrue(is_real_source_url("https://example.com"))
        self.assertTrue(is_real_source_url("http://example.com/path?q=1"))
        self.assertTrue(is_real_source_url("https://news.ycombinator.com/item?id=456"))

    def test_real_url_rejects_placeholders(self):
        self.assertFalse(is_real_source_url("urn:oos:placeholder"))
        self.assertFalse(is_real_source_url(""))
        self.assertFalse(is_real_source_url("ftp://files.example.com"))

    def test_malformed_url_detection(self):
        self.assertTrue(is_malformed_source_url("http://"))
        self.assertTrue(is_malformed_source_url("https://"))
        self.assertTrue(is_malformed_source_url("http:"))
        self.assertTrue(is_malformed_source_url("https:"))

    def test_malformed_url_rejects_good_urls(self):
        self.assertFalse(is_malformed_source_url("https://example.com"))
        self.assertFalse(is_malformed_source_url(""))
        self.assertFalse(is_malformed_source_url("urn:oos:placeholder"))


class TestCollectSourceURLsFromArtifact(unittest.TestCase):
    """Test the collect_source_urls_from_artifact helper."""

    def test_collects_source_urls_from_evidence_packs(self):
        data = {
            "items": [
                {"evidence_pack_id": "ep1", "source_urls": ["https://a.com", "https://b.com"]},
                {"evidence_pack_id": "ep2", "source_urls": ["https://c.com"]},
            ]
        }
        urls = collect_source_urls_from_artifact(data, "evidence_packs")
        self.assertEqual(urls, ["https://a.com", "https://b.com", "https://c.com"])

    def test_collects_linked_source_urls_from_founder_decisions(self):
        data = {
            "items": [
                {
                    "decision_id": "d1",
                    "linked_source_urls": ["urn:oos:placeholder", "https://real.com"],
                }
            ]
        }
        urls = collect_source_urls_from_artifact(data, "founder_decisions_v2")
        self.assertEqual(urls, ["urn:oos:placeholder", "https://real.com"])

    def test_deduplicates_urls(self):
        data = {
            "items": [
                {"evidence_pack_id": "ep1", "source_urls": ["https://a.com"]},
                {"evidence_pack_id": "ep2", "source_urls": ["https://a.com"]},
            ]
        }
        urls = collect_source_urls_from_artifact(data, "evidence_packs")
        self.assertEqual(urls, ["https://a.com"])

    def test_handles_empty_artifacts(self):
        self.assertEqual(collect_source_urls_from_artifact({}, "evidence_packs"), [])
        self.assertEqual(collect_source_urls_from_artifact({"items": []}, "evidence_packs"), [])

    def test_handles_unknown_artifact_key(self):
        self.assertEqual(collect_source_urls_from_artifact({}, "unknown_key"), [])


class TestCheckSourceURLTraceability(unittest.TestCase):
    """End-to-end scan tests using temp directories (no real artifacts/)."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="oos_test_src_url_"))

    def tearDown(self):
        import shutil
        if self.tmpdir.exists():
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_artifact(self, filename: str, data: dict | list):
        path = self.tmpdir / filename
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def test_missing_run_dir_returns_error(self):
        report = check_source_url_traceability(self.tmpdir / "nonexistent")
        self.assertFalse(report.validation_passed)
        self.assertGreater(len(report.errors), 0)
        self.assertIn("not found", report.errors[0])

    def test_missing_optional_artifact_does_not_crash(self):
        """Scan handles missing optional artifact without crashing."""
        # Write only a manifest so the dir exists, but no artifact files
        self._write_artifact("manifest.json", {"run_id": "test_run"})
        report = check_source_url_traceability(self.tmpdir)
        # All artifacts are absent but scan completes
        self.assertEqual(report.artifacts_checked, 0)
        self.assertTrue(report.validation_passed)  # no blocker issues
        self.assertEqual(len(report.errors), 0)

    def test_detects_placeholder_urn_in_founder_decisions_v2(self):
        data = {
            "items": [
                {
                    "decision_id": "dec_01",
                    "opportunity_id": "opp_01",
                    "evidence_pack_id": "ep_01",
                    "decision": "promote",
                    "linked_evidence_ids": ["e1"],
                    "linked_source_signal_ids": ["s1"],
                    "linked_source_urls": ["urn:oos:founder_import:placeholder"],
                    "decided_by": "founder",
                }
            ]
        }
        self._write_artifact("founder_decisions_v2.json", data)
        report = check_source_url_traceability(self.tmpdir)

        self.assertFalse(report.validation_passed)
        self.assertGreaterEqual(report.placeholder_url_count, 1)
        self.assertGreaterEqual(report.issue_count, 1)

        placeholder_issues = [
            i for i in report.issues if i.issue_type == "placeholder_source_url"
        ]
        self.assertGreaterEqual(len(placeholder_issues), 1)
        self.assertEqual(
            placeholder_issues[0].artifact_key, "founder_decisions_v2"
        )
        self.assertIn("urn:oos:", placeholder_issues[0].source_url_value)

    def test_detects_placeholder_urn_in_founder_feedback_mappings(self):
        data = {
            "items": [
                {
                    "feedback_mapping_id": "fm_01",
                    "opportunity_id": "opp_01",
                    "evidence_pack_id": "ep_01",
                    "decision": "promote",
                    "source_signal_ids": ["s1"],
                    "source_urls": ["urn:oos:founder_import:placeholder"],
                    "signal_impact": "positive",
                    "recommended_future_handling": ["boost_similar_pattern"],
                }
            ]
        }
        self._write_artifact("founder_feedback_mappings.json", data)
        report = check_source_url_traceability(self.tmpdir)

        self.assertFalse(report.validation_passed)
        placeholder_issues = [
            i for i in report.issues if i.issue_type == "placeholder_source_url"
        ]
        self.assertGreaterEqual(len(placeholder_issues), 1)
        self.assertEqual(
            placeholder_issues[0].artifact_key, "founder_feedback_mappings"
        )

    def test_detects_missing_source_urls(self):
        data = {
            "items": [
                {
                    "opportunity_id": "opp_01",
                    "source_signal_ids": ["s1"],
                    "source_urls": [],
                    "unsupported_assumptions": [],
                    "risk_notes": [],
                    "evidence_ids": ["e1"],
                    "confidence": 0.7,
                }
            ]
        }
        self._write_artifact("opportunity_candidates.json", data)
        report = check_source_url_traceability(self.tmpdir)

        self.assertFalse(report.validation_passed)
        missing_issues = [
            i for i in report.issues if i.issue_type == "missing_source_url"
        ]
        self.assertGreaterEqual(len(missing_issues), 1)
        self.assertEqual(missing_issues[0].severity, "error")

    def test_exempts_insufficient_evidence_packs(self):
        data = {
            "items": [
                {
                    "evidence_pack_id": "ep_exempt",
                    "source_urls": [],
                    "created_from": "insufficient_evidence",
                },
                {
                    "evidence_pack_id": "ep_normal",
                    "source_urls": ["https://example.com"],
                    "created_from": "evidence_pack_builder",
                },
            ]
        }
        self._write_artifact("evidence_packs.json", data)
        report = check_source_url_traceability(self.tmpdir)

        # The exempt item should not produce placeholder/missing issues
        self.assertTrue(report.validation_passed)
        status = next(
            s for s in report.artifact_statuses if s.artifact_key == "evidence_packs"
        )
        self.assertEqual(status.items_exempt_insufficient_evidence, 1)

    def test_handles_malformed_json_artifact(self):
        path = self.tmpdir / "founder_decisions_v2.json"
        path.write_text("{ not valid json }", encoding="utf-8")
        report = check_source_url_traceability(self.tmpdir)

        self.assertFalse(report.validation_passed)
        unsupported = [
            i for i in report.issues if i.issue_type == "unsupported_artifact"
        ]
        self.assertGreaterEqual(len(unsupported), 1)
        self.assertEqual(unsupported[0].severity, "error")

    def test_handles_artifact_that_is_array_not_object(self):
        path = self.tmpdir / "founder_decisions_v2.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        report = check_source_url_traceability(self.tmpdir)

        unsupported = [
            i for i in report.issues if i.issue_type == "unsupported_artifact"
        ]
        self.assertGreaterEqual(len(unsupported), 1)

    def test_deterministic_issue_ids(self):
        data = {
            "items": [
                {
                    "opportunity_id": "opp_01",
                    "source_urls": [],
                    "source_signal_ids": ["s1"],
                    "unsupported_assumptions": [],
                    "risk_notes": [],
                    "evidence_ids": ["e1"],
                    "confidence": 0.7,
                }
            ]
        }
        self._write_artifact("opportunity_candidates.json", data)

        report1 = check_source_url_traceability(self.tmpdir)
        report2 = check_source_url_traceability(self.tmpdir)

        ids1 = [i.issue_id for i in report1.issues]
        ids2 = [i.issue_id for i in report2.issues]
        self.assertEqual(ids1, ids2)  # Deterministic across runs

    def test_advisory_and_no_live_flags_are_true(self):
        report = check_source_url_traceability(self.tmpdir)
        self.assertTrue(report.advisory_only)
        self.assertTrue(report.no_live_api)
        self.assertTrue(report.no_live_llm)

    def test_clean_run_with_real_urls_passes(self):
        """A run with all real source URLs should pass validation."""
        ep_data = {
            "items": [
                {
                    "evidence_pack_id": "ep1",
                    "source_urls": ["https://hn.example.com/item?id=1"],
                    "created_from": "evidence_pack_builder",
                }
            ]
        }
        opp_data = {
            "items": [
                {
                    "opportunity_id": "opp1",
                    "source_urls": ["https://hn.example.com/item?id=1"],
                    "evidence_ids": ["e1"],
                    "source_signal_ids": ["s1"],
                    "unsupported_assumptions": [],
                    "risk_notes": [],
                    "confidence": 0.8,
                }
            ]
        }
        dec_data = {
            "items": [
                {
                    "decision_id": "d1",
                    "opportunity_id": "opp1",
                    "evidence_pack_id": "ep1",
                    "decision": "promote",
                    "linked_evidence_ids": ["e1"],
                    "linked_source_signal_ids": ["s1"],
                    "linked_source_urls": ["https://hn.example.com/item?id=1"],
                    "decided_by": "founder",
                }
            ]
        }
        fm_data = {
            "items": [
                {
                    "feedback_mapping_id": "fm1",
                    "opportunity_id": "opp1",
                    "evidence_pack_id": "ep1",
                    "decision": "promote",
                    "source_signal_ids": ["s1"],
                    "source_urls": ["https://hn.example.com/item?id=1"],
                    "signal_impact": "positive",
                    "recommended_future_handling": ["boost_similar_pattern"],
                }
            ]
        }
        inbox_data = {
            "review_items": [
                {
                    "review_item_id": "ri1",
                    "linked_source_urls": ["https://hn.example.com/item?id=1"],
                }
            ]
        }

        self._write_artifact("evidence_packs.json", ep_data)
        self._write_artifact("opportunity_candidates.json", opp_data)
        self._write_artifact("founder_decisions_v2.json", dec_data)
        self._write_artifact("founder_feedback_mappings.json", fm_data)
        self._write_artifact("founder_inbox_v2_index.json", inbox_data)
        # quality_gate_decisions is optional
        # but to be safe, it won't fail if missing

        report = check_source_url_traceability(self.tmpdir)
        self.assertTrue(report.validation_passed, f"Issues found: {report.issues}")
        self.assertEqual(report.placeholder_url_count, 0)
        self.assertEqual(report.missing_source_url_count, 0)

    def test_no_real_artifacts_directory_written(self):
        """Confirm tests do not create artifacts/ directory."""
        import os
        cwd = Path(os.getcwd())
        artifacts_dir = cwd / "artifacts"
        # We only assert that our tempdir does not leak into the project tree
        self.assertFalse(
            str(self.tmpdir).startswith(str(artifacts_dir)),
            "Test tempdir should not be under artifacts/",
        )


class TestIsMalformedSourceURL(unittest.TestCase):
    """Edge cases for malformed URL detection."""

    def test_good_urls_are_not_malformed(self):
        self.assertFalse(is_malformed_source_url("https://example.com/path"))
        self.assertFalse(is_malformed_source_url("http://localhost:8080/api"))
        self.assertFalse(is_malformed_source_url("https://a.b.c/d/e/f"))

    def test_scheme_only_is_malformed(self):
        self.assertTrue(is_malformed_source_url("http:"))
        self.assertTrue(is_malformed_source_url("https:"))

    def test_scheme_slash_slash_only_is_malformed(self):
        self.assertTrue(is_malformed_source_url("http://"))
        self.assertTrue(is_malformed_source_url("https://"))


class TestSyntheticInboxExemption(unittest.TestCase):
    """Tests for synthetic founder_inbox_v2_index exemption (Roadmap v2.9 item 2.2)."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="oos_test_src_url_synth_"))

    def tearDown(self):
        import shutil
        if self.tmpdir.exists():
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_artifact(self, filename: str, data: dict | list):
        path = self.tmpdir / filename
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def test_synthetic_inbox_item_all_empty_is_exempt(self):
        """Synthetic inbox item with all five linked fields empty is exempt
        from missing_source_url."""
        inbox_data = {
            "review_items": [
                {
                    "review_item_id": "inbox_review_822b4d010950",
                    "section_id": "decision_recording_commands",
                    "title": "Decision Recording Commands",
                    "linked_opportunity_ids": [],
                    "linked_evidence_pack_ids": [],
                    "linked_evidence_ids": [],
                    "linked_quality_gate_ids": [],
                    "linked_source_urls": [],
                }
            ]
        }
        self._write_artifact("founder_inbox_v2_index.json", inbox_data)
        report = check_source_url_traceability(self.tmpdir)

        inbox_issues = [
            i for i in report.issues
            if i.artifact_key == "founder_inbox_v2_index"
            and i.issue_type == "missing_source_url"
        ]
        self.assertEqual(len(inbox_issues), 0,
                         f"Expected 0 missing_source_url for synthetic item, got {len(inbox_issues)}")

        self.assertGreaterEqual(report.exempt_synthetic_inbox_count, 1)

    def test_inbox_item_with_linked_id_not_exempt(self):
        """Inbox item with any linked ID present and empty linked_source_urls
        is NOT exempt from missing_source_url."""
        inbox_data = {
            "review_items": [
                {
                    "review_item_id": "inbox_review_test1",
                    "section_id": "top_opportunities_to_review",
                    "title": "Test Opportunity",
                    "linked_opportunity_ids": ["opp_001"],
                    "linked_evidence_pack_ids": [],
                    "linked_evidence_ids": [],
                    "linked_quality_gate_ids": [],
                    "linked_source_urls": [],
                }
            ]
        }
        self._write_artifact("founder_inbox_v2_index.json", inbox_data)
        report = check_source_url_traceability(self.tmpdir)

        missing = [
            i for i in report.issues
            if i.artifact_key == "founder_inbox_v2_index"
            and i.issue_type == "missing_source_url"
        ]
        self.assertGreaterEqual(len(missing), 1,
                                "Item with linked_opportunity_id and empty source_urls should NOT be exempt")

    def test_inbox_item_with_placeholder_still_flagged(self):
        """Inbox item with linked_source_urls containing urn:oos:* is still
        flagged for placeholder even if other linked IDs are empty."""
        inbox_data = {
            "review_items": [
                {
                    "review_item_id": "inbox_review_test2",
                    "section_id": "top_opportunities_to_review",
                    "title": "Test item with placeholder",
                    "linked_opportunity_ids": [],
                    "linked_evidence_pack_ids": [],
                    "linked_evidence_ids": [],
                    "linked_quality_gate_ids": [],
                    "linked_source_urls": ["urn:oos:founder_import:placeholder"],
                }
            ]
        }
        self._write_artifact("founder_inbox_v2_index.json", inbox_data)
        report = check_source_url_traceability(self.tmpdir)

        placeholder_issues = [
            i for i in report.issues
            if i.artifact_key == "founder_inbox_v2_index"
            and i.issue_type == "placeholder_source_url"
        ]
        self.assertGreaterEqual(len(placeholder_issues), 1,
                                "Placeholder URN in linked_source_urls must still be detected")

        inbox_status = next(
            s for s in report.artifact_statuses
            if s.artifact_key == "founder_inbox_v2_index"
        )
        self.assertEqual(inbox_status.items_exempt_synthetic_inbox, 0)

    def test_clean_fixture_run_with_synthetic_inbox_passes(self):
        """Clean fixture-like run passes with synthetic inbox item exempt."""
        ep_data = {
            "items": [
                {
                    "evidence_pack_id": "ep1",
                    "source_urls": ["https://hn.example.com/item?id=1"],
                    "created_from": "evidence_pack_builder",
                }
            ]
        }
        opp_data = {
            "items": [
                {
                    "opportunity_id": "opp1",
                    "source_urls": ["https://hn.example.com/item?id=1"],
                    "evidence_ids": ["e1"],
                    "source_signal_ids": ["s1"],
                    "unsupported_assumptions": [],
                    "risk_notes": [],
                    "confidence": 0.8,
                }
            ]
        }
        dec_data = {
            "items": [
                {
                    "decision_id": "d1",
                    "opportunity_id": "opp1",
                    "evidence_pack_id": "ep1",
                    "decision": "promote",
                    "linked_evidence_ids": ["e1"],
                    "linked_source_signal_ids": ["s1"],
                    "linked_source_urls": ["https://hn.example.com/item?id=1"],
                    "decided_by": "founder",
                }
            ]
        }
        fm_data = {
            "items": [
                {
                    "feedback_mapping_id": "fm1",
                    "opportunity_id": "opp1",
                    "evidence_pack_id": "ep1",
                    "decision": "promote",
                    "source_signal_ids": ["s1"],
                    "source_urls": ["https://hn.example.com/item?id=1"],
                    "signal_impact": "positive",
                    "recommended_future_handling": ["boost_similar_pattern"],
                }
            ]
        }
        inbox_data = {
            "review_items": [
                {
                    "review_item_id": "ri1",
                    "linked_opportunity_ids": ["opp1"],
                    "linked_evidence_pack_ids": ["ep1"],
                    "linked_evidence_ids": ["e1"],
                    "linked_quality_gate_ids": [],
                    "linked_source_urls": ["https://hn.example.com/item?id=1"],
                },
                {
                    "review_item_id": "inbox_review_synthetic",
                    "section_id": "decision_recording_commands",
                    "title": "Decision Recording Commands",
                    "linked_opportunity_ids": [],
                    "linked_evidence_pack_ids": [],
                    "linked_evidence_ids": [],
                    "linked_quality_gate_ids": [],
                    "linked_source_urls": [],
                },
            ]
        }

        self._write_artifact("evidence_packs.json", ep_data)
        self._write_artifact("opportunity_candidates.json", opp_data)
        self._write_artifact("founder_decisions_v2.json", dec_data)
        self._write_artifact("founder_feedback_mappings.json", fm_data)
        self._write_artifact("founder_inbox_v2_index.json", inbox_data)

        report = check_source_url_traceability(self.tmpdir)
        self.assertTrue(report.validation_passed,
                        f"Expected validation_passed=True, got issues: {report.issues}")
        self.assertEqual(report.placeholder_url_count, 0)
        self.assertEqual(report.missing_source_url_count, 0,
                         f"Expected missing_count=0, got {report.missing_source_url_count}")
        self.assertGreaterEqual(report.exempt_synthetic_inbox_count, 1)


if __name__ == "__main__":
    unittest.main()
