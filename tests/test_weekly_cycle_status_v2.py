"""Tests for the weekly cycle status command (Roadmap v2.6 item 6.1).

All tests use temp directories — no real artifacts/ are written.
No live APIs, no live LLMs, no portfolio mutations.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

from oos.weekly_cycle_status import (
    WeeklyCycleStatus,
    WeeklyCycleArtifactStatus,
    build_weekly_cycle_status,
    render_weekly_cycle_status_markdown,
    weekly_cycle_status_to_json,
)
from oos.weekly_cycle_builder import build_weekly_cycle
from oos.weekly_run_manifest import (
    canonical_artifact_paths,
    canonical_artifact_schema_versions,
)


# ---------------------------------------------------------------------------
# Temp project root helper
# ---------------------------------------------------------------------------


def _temp_project_root(test_case: unittest.TestCase) -> Path:
    tmpdir = tempfile.TemporaryDirectory(prefix="oos_test_wcs_")
    test_case.addCleanup(tmpdir.cleanup)
    root = Path(tmpdir.name)
    (root / "artifacts" / "weekly_runs").mkdir(parents=True, exist_ok=True)
    return root


# ---------------------------------------------------------------------------
# Minimal mock weekly run (like test_founder_decision_import_v2)
# ---------------------------------------------------------------------------


def _build_mock_weekly_run(
    project_root: Path,
    run_id: str,
    *,
    with_inbox: bool = True,
    with_decisions: bool = False,
    decision_count: int = 0,
    inbox_review_items: int = 3,
    feedback_count: int = 0,
    parking_lot_count: int = 0,
    next_best_action_count: int = 2,
    omit_artifacts: list[str] | None = None,
    corrupt_artifact: str | None = None,
) -> Path:
    """Build a minimal mock weekly run directory for testing.

    Returns the run directory path.
    """
    run_dir = project_root / "artifacts" / "weekly_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    omit = set(omit_artifacts or [])

    paths = canonical_artifact_paths()
    versions = canonical_artifact_schema_versions()

    # empty states
    empty_states: dict[str, bool] = {k: True for k in paths}
    empty_states["manifest"] = False
    empty_states["weekly_opportunity_review"] = False
    empty_states["run_report"] = False
    empty_states["founder_inbox_v2_index"] = not with_inbox
    empty_states["founder_inbox_v2_md"] = not with_inbox
    empty_states["run_report_md"] = False
    empty_states["evidence_packs"] = False
    empty_states["opportunity_candidates"] = False
    empty_states["quality_gate_decisions"] = False
    empty_states["next_best_actions"] = next_best_action_count == 0
    empty_states["founder_decisions_v2"] = not with_decisions
    empty_states["founder_feedback_mappings"] = feedback_count == 0
    empty_states["founder_preference_profile"] = True  # default empty
    empty_states["parking_lot_records"] = parking_lot_count == 0

    now = datetime.now(timezone.utc).isoformat()

    # manifest.json
    if "manifest" not in omit:
        manifest = {
            "run_id": run_id,
            "created_at": now,
            "schema_version": "weekly_run_manifest.v1",
            "artifact_paths": dict(paths),
            "artifact_schema_versions": dict(versions),
            "empty_states": dict(empty_states),
            "advisory_only": True,
            "no_live_api": True,
            "no_live_llm": True,
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # evidence_packs.json
    if "evidence_packs" not in omit:
        (run_dir / "evidence_packs.json").write_text(
            json.dumps({"items": [{"id": f"ep_{i}"} for i in range(2)], "schema_version": "evidence_pack.v1", "empty": False}, indent=2),
            encoding="utf-8",
        )

    # opportunity_candidates.json
    if "opportunity_candidates" not in omit:
        (run_dir / "opportunity_candidates.json").write_text(
            json.dumps({"items": [{"id": f"opp_{i}"} for i in range(2)], "schema_version": "opportunity_sketch.v1", "empty": False}, indent=2),
            encoding="utf-8",
        )

    # quality_gate_decisions.json
    if "quality_gate_decisions" not in omit:
        (run_dir / "quality_gate_decisions.json").write_text(
            json.dumps({"items": [{"id": f"qg_{i}"} for i in range(2)], "schema_version": "opportunity_quality_gate.v1", "empty": False}, indent=2),
            encoding="utf-8",
        )

    # founder_decisions_v2.json
    if "founder_decisions_v2" not in omit:
        if corrupt_artifact == "founder_decisions_v2":
            (run_dir / "founder_decisions_v2.json").write_text("not valid json {{", encoding="utf-8")
        else:
            decisions = [{"decision_id": f"fd_{i}"} for i in range(decision_count)] if with_decisions else []
            (run_dir / "founder_decisions_v2.json").write_text(
                json.dumps({"items": decisions, "schema_version": "founder_decision_v2.v1", "empty": len(decisions) == 0}, indent=2),
                encoding="utf-8",
            )

    # founder_feedback_mappings.json
    if "founder_feedback_mappings" not in omit:
        mappings = [{"mapping_id": f"fm_{i}"} for i in range(feedback_count)]
        (run_dir / "founder_feedback_mappings.json").write_text(
            json.dumps({"items": mappings, "schema_version": "founder_feedback_mapping.v1", "empty": len(mappings) == 0}, indent=2),
            encoding="utf-8",
        )

    # founder_preference_profile.json
    if "founder_preference_profile" not in omit:
        (run_dir / "founder_preference_profile.json").write_text(
            json.dumps({
                "profile_id": "test_profile",
                "preferred_pain_types": [],
                "rejected_patterns": [],
                "promoted_patterns": [],
                "recurring_kill_reasons": [],
                "areas_needing_more_evidence": [],
                "source_decision_ids": [],
                "source_feedback_mapping_ids": [],
                "generated_at": now,
                "decision_count": decision_count,
                "promote_count": 0,
                "park_count": 0,
                "kill_count": 0,
                "revisit_count": 0,
                "needs_more_evidence_count": 0,
                "schema_version": "founder_preference_profile.v1",
                "ml_training_claimed": False,
                "autonomous_decisions_made": False,
                "empty": decision_count == 0,
            }, indent=2),
            encoding="utf-8",
        )

    # weekly_opportunity_review.json
    if "weekly_opportunity_review" not in omit:
        (run_dir / "weekly_opportunity_review.json").write_text(
            json.dumps({"package_id": "test", "schema_version": "weekly_opportunity_review.v1", "sections": []}, indent=2),
            encoding="utf-8",
        )

    # next_best_actions.json
    if "next_best_actions" not in omit:
        actions = [{"action_id": f"nba_{i}"} for i in range(next_best_action_count)]
        (run_dir / "next_best_actions.json").write_text(
            json.dumps({"items": actions, "schema_version": "founder_action.v1", "empty": len(actions) == 0}, indent=2),
            encoding="utf-8",
        )

    # parking_lot_records.json
    if "parking_lot_records" not in omit:
        pl_records = [{"record_id": f"pl_{i}"} for i in range(parking_lot_count)]
        (run_dir / "parking_lot_records.json").write_text(
            json.dumps({"items": pl_records, "schema_version": "parking_lot.v1", "empty": len(pl_records) == 0}, indent=2),
            encoding="utf-8",
        )

    # run_report.json
    if "run_report" not in omit:
        (run_dir / "run_report.json").write_text(
            json.dumps({"run_id": run_id, "schema_version": "weekly_run_report.v1", "placeholder": True}, indent=2),
            encoding="utf-8",
        )

    # founder_inbox_v2_index.json
    if "founder_inbox_v2_index" not in omit:
        items = [
            {
                "review_item_id": f"ri_{i}",
                "section_id": "top_opportunities_to_review",
                "linked_source_urls": [f"https://example.com/ri_{i}"],
                "linked_opportunity_ids": [f"opp_ri_{i}"],
                "linked_evidence_pack_ids": [f"ep_ri_{i}"],
                "linked_evidence_ids": [f"ev_ri_{i}"],
                "linked_quality_gate_ids": [f"qg_ri_{i}"],
                "decision_options": ["PROMOTE", "PARK", "KILL", "NEEDS_MORE_EVIDENCE", "REVISIT_LATER"],
            }
            for i in range(inbox_review_items)
        ]
        (run_dir / "founder_inbox_v2_index.json").write_text(
            json.dumps({"review_items": items, "schema_version": "founder_inbox_v2_index.v1"}, indent=2),
            encoding="utf-8",
        )

    # founder_inbox_v2.md
    if "founder_inbox_v2_md" not in omit and with_inbox:
        (run_dir / "founder_inbox_v2.md").write_text("# Founder Inbox v2\n\nTest inbox.\n", encoding="utf-8")

    # run_report.md
    if "run_report_md" not in omit:
        (run_dir / "run_report.md").write_text("# Weekly Run Report\n\nTest report.\n", encoding="utf-8")

    return run_dir


# ---------------------------------------------------------------------------
# Tests: Model serialization
# ---------------------------------------------------------------------------


class WeeklyCycleStatusModelTests(unittest.TestCase):
    """Test WeeklyCycleStatus model serialization."""

    def test_status_model_serializes_to_json(self):
        """Status model serializes to valid JSON."""
        status = WeeklyCycleStatus(
            run_id="weekly_run_2026_01_01_abc123",
            run_dir="/tmp/test",
            manifest_path="/tmp/test/manifest.json",
            manifest_valid=True,
            expected_artifact_count=14,
            present_artifact_count=14,
            founder_inbox_present=True,
            founder_inbox_review_item_count=5,
            founder_decisions_imported=True,
            founder_decision_count=3,
            feedback_mapping_count=3,
            preference_profile_present=True,
            parking_lot_record_count=2,
            next_best_action_count=4,
            run_report_present=True,
            validation_passed=True,
        )

        json_str = weekly_cycle_status_to_json(status)
        data = json.loads(json_str)

        self.assertEqual(data["run_id"], "weekly_run_2026_01_01_abc123")
        self.assertTrue(data["manifest_valid"])
        self.assertEqual(data["expected_artifact_count"], 14)
        self.assertEqual(data["present_artifact_count"], 14)
        self.assertTrue(data["validation_passed"])

    def test_artifact_status_model_serializes(self):
        """WeeklyCycleArtifactStatus serializes correctly."""
        art = WeeklyCycleArtifactStatus(
            artifact_key="evidence_packs",
            relative_path="evidence_packs.json",
            exists=True,
            is_empty_state=False,
            schema_version="evidence_pack.v1",
            item_count=5,
            warnings=["Low confidence"],
            errors=[],
        )
        d = art.to_dict()
        self.assertEqual(d["artifact_key"], "evidence_packs")
        self.assertEqual(d["item_count"], 5)
        self.assertEqual(d["warnings"], ["Low confidence"])

    def test_status_markdown_render_contains_all_sections(self):
        """Markdown render includes all 10 sections."""
        status = WeeklyCycleStatus(
            run_id="weekly_run_2026_01_01_abc123",
            run_dir="/tmp/test",
            manifest_path="/tmp/test/manifest.json",
            manifest_valid=True,
            expected_artifact_count=14,
            present_artifact_count=14,
            validation_passed=True,
            recommended_next_step="All is well.",
        )
        md = render_weekly_cycle_status_markdown(status)

        self.assertIn("## 1. Run Identity", md)
        self.assertIn("## 2. Manifest Status", md)
        self.assertIn("## 3. Artifact Completeness", md)
        self.assertIn("## 4. Pipeline Artifact Counts", md)
        self.assertIn("## 5. Founder Inbox Status", md)
        self.assertIn("## 6. Founder Decision Import Status", md)
        self.assertIn("## 7. Feedback / Profile / Parking Lot Status", md)
        self.assertIn("## 8. Warnings / Errors", md)
        self.assertIn("## 9. Recommended Next Step", md)
        self.assertIn("## 11. Artifact Paths", md)
        self.assertIn("## Safety", md)
        self.assertIn("All is well.", md)


# ---------------------------------------------------------------------------
# Tests: Valid weekly run from mock
# ---------------------------------------------------------------------------


class WeeklyCycleStatusMockRunTests(unittest.TestCase):
    """Test status reading from mock weekly runs."""

    def test_status_reads_valid_run_with_all_artifacts(self):
        """Status reads a valid mock weekly run with all artifacts present."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_01_01_abc123"
        _build_mock_weekly_run(root, run_id)

        status = build_weekly_cycle_status(root, run_id=run_id)

        self.assertTrue(status.manifest_valid)
        self.assertEqual(status.run_id, run_id)
        self.assertEqual(status.expected_artifact_count, 14)
        self.assertEqual(status.present_artifact_count, 14)
        self.assertEqual(len(status.missing_artifact_keys), 0)
        self.assertTrue(status.founder_inbox_present)
        self.assertEqual(status.founder_inbox_review_item_count, 3)
        self.assertFalse(status.founder_decisions_imported)
        self.assertEqual(status.founder_decision_count, 0)
        self.assertEqual(status.next_best_action_count, 2)
        self.assertTrue(status.run_report_present)
        self.assertTrue(status.preference_profile_present)
        self.assertTrue(status.validation_passed)

    def test_status_reports_all_artifact_statuses(self):
        """Status includes per-artifact status entries for all canonical keys."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_01_01_abc123"
        _build_mock_weekly_run(root, run_id)

        status = build_weekly_cycle_status(root, run_id=run_id)

        self.assertEqual(len(status.artifact_statuses), 14)
        for art in status.artifact_statuses:
            self.assertTrue(art.exists, f"Artifact {art.artifact_key} should exist")
            self.assertIn(art.artifact_key, canonical_artifact_paths())

    def test_status_reports_founder_inbox_present_and_review_count(self):
        """Status reports inbox present and review item count."""
        root = _temp_project_root(self)
        run_id = "weekly_run_inbox_test"
        _build_mock_weekly_run(root, run_id, with_inbox=True, inbox_review_items=7)

        status = build_weekly_cycle_status(root, run_id=run_id)
        self.assertTrue(status.founder_inbox_present)
        self.assertEqual(status.founder_inbox_review_item_count, 7)

    def test_status_reports_no_decisions_before_import(self):
        """Status reports no founder decisions imported before import."""
        root = _temp_project_root(self)
        run_id = "weekly_run_no_decisions"
        _build_mock_weekly_run(root, run_id, with_decisions=False)

        status = build_weekly_cycle_status(root, run_id=run_id)
        self.assertFalse(status.founder_decisions_imported)
        self.assertEqual(status.founder_decision_count, 0)
        # Recommended next step should point to founder inbox and decision import
        self.assertIn("review founder_inbox_v2.md", status.recommended_next_step.lower())

    def test_status_reports_decisions_imported_after_import(self):
        """Status reports decisions imported after import."""
        root = _temp_project_root(self)
        run_id = "weekly_run_imported"
        _build_mock_weekly_run(
            root, run_id,
            with_decisions=True,
            decision_count=5,
            feedback_count=5,
            parking_lot_count=2,
        )

        status = build_weekly_cycle_status(root, run_id=run_id)
        self.assertTrue(status.founder_decisions_imported)
        self.assertEqual(status.founder_decision_count, 5)
        self.assertEqual(status.feedback_mapping_count, 5)
        self.assertEqual(status.parking_lot_record_count, 2)

    def test_status_reports_feedback_mappings_and_profile_counts(self):
        """Status reports feedback mappings, profile, and parking lot counts."""
        root = _temp_project_root(self)
        run_id = "weekly_run_full"
        _build_mock_weekly_run(
            root, run_id,
            with_decisions=True,
            decision_count=3,
            feedback_count=3,
            parking_lot_count=1,
            next_best_action_count=4,
        )

        status = build_weekly_cycle_status(root, run_id=run_id)
        self.assertEqual(status.feedback_mapping_count, 3)
        self.assertTrue(status.preference_profile_present)
        self.assertEqual(status.parking_lot_record_count, 1)
        self.assertEqual(status.next_best_action_count, 4)

    def test_status_handles_missing_manifest(self):
        """Status handles missing manifest with validation failure."""
        root = _temp_project_root(self)
        run_id = "weekly_run_no_manifest"
        run_dir = root / "artifacts" / "weekly_runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        status = build_weekly_cycle_status(root, run_id=run_id)
        self.assertFalse(status.manifest_valid)
        self.assertTrue(len(status.manifest_errors) > 0)
        self.assertFalse(status.validation_passed)

    def test_status_handles_missing_artifact(self):
        """Status handles a missing artifact with validation failure."""
        root = _temp_project_root(self)
        run_id = "weekly_run_missing"
        _build_mock_weekly_run(root, run_id, omit_artifacts=["evidence_packs"])

        status = build_weekly_cycle_status(root, run_id=run_id)
        self.assertTrue(status.manifest_valid)
        self.assertIn("evidence_packs", status.missing_artifact_keys)
        self.assertLess(status.present_artifact_count, status.expected_artifact_count)
        # One artifact missing but manifest valid — still some errors
        self.assertFalse(status.validation_passed)

    def test_status_handles_invalid_json_artifact(self):
        """Status handles invalid JSON artifact without crashing."""
        root = _temp_project_root(self)
        run_id = "weekly_run_corrupt"
        _build_mock_weekly_run(root, run_id, corrupt_artifact="founder_decisions_v2")

        status = build_weekly_cycle_status(root, run_id=run_id)
        self.assertTrue(status.manifest_valid)
        # The corrupt artifact should be detected
        art_errors = []
        for art in status.artifact_statuses:
            art_errors.extend(art.errors)
        self.assertTrue(len(art_errors) > 0)
        self.assertFalse(status.validation_passed)

    def test_status_auto_discovers_latest_run(self):
        """Status auto-discovers the latest run when run_id is omitted."""
        root = _temp_project_root(self)
        _build_mock_weekly_run(root, "weekly_run_2026_01_01_aaa")
        _build_mock_weekly_run(root, "weekly_run_2026_01_02_bbb")
        _build_mock_weekly_run(root, "weekly_run_2026_01_03_ccc")

        status = build_weekly_cycle_status(root, run_id=None)
        self.assertEqual(status.run_id, "weekly_run_2026_01_03_ccc")
        self.assertTrue(status.manifest_valid)

    def test_status_fails_clearly_when_no_runs_exist(self):
        """Status returns error when no weekly runs exist."""
        root = _temp_project_root(self)
        status = build_weekly_cycle_status(root, run_id=None)
        self.assertEqual(status.run_id, "")
        self.assertFalse(status.validation_passed)
        self.assertTrue(len(status.errors) > 0)
        self.assertIn("No weekly runs found", status.errors[0])


# ---------------------------------------------------------------------------
# Tests: Integration with real weekly cycle builder
# ---------------------------------------------------------------------------


class WeeklyCycleStatusIntegrationTests(unittest.TestCase):
    """Test status against real weekly cycle builder output."""

    def _evaluation_dataset_items(self) -> list[dict[str, Any]]:
        """Return evaluation-quality-case-style items."""
        return [
            {
                "case_id": "case_001",
                "title": "Strong SMB invoice collection pain",
                "synthetic_data": True,
                "input_artifacts": {
                    "evidence_pack": {
                        "evidence_pack_id": "ep_case_001",
                        "cluster_id": "cluster_invoice",
                        "topic_id": "smb_invoice_collection",
                        "source_signal_ids": ["sig_001", "sig_002", "sig_003"],
                        "evidence_ids": ["ev_001", "ev_002", "ev_003"],
                        "source_urls": [
                            "https://news.ycombinator.com/item?id=fixture_001",
                            "https://github.com/fixture/repo/issues/1",
                            "https://news.ycombinator.com/item?id=fixture_003",
                        ],
                        "items": [
                            {
                                "evidence_id": "ev_001",
                                "source_signal_id": "sig_001",
                                "source_url": "https://news.ycombinator.com/item?id=fixture_001",
                                "source_type": "hn_algolia",
                                "summary": "SMB owner spends hours on unpaid invoice follow-up.",
                                "confidence": 0.85,
                            },
                            {
                                "evidence_id": "ev_002",
                                "source_signal_id": "sig_002",
                                "source_url": "https://github.com/fixture/repo/issues/1",
                                "source_type": "github_issues",
                                "summary": "Bookkeeper requests automated invoice reminders.",
                                "confidence": 0.80,
                            },
                            {
                                "evidence_id": "ev_003",
                                "source_signal_id": "sig_003",
                                "source_url": "https://news.ycombinator.com/item?id=fixture_003",
                                "source_type": "hn_algolia",
                                "summary": "Freelance accountant: unpaid invoices are #1 cash flow problem.",
                                "confidence": 0.75,
                            },
                        ],
                        "summaries": [
                            "SMB owners spend significant time on unpaid invoice follow-up",
                            "Existing tools lack escalation and personalization",
                            "Multiple independent sources confirm the pain",
                        ],
                        "source_summaries": [
                            {
                                "source_type": "hn_algolia",
                                "source_count": 2,
                                "evidence_ids": ["ev_001", "ev_003"],
                            },
                            {
                                "source_type": "github_issues",
                                "source_count": 1,
                                "evidence_ids": ["ev_002"],
                            },
                        ],
                        "recurrence_count": 3,
                        "source_diversity": 2,
                        "price_signal_ids": ["price_001"],
                        "weak_pattern_ids": [],
                        "kill_warning_ids": [],
                        "risk_notes": [],
                        "confidence_values": [0.85, 0.80, 0.75],
                        "created_from": "fixture_test",
                        "source_types": ["hn_algolia", "github_issues"],
                    }
                },
                "expected": {
                    "quality_label": "pass",
                    "founder_review_posture": "promote",
                },
            },
            {
                "case_id": "case_002",
                "title": "Weak vendor promo should be rejected",
                "synthetic_data": True,
                "input_artifacts": {
                    "evidence_pack": {
                        "evidence_pack_id": "ep_case_002",
                        "cluster_id": "cluster_vendor",
                        "topic_id": "vendor_promo",
                        "source_signal_ids": ["sig_004"],
                        "evidence_ids": ["ev_004"],
                        "source_urls": ["https://github.com/vendor/repo/issues/1"],
                        "items": [
                            {
                                "evidence_id": "ev_004",
                                "source_signal_id": "sig_004",
                                "source_url": "https://github.com/vendor/repo/issues/1",
                                "source_type": "github_issues",
                                "summary": "We built an AI invoicing tool that integrates with Stripe. Check it out!",
                                "confidence": 0.30,
                            },
                        ],
                        "summaries": ["Vendor promo for AI invoicing tool"],
                        "source_summaries": [
                            {
                                "source_type": "github_issues",
                                "source_count": 1,
                                "evidence_ids": ["ev_004"],
                            },
                        ],
                        "recurrence_count": 1,
                        "source_diversity": 1,
                        "price_signal_ids": [],
                        "weak_pattern_ids": [],
                        "kill_warning_ids": [],
                        "risk_notes": [
                            {
                                "risk_type": "vendor_promo",
                                "note": "Looks like a vendor submission.",
                                "severity": "high",
                            }
                        ],
                        "confidence_values": [0.30],
                        "created_from": "fixture_test",
                        "source_types": ["github_issues"],
                    }
                },
                "expected": {
                    "quality_label": "kill",
                    "founder_review_posture": "kill",
                },
            },
        ]

    def test_status_reads_real_weekly_run(self):
        """Status reads a real weekly run produced by build_weekly_cycle()."""
        root = _temp_project_root(self)
        input_items = self._evaluation_dataset_items()
        input_file = root / "fixture_input.json"
        input_file.write_text(json.dumps(input_items, ensure_ascii=False, indent=2), encoding="utf-8")

        result = build_weekly_cycle(
            project_root=root,
            input_file=input_file,
            run_id=None,
        )
        self.assertTrue(result.validation_passed, f"Builder errors: {result.errors}")

        status = build_weekly_cycle_status(root, run_id=result.run_id)
        self.assertTrue(status.manifest_valid, f"Manifest errors: {status.manifest_errors}")
        self.assertEqual(status.expected_artifact_count, 14)
        self.assertEqual(status.present_artifact_count, 14)
        self.assertTrue(status.founder_inbox_present)
        self.assertFalse(status.founder_decisions_imported)
        self.assertIn("review founder_inbox_v2.md", status.recommended_next_step.lower())
        self.assertTrue(status.validation_passed)

    def test_status_is_read_only_does_not_modify_artifacts(self):
        """Status does not modify any run artifacts."""
        root = _temp_project_root(self)
        input_items = self._evaluation_dataset_items()
        input_file = root / "fixture_input.json"
        input_file.write_text(json.dumps(input_items, ensure_ascii=False, indent=2), encoding="utf-8")

        result = build_weekly_cycle(
            project_root=root,
            input_file=input_file,
            run_id=None,
        )
        run_dir = Path(result.run_dir)

        # Collect file hashes before status
        before_hashes: dict[str, str] = {}
        for fpath in sorted(run_dir.iterdir()):
            if fpath.is_file():
                before_hashes[fpath.name] = fpath.read_bytes().hex()

        # Run status check
        status = build_weekly_cycle_status(root, run_id=result.run_id)
        self.assertTrue(status.validation_passed)

        # Collect file hashes after status
        after_hashes: dict[str, str] = {}
        for fpath in sorted(run_dir.iterdir()):
            if fpath.is_file():
                after_hashes[fpath.name] = fpath.read_bytes().hex()

        # Assert no changes
        self.assertEqual(before_hashes, after_hashes,
                         f"Artifacts were modified by status! "
                         f"Before: {set(before_hashes.keys())}, "
                         f"After: {set(after_hashes.keys())}")

    def test_status_handles_empty_input_run(self):
        """Status works on a run with empty input."""
        root = _temp_project_root(self)
        empty_file = root / "empty_input.json"
        empty_file.write_text("[]", encoding="utf-8")

        result = build_weekly_cycle(
            project_root=root,
            input_file=empty_file,
            run_id=None,
        )
        self.assertTrue(result.validation_passed, f"Errors: {result.errors}")

        status = build_weekly_cycle_status(root, run_id=result.run_id)
        self.assertTrue(status.manifest_valid)
        self.assertEqual(status.present_artifact_count, 14)
        self.assertTrue(status.validation_passed)

    def test_status_returns_nonzero_exit_code_for_invalid_run_id(self):
        """Status should indicate validation failure for non-existent run_id."""
        root = _temp_project_root(self)
        status = build_weekly_cycle_status(root, run_id="nonexistent_run")
        self.assertFalse(status.validation_passed)
        self.assertTrue(len(status.errors) > 0)

    def test_status_handles_corrupt_manifest(self):
        """Status handles a run directory with a corrupt/malformed manifest."""
        root = _temp_project_root(self)
        run_id = "corrupt_manifest_run"
        run_dir = root / "artifacts" / "weekly_runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        # Write invalid JSON as manifest
        (run_dir / "manifest.json").write_text("{ invalid json !!!", encoding="utf-8")

        status = build_weekly_cycle_status(root, run_id=run_id)
        self.assertFalse(status.manifest_valid)
        self.assertFalse(status.validation_passed)
        self.assertTrue(len(status.manifest_errors) > 0)


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class WeeklyCycleStatusCLITests(unittest.TestCase):
    """Test CLI behavior of weekly-cycle-status-v2."""

    def _run_cli(self, project_root: Path, run_id: str | None = None, json_output: bool = False) -> tuple[int, str]:
        """Run the CLI command and return (exit_code, output)."""
        from oos.cli import main

        argv = ["weekly-cycle-status-v2", "--project-root", str(project_root)]
        if run_id:
            argv.extend(["--run-id", run_id])
        if json_output:
            argv.append("--json")

        old_stdout = sys.stdout
        captured = StringIO()
        sys.stdout = captured
        try:
            exit_code = main(argv)
        finally:
            sys.stdout = old_stdout

        return exit_code, captured.getvalue()

    def test_cli_exists_and_prints_status(self):
        """CLI command exists and prints status output."""
        temp_root = _temp_project_root(self)
        _build_mock_weekly_run(temp_root, "weekly_run_2026_01_01_cli01")

        exit_code, output = self._run_cli(temp_root, run_id="weekly_run_2026_01_01_cli01")
        self.assertEqual(exit_code, 0)
        self.assertIn("Weekly Cycle Status", output)
        self.assertIn("weekly_run_2026_01_01_cli01", output)

    def test_cli_prints_run_id_manifest_artifact_status(self):
        """CLI prints run_id, manifest status, artifact completeness."""
        temp_root = _temp_project_root(self)
        _build_mock_weekly_run(temp_root, "weekly_run_2026_01_01_cli02")

        exit_code, output = self._run_cli(temp_root, run_id="weekly_run_2026_01_01_cli02")
        self.assertEqual(exit_code, 0)
        self.assertIn("weekly_run_2026_01_01_cli02", output)
        self.assertIn("manifest valid", output.lower())
        self.assertIn("Artifact Completeness", output)
        self.assertIn("Founder Inbox Status", output)
        self.assertIn("Founder Decision Import Status", output)
        self.assertIn("Recommended Next Step", output)

    def test_cli_returns_expected_exit_codes(self):
        """CLI returns 0 on success, 1 on validation issues, 2 on invalid/missing."""
        temp_root = _temp_project_root(self)

        # Exit code 0: valid run
        _build_mock_weekly_run(temp_root, "exit_ok")
        exit_code, _ = self._run_cli(temp_root, run_id="exit_ok")
        self.assertEqual(exit_code, 0)

        # Exit code 1: run with missing artifact (manifest valid but issues)
        _build_mock_weekly_run(temp_root, "exit_issues", omit_artifacts=["evidence_packs"])
        exit_code, _ = self._run_cli(temp_root, run_id="exit_issues")
        # Omitted artifact: manifest is valid (all keys present) but file is missing -> exit 1
        self.assertEqual(exit_code, 1)

        # Exit code 2: invalid run_id (no run found)
        exit_code, _ = self._run_cli(temp_root, run_id="nonexistent")
        self.assertEqual(exit_code, 2)

    def test_cli_json_output(self):
        """CLI --json flag produces valid JSON."""
        temp_root = _temp_project_root(self)
        _build_mock_weekly_run(temp_root, "json_test")

        exit_code, output = self._run_cli(temp_root, run_id="json_test", json_output=True)
        self.assertEqual(exit_code, 0)
        data = json.loads(output)
        self.assertEqual(data["run_id"], "json_test")
        self.assertTrue(data["manifest_valid"])
        self.assertTrue(data["advisory_only"])
        self.assertTrue(data["no_live_api"])
        self.assertTrue(data["no_live_llm"])

    def test_cli_auto_discovers_latest(self):
        """CLI auto-discovers latest run when --run-id omitted."""
        temp_root = _temp_project_root(self)
        _build_mock_weekly_run(temp_root, "weekly_run_2026_01_02_later")
        _build_mock_weekly_run(temp_root, "weekly_run_2026_01_01_earlier")

        exit_code, output = self._run_cli(temp_root)
        self.assertEqual(exit_code, 0)
        self.assertIn("weekly_run_2026_01_02_later", output)

    def test_cli_is_read_only(self):
        """CLI command does not modify run artifacts."""
        temp_root = _temp_project_root(self)
        run_id = "read_only_test"
        run_dir = _build_mock_weekly_run(temp_root, run_id)

        before_mtimes = {}
        for fpath in sorted(run_dir.iterdir()):
            if fpath.is_file():
                before_mtimes[fpath.name] = fpath.stat().st_mtime

        exit_code, _ = self._run_cli(temp_root, run_id=run_id)
        self.assertEqual(exit_code, 0)

        after_mtimes = {}
        for fpath in sorted(run_dir.iterdir()):
            if fpath.is_file():
                after_mtimes[fpath.name] = fpath.stat().st_mtime

        self.assertEqual(before_mtimes, after_mtimes,
                         "CLI command modified artifact files!")

    def test_cli_handles_no_runs_gracefully(self):
        """CLI handles no runs gracefully with exit code 2."""
        temp_root = _temp_project_root(self)
        exit_code, output = self._run_cli(temp_root)
        self.assertEqual(exit_code, 2)
        self.assertIn("No weekly runs found", output)

    def test_existing_run_weekly_cycle_v2_still_works(self):
        """Existing run-weekly-cycle-v2 command still works after status addition."""
        temp_root = _temp_project_root(self)
        input_items = [
            {
                "case_id": "existing_cli_test",
                "title": "Test existing CLI",
                "synthetic_data": True,
                "input_artifacts": {
                    "evidence_pack": {
                        "evidence_pack_id": "ep_cli_test",
                        "cluster_id": "cluster_cli",
                        "topic_id": "test",
                        "source_signal_ids": ["sig_001"],
                        "evidence_ids": ["ev_001"],
                        "source_urls": ["https://example.com/test"],
                        "items": [
                            {
                                "evidence_id": "ev_001",
                                "source_signal_id": "sig_001",
                                "source_url": "https://example.com/test",
                                "source_type": "hn_algolia",
                                "summary": "Test signal.",
                                "confidence": 0.70,
                            },
                        ],
                        "summaries": ["Test summary"],
                        "source_summaries": [
                            {"source_type": "hn_algolia", "source_count": 1, "evidence_ids": ["ev_001"]},
                        ],
                        "recurrence_count": 1,
                        "source_diversity": 1,
                        "price_signal_ids": [],
                        "weak_pattern_ids": [],
                        "kill_warning_ids": [],
                        "risk_notes": [],
                        "confidence_values": [0.70],
                        "created_from": "fixture_test",
                        "source_types": ["hn_algolia"],
                    }
                },
                "expected": {"quality_label": "pass", "founder_review_posture": "promote"},
            }
        ]
        input_file = temp_root / "existing_cli_input.json"
        input_file.write_text(json.dumps(input_items, ensure_ascii=False, indent=2), encoding="utf-8")

        from oos.cli import main

        old_stdout = sys.stdout
        captured = StringIO()
        sys.stdout = captured
        try:
            exit_code = main([
                "run-weekly-cycle-v2",
                "--project-root", str(temp_root),
                "--input-file", str(input_file),
            ])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(exit_code, 0, f"run-weekly-cycle-v2 failed: {captured.getvalue()}")
        self.assertIn("validation_passed: true", captured.getvalue())

    def test_existing_import_founder_decisions_v2_still_works(self):
        """Existing import-founder-decisions-v2 command still works after status addition."""
        temp_root = _temp_project_root(self)
        run_id = "import_cli_test"
        _build_mock_weekly_run(temp_root, run_id, with_inbox=True, inbox_review_items=1)

        decisions_file = temp_root / "decisions.json"
        decisions_file.write_text(
            json.dumps([{"review_item_id": "ri_0", "decision": "PARK", "reason_categories": ["interesting_but_not_now"]}], indent=2),
            encoding="utf-8",
        )

        from oos.cli import main

        old_stdout = sys.stdout
        captured = StringIO()
        sys.stdout = captured
        try:
            exit_code = main([
                "import-founder-decisions-v2",
                "--project-root", str(temp_root),
                "--run-id", run_id,
                "--decisions-file", str(decisions_file),
            ])
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        self.assertEqual(exit_code, 0, f"import-founder-decisions-v2 failed: {output}")
        self.assertIn("validation_passed: true", output)

    def test_no_live_api_no_live_llm_in_status(self):
        """Status always reports no_live_api=True and no_live_llm=True."""
        temp_root = _temp_project_root(self)
        _build_mock_weekly_run(temp_root, "safety_test")

        status = build_weekly_cycle_status(temp_root, run_id="safety_test")
        self.assertTrue(status.advisory_only)
        self.assertTrue(status.no_live_api)
        self.assertTrue(status.no_live_llm)
        self.assertTrue(status.validation_passed)


# ---------------------------------------------------------------------------
# Tests: Import History Audit Trail Visibility (v2.8 item 2.1)
# ---------------------------------------------------------------------------


class TestImportHistoryStatusVisibility(unittest.TestCase):
    """Import history visibility in weekly-cycle-status-v2."""

    def test_status_reports_import_history_when_present(self):
        """Status reports import history entry count when import_history.json exists."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_09_hist01"
        run_dir = _build_mock_weekly_run(root, run_id)
        # Write import_history.json
        hist_path = run_dir / "import_history.json"
        import json
        hist_data = {
            "schema_version": "import_history.v1",
            "run_id": run_id,
            "entries": [
                {
                    "correction_id": "corr_abc123",
                    "corrected_at": "2026-05-09T12:00:00+00:00",
                    "correction_mode": "replace",
                    "replaced_review_item_ids": ["ri_001"],
                    "old_decision_ids": ["fd_old"],
                    "new_decision_ids": ["fd_new"],
                    "old_artifact_checksums": {},
                    "new_artifact_checksums": {},
                    "warnings": [],
                    "errors": [],
                    "advisory_only": True,
                    "no_live_api": True,
                    "no_live_llm": True,
                }
            ],
        }
        hist_path.write_text(json.dumps(hist_data, sort_keys=True, indent=2), encoding="utf-8")

        status = build_weekly_cycle_status(root, run_id=run_id)
        self.assertTrue(status.import_history_present)
        self.assertEqual(status.import_history_entry_count, 1)
        self.assertEqual(status.import_history_latest_correction_mode, "replace")
        self.assertEqual(status.import_history_mode_counts, {"replace": 1})
        self.assertEqual(status.import_history_replaced_decision_ids, ["fd_old"])

        # Check markdown rendering
        md = render_weekly_cycle_status_markdown(status)
        self.assertIn("Import History / Audit Trail", md)
        self.assertIn("- **Correction entry count**: 1", md)
        self.assertIn("replace", md)

    def test_status_reports_latest_correction_mode(self):
        """Status reports latest correction mode from import history."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_09_hist02"
        run_dir = _build_mock_weekly_run(root, run_id)
        import json
        hist_data = {
            "schema_version": "import_history.v1",
            "run_id": run_id,
            "entries": [
                {
                    "correction_id": "corr_1",
                    "corrected_at": "2026-05-09T12:00:00+00:00",
                    "correction_mode": "replace",
                    "replaced_review_item_ids": ["ri_a"],
                    "old_decision_ids": ["fd_a"],
                    "new_decision_ids": ["fd_b"],
                    "old_artifact_checksums": {},
                    "new_artifact_checksums": {},
                    "warnings": [],
                    "errors": [],
                    "advisory_only": True,
                    "no_live_api": True,
                    "no_live_llm": True,
                },
                {
                    "correction_id": "corr_2",
                    "corrected_at": "2026-05-09T13:00:00+00:00",
                    "correction_mode": "amend",
                    "replaced_review_item_ids": ["ri_b"],
                    "old_decision_ids": ["fd_c"],
                    "new_decision_ids": ["fd_c"],
                    "old_artifact_checksums": {},
                    "new_artifact_checksums": {},
                    "warnings": [],
                    "errors": [],
                    "advisory_only": True,
                    "no_live_api": True,
                    "no_live_llm": True,
                },
            ],
        }
        hist_path = run_dir / "import_history.json"
        hist_path.write_text(json.dumps(hist_data, sort_keys=True, indent=2), encoding="utf-8")

        status = build_weekly_cycle_status(root, run_id=run_id)
        self.assertTrue(status.import_history_present)
        self.assertEqual(status.import_history_entry_count, 2)
        self.assertEqual(status.import_history_latest_correction_mode, "amend")
        self.assertEqual(status.import_history_mode_counts, {"replace": 1, "amend": 1})

    def test_status_handles_missing_import_history_gracefully(self):
        """Status handles missing import_history.json without errors."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_09_no_hist"
        _build_mock_weekly_run(root, run_id)

        status = build_weekly_cycle_status(root, run_id=run_id)
        self.assertFalse(status.import_history_present)
        self.assertEqual(status.import_history_entry_count, 0)
        self.assertEqual(status.import_history_latest_correction_mode, "")
        self.assertEqual(status.import_history_mode_counts, {})
        self.assertEqual(status.import_history_replaced_decision_ids, [])
        self.assertEqual(status.import_history_amended_decision_ids, [])

        # Markdown should not error
        md = render_weekly_cycle_status_markdown(status)
        self.assertIn("Import History / Audit Trail", md)
        self.assertIn("no corrections applied", md)

    def test_status_handles_malformed_import_history_gracefully(self):
        """Status handles malformed import_history.json without crashing."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_09_bad_hist"
        run_dir = _build_mock_weekly_run(root, run_id)
        (run_dir / "import_history.json").write_text("not valid json {{{", encoding="utf-8")

        status = build_weekly_cycle_status(root, run_id=run_id)
        self.assertFalse(status.import_history_present)
        self.assertEqual(status.import_history_entry_count, 0)
