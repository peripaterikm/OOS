"""Tests for run reports and dashboard index (Roadmap v2.6 item 7.1).

All tests use temp directories — no real artifacts/ are written.
No live APIs, no live LLMs, no portfolio mutations.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from typing import Any

from oos.weekly_run_reports import (
    WeeklyRunReport,
    WeeklyDashboardIndex,
    WeeklyDashboardRunSummary,
    build_weekly_run_report,
    build_weekly_dashboard_index,
    write_weekly_run_report,
    write_weekly_dashboard_index,
    render_weekly_run_report_markdown,
    render_weekly_dashboard_markdown,
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
    tmpdir = tempfile.TemporaryDirectory(prefix="oos_test_rr_")
    test_case.addCleanup(tmpdir.cleanup)
    root = Path(tmpdir.name)
    (root / "artifacts" / "weekly_runs").mkdir(parents=True, exist_ok=True)
    return root


# ---------------------------------------------------------------------------
# Minimal mock weekly run
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
    evidence_pack_count: int = 2,
    opportunity_count: int = 2,
    quality_gate_count: int = 2,
) -> Path:
    """Build a minimal mock weekly run directory for testing."""
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
    empty_states["run_report_md"] = False
    empty_states["founder_inbox_v2_index"] = not with_inbox
    empty_states["founder_inbox_v2_md"] = not with_inbox

    # Write evidence_packs.json
    if "evidence_packs" not in omit:
        ep_items = []
        for i in range(evidence_pack_count):
            ep_items.append({
                "evidence_pack_id": f"ep_{run_id}_{i}",
                "cluster_id": f"cluster_{i}",
                "source_signal_ids": [f"sig_{i}"],
                "evidence_ids": [f"ev_{i}"],
                "source_urls": [f"https://example.com/{i}"],
                "summaries": [f"Summary {i}"],
                "source_types": ["hn"],
                "topic_id": "test_topic",
                "confidence_values": [0.7],
                "source_diversity": 1,
                "recurrence_count": 1,
                "created_from": "test",
                "items": [
                    {
                        "evidence_id": f"ev_{i}",
                        "source_signal_id": f"sig_{i}",
                        "source_url": f"https://example.com/{i}",
                        "source_type": "hn",
                        "summary": f"Summary {i}",
                        "confidence": 0.7,
                    }
                ],
                "source_summaries": [
                    {
                        "source_type": "hn",
                        "source_count": 1,
                        "evidence_ids": [f"ev_{i}"],
                    }
                ],
            })
        (run_dir / paths["evidence_packs"]).write_text(
            json.dumps({"items": ep_items, "schema_version": versions["evidence_packs"], "empty": False},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        empty_states["evidence_packs"] = False

    # Write opportunity_candidates.json
    if "opportunity_candidates" not in omit:
        opp_items = []
        for i in range(opportunity_count):
            opp_items.append({
                "opportunity_id": f"opp_{run_id}_{i}",
                "evidence_pack_id": f"ep_{run_id}_{i}",
                "problem_statement": f"Problem {i}",
                "opportunity_sketch": f"Sketch {i}",
                "evidence_ids": [f"ev_{i}"],
                "source_signal_ids": [f"sig_{i}"],
                "source_urls": [f"https://example.com/{i}"],
            })
        (run_dir / paths["opportunity_candidates"]).write_text(
            json.dumps({"items": opp_items, "schema_version": versions["opportunity_candidates"], "empty": False},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        empty_states["opportunity_candidates"] = False

    # Write quality_gate_decisions.json
    if "quality_gate_decisions" not in omit:
        gate_items = []
        decisions = ["pass", "park", "pass"]
        for i in range(quality_gate_count):
            gate_items.append({
                "opportunity_id": f"opp_{run_id}_{i}",
                "decision": decisions[i % len(decisions)],
                "rationale": f"Rationale {i}",
            })
        (run_dir / paths["quality_gate_decisions"]).write_text(
            json.dumps({"items": gate_items, "schema_version": versions["quality_gate_decisions"], "empty": False},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        empty_states["quality_gate_decisions"] = False

    # Write founder_decisions_v2.json
    if "founder_decisions_v2" not in omit:
        dec_items = []
        for i in range(decision_count):
            dec_items.append({
                "decision_id": f"dec_{run_id}_{i}",
                "review_item_id": f"rev_{i}",
                "decision": "promote",
                "reason": "good_fit",
                "note": f"Note {i}",
            })
        (run_dir / paths["founder_decisions_v2"]).write_text(
            json.dumps({"items": dec_items, "schema_version": versions["founder_decisions_v2"], "empty": decision_count == 0},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if decision_count > 0:
            empty_states["founder_decisions_v2"] = False

    # Write founder_feedback_mappings.json
    if "founder_feedback_mappings" not in omit:
        fm_items = []
        for i in range(feedback_count):
            fm_items.append({
                "feedback_mapping_id": f"fm_{run_id}_{i}",
            })
        (run_dir / paths["founder_feedback_mappings"]).write_text(
            json.dumps({"items": fm_items, "schema_version": versions["founder_feedback_mappings"], "empty": feedback_count == 0},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if feedback_count > 0:
            empty_states["founder_feedback_mappings"] = False

    # Write founder_preference_profile.json
    if "founder_preference_profile" not in omit:
        (run_dir / paths["founder_preference_profile"]).write_text(
            json.dumps({
                "profile_id": f"profile_{run_id}",
                "preferred_pain_types": [],
                "rejected_patterns": [],
                "promoted_patterns": [],
                "recurring_kill_reasons": [],
                "areas_needing_more_evidence": [],
                "decision_count": decision_count,
                "schema_version": versions["founder_preference_profile"],
                "empty": decision_count == 0,
            }, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if decision_count > 0:
            empty_states["founder_preference_profile"] = False

    # Write weekly_opportunity_review.json
    if "weekly_opportunity_review" not in omit:
        (run_dir / paths["weekly_opportunity_review"]).write_text(
            json.dumps({
                "review_package_id": f"worp_{run_id}",
                "schema_version": versions["weekly_opportunity_review"],
                "empty": False,
            }, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # Write next_best_actions.json
    if "next_best_actions" not in omit:
        nba_items = []
        for i in range(next_best_action_count):
            nba_items.append({
                "action_id": f"act_{run_id}_{i}",
                "action_type": "review_opportunity",
                "priority_band": "high",
            })
        (run_dir / paths["next_best_actions"]).write_text(
            json.dumps({"items": nba_items, "schema_version": versions["next_best_actions"], "empty": False},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        empty_states["next_best_actions"] = False

    # Write parking_lot_records.json
    if "parking_lot_records" not in omit:
        pl_items = []
        for i in range(parking_lot_count):
            pl_items.append({
                "record_id": f"pl_{run_id}_{i}",
                "opportunity_id": f"opp_{run_id}_{i}",
            })
        (run_dir / paths["parking_lot_records"]).write_text(
            json.dumps({"items": pl_items, "schema_version": versions["parking_lot_records"], "empty": parking_lot_count == 0},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if parking_lot_count > 0:
            empty_states["parking_lot_records"] = False

    # Write founder inbox v2 index + md
    if with_inbox and "founder_inbox_v2_index" not in omit:
        rev_items = []
        for i in range(inbox_review_items):
            rev_items.append({
                "review_item_id": f"rev_{i}",
                "item_type": "opportunity",
                "linked_opportunity_ids": [f"opp_{run_id}_{i}"],
            })
        (run_dir / paths["founder_inbox_v2_index"]).write_text(
            json.dumps({"review_items": rev_items, "schema_version": versions["founder_inbox_v2_index"]},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if with_inbox and "founder_inbox_v2_md" not in omit:
        (run_dir / paths["founder_inbox_v2_md"]).write_text(
            "# Founder Inbox v2\n\nMock inbox.\n",
            encoding="utf-8",
        )

    # Write run_report.json (placeholder, will be overwritten by build)
    if "run_report" not in omit:
        (run_dir / paths["run_report"]).write_text(
            json.dumps({
                "run_id": run_id,
                "schema_version": "weekly_run_report.v1",
                "placeholder": True,
            }, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # Write run_report.md (placeholder)
    if "run_report_md" not in omit:
        (run_dir / paths["run_report_md"]).write_text(
            "# Weekly Run Report (Placeholder)\n\nMock.\n",
            encoding="utf-8",
        )

    # Corrupt an artifact if requested
    if corrupt_artifact:
        corrupt_path = run_dir / paths.get(corrupt_artifact, corrupt_artifact)
        corrupt_path.write_text("not valid json {{{", encoding="utf-8")

    # Write manifest.json
    manifest_data: dict[str, Any] = {
        "run_id": run_id,
        "created_at": "2026-05-07T00:00:00+00:00",
        "schema_version": "weekly_run_manifest.v1",
        "artifact_paths": dict(paths),
        "artifact_schema_versions": dict(versions),
        "empty_states": {k: empty_states.get(k, True) for k in paths},
        "input_file": "test_input.jsonl",
        "input_signal_count": evidence_pack_count,
        "advisory_only": True,
        "no_live_api": True,
        "no_live_llm": True,
    }
    (run_dir / paths["manifest"]).write_text(
        json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return run_dir


# ---------------------------------------------------------------------------
# Tests: Models
# ---------------------------------------------------------------------------


class TestWeeklyRunReportModel(unittest.TestCase):
    """WeeklyRunReport model tests."""

    def test_serializes_to_json(self) -> None:
        report = WeeklyRunReport(
            run_id="weekly_run_2026_05_07_abc123",
            generated_at="2026-05-07T00:00:00+00:00",
            validation_passed=True,
        )
        data = report.to_dict()
        self.assertEqual(data["run_id"], "weekly_run_2026_05_07_abc123")
        self.assertEqual(data["schema_version"], "weekly_run_report.v1")
        self.assertTrue(data["advisory_only"])
        self.assertTrue(data["no_live_api"])
        self.assertTrue(data["no_live_llm"])
        # Must be JSON-serializable
        serialized = json.dumps(data)
        self.assertIsInstance(serialized, str)
        roundtripped = json.loads(serialized)
        self.assertEqual(roundtripped["run_id"], "weekly_run_2026_05_07_abc123")

    def test_defaults(self) -> None:
        report = WeeklyRunReport()
        self.assertEqual(report.schema_version, "weekly_run_report.v1")
        self.assertEqual(report.run_id, "")
        self.assertFalse(report.validation_passed)
        self.assertTrue(report.advisory_only)


class TestWeeklyDashboardIndexModel(unittest.TestCase):
    """WeeklyDashboardIndex model tests."""

    def test_serializes_to_json(self) -> None:
        dashboard = WeeklyDashboardIndex(
            generated_at="2026-05-07T00:00:00+00:00",
            total_runs=2,
            latest_run_id="weekly_run_2026_05_07_def456",
            complete_run_count=1,
            incomplete_run_count=1,
        )
        data = dashboard.to_dict()
        self.assertEqual(data["total_runs"], 2)
        self.assertEqual(data["latest_run_id"], "weekly_run_2026_05_07_def456")
        self.assertEqual(data["schema_version"], "weekly_dashboard_index.v1")
        self.assertTrue(data["advisory_only"])

    def test_with_run_summaries(self) -> None:
        summary = WeeklyDashboardRunSummary(
            run_id="run_1",
            run_dir="/tmp/runs/run_1",
            manifest_valid=True,
            validation_passed=True,
            present_artifact_count=14,
            expected_artifact_count=14,
        )
        dashboard = WeeklyDashboardIndex(
            total_runs=1,
            latest_run_id="run_1",
            runs=[summary],
        )
        data = dashboard.to_dict()
        self.assertEqual(len(data["runs"]), 1)
        self.assertEqual(data["runs"][0]["run_id"], "run_1")

    def test_defaults(self) -> None:
        dashboard = WeeklyDashboardIndex()
        self.assertEqual(dashboard.schema_version, "weekly_dashboard_index.v1")
        self.assertEqual(dashboard.total_runs, 0)
        self.assertEqual(dashboard.latest_run_id, "")


class TestWeeklyDashboardRunSummaryModel(unittest.TestCase):
    """WeeklyDashboardRunSummary model tests."""

    def test_to_dict(self) -> None:
        summary = WeeklyDashboardRunSummary(
            run_id="run_1",
            manifest_valid=True,
            validation_passed=False,
        )
        data = summary.to_dict()
        self.assertEqual(data["run_id"], "run_1")
        self.assertTrue(data["manifest_valid"])
        self.assertFalse(data["validation_passed"])


# ---------------------------------------------------------------------------
# Tests: build_weekly_run_report
# ---------------------------------------------------------------------------


class TestBuildWeeklyRunReport(unittest.TestCase):
    """build_weekly_run_report tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root(self)

    def test_report_builds_from_valid_run(self) -> None:
        run_id = "weekly_run_2026_05_07_test001"
        _build_mock_weekly_run(
            self.project_root, run_id,
            evidence_pack_count=3,
            opportunity_count=3,
            quality_gate_count=3,
        )
        report = build_weekly_run_report(
            project_root=self.project_root,
            run_id=run_id,
        )
        self.assertEqual(report.run_id, run_id)
        self.assertEqual(report.pipeline_counts.get("evidence_packs"), 3)
        self.assertEqual(report.pipeline_counts.get("opportunity_candidates"), 3)
        self.assertEqual(report.pipeline_counts.get("quality_gate_decisions"), 3)
        self.assertTrue(report.validation_passed)
        self.assertTrue(report.advisory_only)
        self.assertTrue(report.no_live_api)
        self.assertTrue(report.no_live_llm)

    def test_report_handles_missing_run(self) -> None:
        report = build_weekly_run_report(
            project_root=self.project_root,
            run_id="nonexistent_run",
        )
        self.assertEqual(report.run_id, "nonexistent_run")
        self.assertFalse(report.validation_passed)
        self.assertTrue(len(report.errors) > 0)

    def test_report_handles_corrupt_manifest(self) -> None:
        run_id = "weekly_run_2026_05_07_corrupt_mf"
        run_dir = _build_mock_weekly_run(self.project_root, run_id)
        # Corrupt manifest
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text("not valid json {{{", encoding="utf-8")
        report = build_weekly_run_report(
            project_root=self.project_root,
            run_id=run_id,
        )
        self.assertFalse(report.validation_passed)

    def test_report_uses_weekly_cycle_status(self) -> None:
        """Report should use WeeklyCycleStatus as source of truth, not rebuild pipeline."""
        run_id = "weekly_run_2026_05_07_status_test"
        _build_mock_weekly_run(
            self.project_root, run_id,
            evidence_pack_count=5,
            inbox_review_items=4,
            decision_count=2,
        )
        report = build_weekly_run_report(
            project_root=self.project_root,
            run_id=run_id,
        )
        self.assertEqual(report.founder_inbox_summary["review_item_count"], 4)
        self.assertEqual(report.decision_import_summary["decision_summary"]["promote"], 2)

    def test_report_includes_artifact_paths(self) -> None:
        run_id = "weekly_run_2026_05_07_paths_test"
        _build_mock_weekly_run(self.project_root, run_id)
        report = build_weekly_run_report(
            project_root=self.project_root,
            run_id=run_id,
        )
        self.assertIn("manifest", report.artifact_paths)
        self.assertIn("run_report", report.artifact_paths)
        self.assertIn("evidence_packs", report.artifact_paths)

    def test_report_preserves_safety_flags(self) -> None:
        run_id = "weekly_run_2026_05_07_safety_test"
        _build_mock_weekly_run(self.project_root, run_id)
        report = build_weekly_run_report(
            project_root=self.project_root,
            run_id=run_id,
        )
        self.assertTrue(report.advisory_only)
        self.assertTrue(report.no_live_api)
        self.assertTrue(report.no_live_llm)

    def test_report_no_live_calls(self) -> None:
        """Report building must not call any live APIs or LLMs."""
        run_id = "weekly_run_2026_05_07_no_live"
        _build_mock_weekly_run(self.project_root, run_id)
        report = build_weekly_run_report(
            project_root=self.project_root,
            run_id=run_id,
        )
        self.assertTrue(report.no_live_api)
        self.assertTrue(report.no_live_llm)


# ---------------------------------------------------------------------------
# Tests: write_weekly_run_report
# ---------------------------------------------------------------------------


class TestWriteWeeklyRunReport(unittest.TestCase):
    """write_weekly_run_report tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root(self)

    def test_writes_run_report_json_and_md(self) -> None:
        run_id = "weekly_run_2026_05_07_write_test"
        run_dir = self.project_root / "artifacts" / "weekly_runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        report = WeeklyRunReport(
            run_id=run_id,
            generated_at="2026-05-07T00:00:00+00:00",
            validation_passed=True,
            pipeline_counts={"evidence_packs": 3},
        )
        json_path, md_path = write_weekly_run_report(report, run_dir)
        self.assertTrue(json_path.exists())
        self.assertTrue(md_path.exists())
        # Verify JSON content
        data = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(data["run_id"], run_id)
        # Verify MD content
        md_content = md_path.read_text(encoding="utf-8")
        self.assertIn("Weekly Run Report", md_content)
        self.assertIn(run_id, md_content)

    def test_updates_existing_run_report(self) -> None:
        run_id = "weekly_run_2026_05_07_update_test"
        run_dir = self.project_root / "artifacts" / "weekly_runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        # Write a placeholder first
        old_json = run_dir / "run_report.json"
        old_json.write_text('{"placeholder": true}', encoding="utf-8")

        report = WeeklyRunReport(
            run_id=run_id,
            generated_at="2026-05-07T00:00:00+00:00",
            validation_passed=True,
        )
        json_path, md_path = write_weekly_run_report(report, run_dir)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(data["run_id"], run_id)
        self.assertNotIn("placeholder", data)


# ---------------------------------------------------------------------------
# Tests: render_weekly_run_report_markdown
# ---------------------------------------------------------------------------


class TestRenderWeeklyRunReportMarkdown(unittest.TestCase):
    """render_weekly_run_report_markdown tests."""

    def test_renders_basic_sections(self) -> None:
        report = WeeklyRunReport(
            run_id="run_test",
            generated_at="2026-05-07T00:00:00+00:00",
            pipeline_counts={"evidence_packs": 2},
            validation_passed=True,
        )
        md = render_weekly_run_report_markdown(report)
        self.assertIn("# Weekly Run Report", md)
        self.assertIn("run_test", md)
        self.assertIn("Pipeline Counts", md)
        self.assertIn("Status Summary", md)
        self.assertIn("Safety Flags", md)

    def test_renders_errors(self) -> None:
        report = WeeklyRunReport(
            run_id="run_test",
            errors=["Manifest not found", "Artifact missing"],
            validation_passed=False,
        )
        md = render_weekly_run_report_markdown(report)
        self.assertIn("Manifest not found", md)
        self.assertIn("Artifact missing", md)

    def test_renders_empty_sections(self) -> None:
        report = WeeklyRunReport(
            run_id="run_test",
            validation_passed=True,
        )
        md = render_weekly_run_report_markdown(report)
        self.assertIn("Warnings", md)
        self.assertIn("- None", md)


# ---------------------------------------------------------------------------
# Tests: build_weekly_dashboard_index
# ---------------------------------------------------------------------------


class TestBuildWeeklyDashboardIndex(unittest.TestCase):
    """build_weekly_dashboard_index tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root(self)

    def test_dashboard_builds_from_multiple_runs(self) -> None:
        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_01_a")
        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_02_b")
        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_03_c")

        dashboard = build_weekly_dashboard_index(project_root=self.project_root)
        self.assertEqual(dashboard.total_runs, 3)
        self.assertEqual(dashboard.latest_run_id, "weekly_run_2026_05_03_c")
        self.assertEqual(len(dashboard.runs), 3)

    def test_dashboard_handles_empty_runs(self) -> None:
        dashboard = build_weekly_dashboard_index(project_root=self.project_root)
        self.assertEqual(dashboard.total_runs, 0)
        self.assertEqual(dashboard.latest_run_id, "")
        self.assertTrue(len(dashboard.warnings) > 0)

    def test_dashboard_classifies_complete_incomplete_invalid(self) -> None:
        # valid run with decisions = complete
        _build_mock_weekly_run(
            self.project_root, "weekly_run_2026_05_07_complete",
            decision_count=3,
            feedback_count=3,
        )
        # valid run without decisions = incomplete
        _build_mock_weekly_run(
            self.project_root, "weekly_run_2026_05_07_incomplete",
            decision_count=0,
        )
        # missing manifest = invalid
        invalid_dir = self.project_root / "artifacts" / "weekly_runs" / "weekly_run_2026_05_07_invalid"
        invalid_dir.mkdir(parents=True, exist_ok=True)
        (invalid_dir / "manifest.json").write_text("not json {{{", encoding="utf-8")

        dashboard = build_weekly_dashboard_index(project_root=self.project_root)
        self.assertEqual(dashboard.total_runs, 3)
        self.assertEqual(dashboard.complete_run_count, 1)
        # incomplete + invalid
        self.assertGreaterEqual(dashboard.incomplete_run_count + dashboard.invalid_run_count, 2)

    def test_dashboard_auto_discovers_latest_run(self) -> None:
        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_01_old")
        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_07_new")
        dashboard = build_weekly_dashboard_index(project_root=self.project_root)
        self.assertEqual(dashboard.latest_run_id, "weekly_run_2026_05_07_new")

    def test_dashboard_per_run_summary_fields(self) -> None:
        _build_mock_weekly_run(
            self.project_root, "weekly_run_2026_05_07_r1",
            inbox_review_items=5,
            decision_count=2,
            next_best_action_count=3,
        )
        dashboard = build_weekly_dashboard_index(project_root=self.project_root)
        self.assertEqual(len(dashboard.runs), 1)
        run_summary = dashboard.runs[0]
        self.assertEqual(run_summary.run_id, "weekly_run_2026_05_07_r1")
        self.assertTrue(run_summary.manifest_valid)
        self.assertEqual(run_summary.founder_inbox_review_item_count, 5)
        self.assertEqual(run_summary.founder_decision_count, 2)
        self.assertEqual(run_summary.next_best_action_count, 3)

    def test_dashboard_safety_flags(self) -> None:
        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_07_sf")
        dashboard = build_weekly_dashboard_index(project_root=self.project_root)
        self.assertTrue(dashboard.advisory_only)
        self.assertTrue(dashboard.no_live_api)
        self.assertTrue(dashboard.no_live_llm)

    def test_dashboard_no_live_calls(self) -> None:
        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_07_nl")
        dashboard = build_weekly_dashboard_index(project_root=self.project_root)
        self.assertTrue(dashboard.no_live_api)
        self.assertTrue(dashboard.no_live_llm)


# ---------------------------------------------------------------------------
# Tests: write_weekly_dashboard_index
# ---------------------------------------------------------------------------


class TestWriteWeeklyDashboardIndex(unittest.TestCase):
    """write_weekly_dashboard_index tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root(self)

    def test_writes_dashboard_json_and_md(self) -> None:
        weekly_runs_root = self.project_root / "artifacts" / "weekly_runs"

        dashboard = WeeklyDashboardIndex(
            generated_at="2026-05-07T00:00:00+00:00",
            total_runs=2,
            latest_run_id="run_2",
            runs=[
                WeeklyDashboardRunSummary(run_id="run_1", manifest_valid=True),
                WeeklyDashboardRunSummary(run_id="run_2", manifest_valid=True, validation_passed=True),
            ],
        )
        json_path, md_path = write_weekly_dashboard_index(dashboard, weekly_runs_root)
        self.assertTrue(json_path.exists())
        self.assertTrue(md_path.exists())
        # Verify JSON
        data = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(data["total_runs"], 2)
        # Verify MD
        md_content = md_path.read_text(encoding="utf-8")
        self.assertIn("Weekly Runs Dashboard", md_content)
        self.assertIn("run_1", md_content)
        self.assertIn("run_2", md_content)

    def test_writes_empty_dashboard(self) -> None:
        weekly_runs_root = self.project_root / "artifacts" / "weekly_runs"
        dashboard = WeeklyDashboardIndex(total_runs=0)
        json_path, md_path = write_weekly_dashboard_index(dashboard, weekly_runs_root)
        self.assertTrue(json_path.exists())
        self.assertTrue(md_path.exists())


# ---------------------------------------------------------------------------
# Tests: render_weekly_dashboard_markdown
# ---------------------------------------------------------------------------


class TestRenderWeeklyDashboardMarkdown(unittest.TestCase):
    """render_weekly_dashboard_markdown tests."""

    def test_renders_table(self) -> None:
        dashboard = WeeklyDashboardIndex(
            total_runs=2,
            latest_run_id="run_2",
            runs=[
                WeeklyDashboardRunSummary(
                    run_id="run_1",
                    manifest_valid=True,
                    validation_passed=True,
                    present_artifact_count=14,
                    expected_artifact_count=14,
                ),
                WeeklyDashboardRunSummary(
                    run_id="run_2",
                    manifest_valid=True,
                    validation_passed=False,
                    present_artifact_count=13,
                    expected_artifact_count=14,
                ),
            ],
        )
        md = render_weekly_dashboard_markdown(dashboard)
        self.assertIn("# Weekly Runs Dashboard", md)
        self.assertIn("Aggregate Metrics", md)
        self.assertIn("Run Summary Table", md)
        self.assertIn("run_1", md)
        self.assertIn("run_2", md)
        self.assertIn("Safety Flags", md)

    def test_renders_empty_dashboard(self) -> None:
        dashboard = WeeklyDashboardIndex(total_runs=0)
        md = render_weekly_dashboard_markdown(dashboard)
        self.assertIn("Total runs**: 0", md)
        self.assertNotIn("Run Summary Table", md)

    def test_renders_warnings_and_errors(self) -> None:
        dashboard = WeeklyDashboardIndex(
            warnings=["[run_1] Warning A"],
            errors=["[run_2] Error B"],
        )
        md = render_weekly_dashboard_markdown(dashboard)
        self.assertIn("[run_1] Warning A", md)
        self.assertIn("[run_2] Error B", md)


# ---------------------------------------------------------------------------
# Tests: weekly_cycle_builder integration
# ---------------------------------------------------------------------------


class TestWeeklyCycleBuilderReportIntegration(unittest.TestCase):
    """Test that the weekly cycle builder produces real run reports."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root(self)

    def test_builder_produces_real_run_report(self) -> None:
        """build_weekly_cycle should write a real run_report.json (not placeholder)."""
        import json
        input_file = self.project_root / "test_input.json"
        input_file.write_text(json.dumps([
            {
                "signal_id": "sig_1",
                "title": "Test Pain",
                "text": "Users complain about slow invoicing.",
                "source_type": "hn",
                "source_ref": "https://news.ycombinator.com/item?id=1",
            },
        ]), encoding="utf-8")

        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        self.assertTrue(result.validation_passed, f"Errors: {result.errors}")

        run_dir = Path(result.run_dir)
        report_json_path = run_dir / "run_report.json"
        self.assertTrue(report_json_path.is_file())
        report_data = json.loads(report_json_path.read_text(encoding="utf-8"))
        # Should NOT be a placeholder
        self.assertNotIn("placeholder", report_data)
        self.assertEqual(report_data.get("schema_version"), "weekly_run_report.v1")
        self.assertEqual(report_data.get("run_id"), result.run_id)
        # Should have pipeline counts
        pc = report_data.get("pipeline_counts", {})
        self.assertGreaterEqual(pc.get("evidence_packs", 0), 0)

        # run_report.md should also exist
        report_md_path = run_dir / "run_report.md"
        self.assertTrue(report_md_path.is_file())
        md_content = report_md_path.read_text(encoding="utf-8")
        self.assertIn("Weekly Run Report", md_content)

    def test_builder_empty_input_produces_real_report(self) -> None:
        """Empty input should still produce a real run report."""
        input_file = self.project_root / "test_empty.json"
        input_file.write_text("[]", encoding="utf-8")

        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        report_json_path = run_dir / "run_report.json"
        self.assertTrue(report_json_path.is_file())
        report_data = json.loads(report_json_path.read_text(encoding="utf-8"))
        self.assertNotIn("placeholder", report_data)
        self.assertEqual(report_data.get("run_id"), result.run_id)


# ---------------------------------------------------------------------------
# Tests: CLI commands
# ---------------------------------------------------------------------------


class TestCliBuildWeeklyRunReportV2(unittest.TestCase):
    """CLI build-weekly-run-report-v2 tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root(self)
        from contextlib import redirect_stdout

        self.redirect_stdout = redirect_stdout

    def test_cli_builds_report_successfully(self) -> None:
        from oos.cli import main

        run_id = "weekly_run_2026_05_07_cli_001"
        _build_mock_weekly_run(self.project_root, run_id)

        stdout = StringIO()
        with self.redirect_stdout(stdout):
            exit_code = main([
                "build-weekly-run-report-v2",
                "--project-root", str(self.project_root),
                "--run-id", run_id,
            ])
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("OOS v2.6 weekly run report built.", output)
        self.assertIn(f"run_id: {run_id}", output)
        self.assertIn("report_json:", output)
        self.assertIn("report_md:", output)

    def test_cli_missing_run_id_fails(self) -> None:
        from oos.cli import main

        stdout = StringIO()
        with self.redirect_stdout(stdout):
            exit_code = main([
                "build-weekly-run-report-v2",
                "--project-root", str(self.project_root),
                "--run-id", "nonexistent",
            ])
        self.assertNotEqual(exit_code, 0)

    def test_cli_no_portfolio_mutation(self) -> None:
        """build-weekly-run-report-v2 must not mutate portfolio state."""
        from oos.cli import main

        run_id = "weekly_run_2026_05_07_cli_nopm"
        run_dir = _build_mock_weekly_run(self.project_root, run_id)

        # Snapshot all artifacts before
        before = {}
        for f in run_dir.iterdir():
            if f.is_file():
                before[f.name] = f.read_bytes()

        stdout = StringIO()
        with self.redirect_stdout(stdout):
            main([
                "build-weekly-run-report-v2",
                "--project-root", str(self.project_root),
                "--run-id", run_id,
            ])

        # Only run_report.json + run_report.md should have changed
        for f in run_dir.iterdir():
            if f.is_file():
                if f.name in ("run_report.json", "run_report.md"):
                    continue
                self.assertEqual(
                    before.get(f.name), f.read_bytes(),
                    f"Artifact {f.name} was modified (should be read-only for non-report artifacts)"
                )

    def test_cli_no_live_calls(self) -> None:
        from oos.cli import main

        run_id = "weekly_run_2026_05_07_cli_nl"
        _build_mock_weekly_run(self.project_root, run_id)

        stdout = StringIO()
        with self.redirect_stdout(stdout):
            exit_code = main([
                "build-weekly-run-report-v2",
                "--project-root", str(self.project_root),
                "--run-id", run_id,
            ])
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("no_live_api: true", output)
        self.assertIn("no_live_llm: true", output)


class TestCliWeeklyDashboardV2(unittest.TestCase):
    """CLI weekly-dashboard-v2 tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root(self)
        from contextlib import redirect_stdout

        self.redirect_stdout = redirect_stdout

    def test_cli_builds_dashboard(self) -> None:
        from oos.cli import main

        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_01_a")
        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_02_b")

        stdout = StringIO()
        with self.redirect_stdout(stdout):
            exit_code = main([
                "weekly-dashboard-v2",
                "--project-root", str(self.project_root),
            ])
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("OOS v2.6 weekly dashboard index built.", output)
        self.assertIn("total_runs: 2", output)
        self.assertIn("dashboard_json:", output)
        self.assertIn("dashboard_md:", output)

    def test_cli_dashboard_empty_runs(self) -> None:
        from oos.cli import main

        stdout = StringIO()
        with self.redirect_stdout(stdout):
            exit_code = main([
                "weekly-dashboard-v2",
                "--project-root", str(self.project_root),
            ])
        output = stdout.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("total_runs: 0", output)

    def test_cli_dashboard_no_live_calls(self) -> None:
        from oos.cli import main

        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_07_dash")

        stdout = StringIO()
        with self.redirect_stdout(stdout):
            exit_code = main([
                "weekly-dashboard-v2",
                "--project-root", str(self.project_root),
            ])
        self.assertEqual(exit_code, 0)

    def test_cli_dashboard_writes_files(self) -> None:
        from oos.cli import main

        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_07_f")
        stdout = StringIO()
        with self.redirect_stdout(stdout):
            main([
                "weekly-dashboard-v2",
                "--project-root", str(self.project_root),
            ])

        dash_json = self.project_root / "artifacts" / "weekly_runs" / "dashboard_index.json"
        dash_md = self.project_root / "artifacts" / "weekly_runs" / "dashboard.md"
        self.assertTrue(dash_json.exists(), f"Expected {dash_json} to exist")
        self.assertTrue(dash_md.exists(), f"Expected {dash_md} to exist")


# ---------------------------------------------------------------------------
# Tests: determinism
# ---------------------------------------------------------------------------


class TestDeterminism(unittest.TestCase):
    """Determinism tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root(self)

    def test_report_is_deterministic(self) -> None:
        run_id = "weekly_run_2026_05_07_det"
        _build_mock_weekly_run(self.project_root, run_id)

        report1 = build_weekly_run_report(project_root=self.project_root, run_id=run_id)
        report2 = build_weekly_run_report(project_root=self.project_root, run_id=run_id)

        # generated_at will differ, but all other fields should match
        data1 = report1.to_dict()
        data2 = report2.to_dict()
        for key in data1:
            if key in ("generated_at",):
                continue
            self.assertEqual(data1[key], data2[key], f"Mismatch on key: {key}")

    def test_dashboard_is_deterministic(self) -> None:
        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_07_d1")
        _build_mock_weekly_run(self.project_root, "weekly_run_2026_05_07_d2")

        dash1 = build_weekly_dashboard_index(project_root=self.project_root)
        dash2 = build_weekly_dashboard_index(project_root=self.project_root)

        data1 = dash1.to_dict()
        data2 = dash2.to_dict()
        for key in data1:
            if key in ("generated_at",):
                continue
            self.assertEqual(data1[key], data2[key], f"Mismatch on key: {key}")


# ---------------------------------------------------------------------------
# Tests: existing commands still work
# ---------------------------------------------------------------------------


class TestExistingCommandsUntouched(unittest.TestCase):
    """Verify existing CLI commands still work after item 7.1 changes."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root(self)
        from contextlib import redirect_stdout

        self.redirect_stdout = redirect_stdout

    def test_weekly_cycle_status_v2_still_works(self) -> None:
        from oos.cli import main

        run_id = "weekly_run_2026_05_07_ec1"
        _build_mock_weekly_run(self.project_root, run_id)

        stdout = StringIO()
        with self.redirect_stdout(stdout):
            exit_code = main([
                "weekly-cycle-status-v2",
                "--project-root", str(self.project_root),
                "--run-id", run_id,
            ])
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Weekly Cycle Status", output)

    def test_run_weekly_cycle_v2_still_works(self) -> None:
        from oos.cli import main

        input_file = self.project_root / "test_input.json"
        input_file.write_text(json.dumps([
            {
                "signal_id": "sig_1",
                "title": "Test",
                "text": "Test text for invoicing pain.",
                "source_type": "hn",
                "source_ref": "https://example.com/1",
            },
        ]), encoding="utf-8")

        stdout = StringIO()
        with self.redirect_stdout(stdout):
            exit_code = main([
                "run-weekly-cycle-v2",
                "--project-root", str(self.project_root),
                "--input-file", str(input_file),
            ])
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0, f"Output: {output}")
        self.assertIn("OOS v2.6 weekly cycle completed.", output)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# Tests: Import History Audit Trail Visibility (v2.8 item 2.1)
# ---------------------------------------------------------------------------


class TestImportHistoryReportVisibility(unittest.TestCase):
    """Import history visibility in run reports and dashboard."""

    def test_report_includes_import_history_summary(self):
        """Run report includes import history summary."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_09_rpt"
        run_dir = _build_mock_weekly_run(root, run_id)
        # Write import_history.json
        import json
        hist_data = {
            "schema_version": "import_history.v1",
            "run_id": run_id,
            "entries": [
                {
                    "correction_id": "corr_rpt1",
                    "corrected_at": "2026-05-09T12:00:00+00:00",
                    "correction_mode": "replace",
                    "replaced_review_item_ids": ["ri_001"],
                    "old_decision_ids": ["fd_old"],
                    "new_decision_ids": ["fd_new"],
                    "old_artifact_checksums": {"fd": "abc"},
                    "new_artifact_checksums": {"fd": "def"},
                    "warnings": [],
                    "errors": [],
                    "advisory_only": True,
                    "no_live_api": True,
                    "no_live_llm": True,
                }
            ],
        }
        (run_dir / "import_history.json").write_text(
            json.dumps(hist_data, sort_keys=True, indent=2), encoding="utf-8"
        )

        report = build_weekly_run_report(
            project_root=root,
            run_id=run_id,
        )
        self.assertIn("import_history_summary", report.to_dict())
        ihs = report.import_history_summary
        self.assertTrue(ihs.get("present"))
        self.assertEqual(ihs.get("entry_count"), 1)
        self.assertEqual(ihs.get("latest_correction_mode"), "replace")
        self.assertEqual(ihs.get("replaced_decision_ids"), ["fd_old"])

        # Markdown rendering
        md = render_weekly_run_report_markdown(report)
        self.assertIn("Import History / Audit Trail", md)
        self.assertIn("Correction entries", md)

    def test_dashboard_includes_correction_count(self):
        """Dashboard run summary includes correction_count."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_09_dash"
        run_dir = _build_mock_weekly_run(root, run_id)
        import json
        hist_data = {
            "schema_version": "import_history.v1",
            "run_id": run_id,
            "entries": [
                {
                    "correction_id": "corr_d1",
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
                    "correction_id": "corr_d2",
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
        (run_dir / "import_history.json").write_text(
            json.dumps(hist_data, sort_keys=True, indent=2), encoding="utf-8"
        )

        dashboard = build_weekly_dashboard_index(project_root=root)
        self.assertGreaterEqual(len(dashboard.runs), 1)
        r = [s for s in dashboard.runs if s.run_id == run_id][0]
        self.assertEqual(r.correction_count, 2)

        # Dashboard markdown should show correction count
        md = render_weekly_dashboard_markdown(dashboard)
        self.assertIn("Corrections", md)

    def test_report_handles_missing_import_history_gracefully(self):
        """Run report handles missing import_history.json without errors."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_09_nohist"
        _build_mock_weekly_run(root, run_id)

        report = build_weekly_run_report(
            project_root=root,
            run_id=run_id,
        )
        ihs = report.import_history_summary
        self.assertFalse(ihs.get("present"))
        self.assertEqual(ihs.get("entry_count"), 0)

        md = render_weekly_run_report_markdown(report)
        self.assertIn("Import History / Audit Trail", md)
        self.assertIn("No corrections recorded", md)

    def test_report_includes_replaced_amended_decision_ids(self):
        """Run report includes replaced/amended decision IDs where available."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_09_ids"
        run_dir = _build_mock_weekly_run(root, run_id)
        import json
        hist_data = {
            "schema_version": "import_history.v1",
            "run_id": run_id,
            "entries": [
                {
                    "correction_id": "corr_ids1",
                    "corrected_at": "2026-05-09T12:00:00+00:00",
                    "correction_mode": "replace",
                    "replaced_review_item_ids": ["ri_x"],
                    "old_decision_ids": ["fd_replaced_1", "fd_replaced_2"],
                    "new_decision_ids": ["fd_new_1", "fd_new_2"],
                    "old_artifact_checksums": {},
                    "new_artifact_checksums": {},
                    "warnings": [],
                    "errors": [],
                    "advisory_only": True,
                    "no_live_api": True,
                    "no_live_llm": True,
                },
                {
                    "correction_id": "corr_ids2",
                    "corrected_at": "2026-05-09T13:00:00+00:00",
                    "correction_mode": "amend",
                    "replaced_review_item_ids": ["ri_y"],
                    "old_decision_ids": ["fd_amended"],
                    "new_decision_ids": ["fd_amended"],
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
        (run_dir / "import_history.json").write_text(
            json.dumps(hist_data, sort_keys=True, indent=2), encoding="utf-8"
        )

        report = build_weekly_run_report(
            project_root=root,
            run_id=run_id,
        )
        ihs = report.import_history_summary
        self.assertIn("fd_replaced_1", ihs.get("replaced_decision_ids", []))
        self.assertIn("fd_replaced_2", ihs.get("replaced_decision_ids", []))
        self.assertIn("fd_amended", ihs.get("amended_decision_ids", []))
        self.assertEqual(len(ihs.get("replaced_decision_ids", [])), 2)
        self.assertEqual(len(ihs.get("amended_decision_ids", [])), 1)


# ---------------------------------------------------------------------------
# Tests: Decision Corrections in Reports/Dashboard (v2.8 item 3.1)
# ---------------------------------------------------------------------------


class TestDecisionCorrectionsReportIntegration(unittest.TestCase):
    """Decision Corrections visibility in run reports and dashboard."""

    def test_run_report_json_includes_import_history_summary(self):
        """run_report.json includes import_history_summary with corrections."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_10_rr01"
        run_dir = _build_mock_weekly_run(root, run_id)
        import json
        hist_data = {
            "schema_version": "import_history.v1",
            "run_id": run_id,
            "entries": [
                {
                    "correction_id": "corr_rr1",
                    "corrected_at": "2026-05-10T12:00:00+00:00",
                    "correction_mode": "replace",
                    "replaced_review_item_ids": ["ri_x"],
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
        (run_dir / "import_history.json").write_text(
            json.dumps(hist_data, sort_keys=True, indent=2), encoding="utf-8"
        )

        report = build_weekly_run_report(
            project_root=root,
            run_id=run_id,
        )
        data = report.to_dict()
        self.assertIn("import_history_summary", data)
        ihs = data["import_history_summary"]
        self.assertTrue(ihs.get("present"))
        self.assertEqual(ihs.get("entry_count"), 1)
        self.assertEqual(ihs.get("latest_correction_mode"), "replace")
        self.assertIn("fd_old", ihs.get("replaced_decision_ids", []))

    def test_run_report_md_includes_per_correction_details(self):
        """run_report.md includes per-correction details section."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_10_rr02"
        run_dir = _build_mock_weekly_run(root, run_id)
        import json
        hist_data = {
            "schema_version": "import_history.v1",
            "run_id": run_id,
            "entries": [
                {
                    "correction_id": "corr_md_r1",
                    "corrected_at": "2026-05-10T12:00:00+00:00",
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
                    "correction_id": "corr_md_r2",
                    "corrected_at": "2026-05-10T13:00:00+00:00",
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
        (run_dir / "import_history.json").write_text(
            json.dumps(hist_data, sort_keys=True, indent=2), encoding="utf-8"
        )

        report = build_weekly_run_report(
            project_root=root,
            run_id=run_id,
        )
        md = render_weekly_run_report_markdown(report)
        self.assertIn("Import History / Audit Trail", md)
        self.assertIn("Correction entries**: 2", md)
        self.assertIn("Per-Correction Details", md)

    def test_dashboard_md_includes_corrections_column(self):
        """Dashboard Markdown table includes Corrections column."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_10_dash01"
        run_dir = _build_mock_weekly_run(root, run_id)
        import json
        hist_data = {
            "schema_version": "import_history.v1",
            "run_id": run_id,
            "entries": [
                {
                    "correction_id": "corr_dc1",
                    "corrected_at": "2026-05-10T12:00:00+00:00",
                    "correction_mode": "replace",
                    "replaced_review_item_ids": ["ri_d"],
                    "old_decision_ids": ["fd_d1"],
                    "new_decision_ids": ["fd_d2"],
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
        (run_dir / "import_history.json").write_text(
            json.dumps(hist_data, sort_keys=True, indent=2), encoding="utf-8"
        )

        dashboard = build_weekly_dashboard_index(project_root=root)
        md = render_weekly_dashboard_markdown(dashboard)
        self.assertIn("Corrections", md)
        # Check for corrected run in the table
        self.assertIn(run_id, md)

        # Verify correction_count in run summary
        r_summaries = [r for r in dashboard.runs if r.run_id == run_id]
        self.assertEqual(len(r_summaries), 1)
        self.assertEqual(r_summaries[0].correction_count, 1)

    def test_dashboard_md_includes_corrected_indicator(self):
        """Dashboard Markdown includes [CORRECTED] indicator for corrected runs."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_10_dash02"
        run_dir = _build_mock_weekly_run(root, run_id)
        import json
        hist_data = {
            "schema_version": "import_history.v1",
            "run_id": run_id,
            "entries": [
                {
                    "correction_id": "corr_ind_d",
                    "corrected_at": "2026-05-10T12:00:00+00:00",
                    "correction_mode": "amend",
                    "replaced_review_item_ids": ["ri_e"],
                    "old_decision_ids": ["fd_e"],
                    "new_decision_ids": ["fd_e"],
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
        (run_dir / "import_history.json").write_text(
            json.dumps(hist_data, sort_keys=True, indent=2), encoding="utf-8"
        )

        dashboard = build_weekly_dashboard_index(project_root=root)
        md = render_weekly_dashboard_markdown(dashboard)
        self.assertIn("[CORRECTED]", md)

    def test_missing_import_history_handled_cleanly_by_reports(self):
        """Run report and dashboard handle missing import_history.json cleanly."""
        root = _temp_project_root(self)
        run_id = "weekly_run_2026_05_10_no_hist"
        _build_mock_weekly_run(root, run_id)

        # Run report
        report = build_weekly_run_report(
            project_root=root,
            run_id=run_id,
        )
        ihs = report.import_history_summary
        self.assertFalse(ihs.get("present"))
        self.assertEqual(ihs.get("entry_count"), 0)
        md_report = render_weekly_run_report_markdown(report)
        self.assertIn("No corrections recorded", md_report)
        self.assertNotIn("[CORRECTED]", md_report)

        # Dashboard
        dashboard = build_weekly_dashboard_index(project_root=root)
        md_dash = render_weekly_dashboard_markdown(dashboard)
        self.assertNotIn("[CORRECTED]", md_dash)
        # Should show 0 in corrections column
        self.assertIn("0", md_dash)
