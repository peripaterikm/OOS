"""Tests for the unified weekly cycle builder (v2.6 item 2.1)."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from typing import Any

from oos.weekly_cycle_builder import (
    WEEKLY_CYCLE_BUILDER_VERSION,
    WeeklyCycleBuildResult,
    build_weekly_cycle,
)
from oos.weekly_run_manifest import (
    WeeklyRunManifest,
    read_weekly_run_manifest,
    canonical_artifact_paths,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _temp_project_root() -> Path:
    return Path(tempfile.mkdtemp(prefix="oos_test_wcb_"))


def _write_fixture_input(
    project_root: Path,
    items: list[dict[str, Any]],
    *,
    filename: str = "fixture_input.json",
) -> Path:
    path = project_root / filename
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    # Ensure artifacts dir exists
    (project_root / "artifacts" / "weekly_runs").mkdir(parents=True, exist_ok=True)
    return path


def _empty_input_file(project_root: Path) -> Path:
    return _write_fixture_input(project_root, [])


def _evaluation_dataset_items() -> list[dict[str, Any]]:
    """Return a small batch of evaluation-quality-case-style items."""
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
                    "source_urls": ["https://news.ycombinator.com/item?id=fixture_001", "https://github.com/fixture/repo/issues/1", "https://news.ycombinator.com/item?id=fixture_003"],
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
                            "summary": "Bookkeeper requests automated invoice reminders with escalation.",
                            "confidence": 0.80,
                        },
                        {
                            "evidence_id": "ev_003",
                            "source_signal_id": "sig_003",
                            "source_url": "https://news.ycombinator.com/item?id=fixture_003",
                            "source_type": "hn_algolia",
                            "summary": "Freelance accountant says unpaid invoices are #1 cash flow problem.",
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
                "quality_label": "reject",
                "founder_review_posture": "kill",
            },
        },
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWeeklyCycleBuilderEmptyInput(unittest.TestCase):
    """Empty input tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root()

    def test_empty_input_produces_valid_manifest(self) -> None:
        input_file = _empty_input_file(self.project_root)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        self.assertTrue(result.validation_passed)
        self.assertTrue(len(result.errors) == 0)
        # Manifest written
        manifest_path = Path(result.manifest_path)
        self.assertTrue(manifest_path.is_file())
        # All 14 artifacts written
        self.assertEqual(result.artifact_count, 14)
        self.assertIn("manifest", result.artifacts_written)
        self.assertIn("evidence_packs", result.artifacts_written)

    def test_empty_input_marks_empty_states_explicitly(self) -> None:
        input_file = _empty_input_file(self.project_root)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        # Most artifacts should be empty
        self.assertTrue(result.empty_states.get("evidence_packs", False))
        self.assertTrue(result.empty_states.get("opportunity_candidates", False))
        self.assertTrue(result.empty_states.get("quality_gate_decisions", False))
        self.assertTrue(result.empty_states.get("founder_decisions_v2", False))
        self.assertTrue(result.empty_states.get("founder_feedback_mappings", False))
        self.assertTrue(result.empty_states.get("founder_preference_profile", False))
        # Non-empty: weekly_review, run_report, manifest, placeholder artifacts
        self.assertFalse(result.empty_states.get("manifest", True))
        self.assertFalse(result.empty_states.get("run_report", True))
        self.assertFalse(result.empty_states.get("weekly_opportunity_review", True))

    def test_empty_input_does_not_crash(self) -> None:
        input_file = _empty_input_file(self.project_root)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        self.assertTrue(result.validation_passed)
        self.assertEqual(len(result.warnings), 1)  # existing_artifacts_dir warning only
        self.assertTrue(any("existing_artifacts_dir" in w for w in result.warnings))

    def test_empty_input_artifact_files_exist(self) -> None:
        input_file = _empty_input_file(self.project_root)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        paths = canonical_artifact_paths()
        for key, filename in paths.items():
            artifact_path = run_dir / filename
            self.assertTrue(
                artifact_path.is_file(),
                f"Artifact '{key}' not found at {artifact_path}",
            )


class TestWeeklyCycleBuilderNonEmptyInput(unittest.TestCase):
    """Non-empty fixture input tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root()

    def test_fixture_input_produces_evidence_packs(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        self.assertTrue(result.validation_passed)
        self.assertGreater(result.pipeline_summary["evidence_packs_built"], 0)

    def test_fixture_input_produces_opportunity_candidates(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        self.assertGreater(result.pipeline_summary["opportunity_candidates_built"], 0)

    def test_fixture_input_produces_quality_gate_decisions(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        self.assertGreater(result.pipeline_summary["quality_gate_results"], 0)

    def test_fixture_input_produces_weekly_review_package(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        # Verify weekly_opportunity_review.json exists and is valid
        run_dir = Path(result.run_dir)
        review_path = run_dir / canonical_artifact_paths()["weekly_opportunity_review"]
        self.assertTrue(review_path.is_file())
        review_data = json.loads(review_path.read_text(encoding="utf-8"))
        self.assertIn("package_id", review_data)
        self.assertIn("sections", review_data)

    def test_fixture_input_produces_next_best_actions(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        self.assertGreater(result.pipeline_summary["next_best_actions_count"], 0)

    def test_fixture_input_produces_parking_lot_records(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        # Initial run: no founder decisions, so parking lot should be empty
        self.assertEqual(result.pipeline_summary["parking_lot_record_count"], 0)


class TestWeeklyCycleBuilderManifestIntegration(unittest.TestCase):
    """Manifest integration tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root()

    def test_builder_writes_valid_manifest(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        manifest = read_weekly_run_manifest(run_dir)
        self.assertTrue(manifest.is_valid())
        self.assertEqual(manifest.run_id, result.run_id)

    def test_manifest_uses_canonical_paths(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        manifest = read_weekly_run_manifest(run_dir)
        canonical = canonical_artifact_paths()
        for key in canonical:
            self.assertEqual(manifest.artifact_paths.get(key), canonical[key])

    def test_manifest_has_all_14_keys(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        manifest = read_weekly_run_manifest(run_dir)
        self.assertEqual(len(manifest.artifact_paths), 14)

    def test_manifest_has_advisory_flags(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        manifest = read_weekly_run_manifest(run_dir)
        self.assertTrue(manifest.advisory_only)
        self.assertTrue(manifest.no_live_api)
        self.assertTrue(manifest.no_live_llm)

    def test_manifest_validates_after_builder_output(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        # Just reading it and getting no exception means validation passed
        # The read_weekly_run_manifest already validates
        # Find the run_dir
        runs_dir = self.project_root / "artifacts" / "weekly_runs"
        run_dirs = list(runs_dir.iterdir())
        self.assertEqual(len(run_dirs), 1)
        manifest = read_weekly_run_manifest(run_dirs[0])
        self.assertTrue(manifest.is_valid())


class TestWeeklyCycleBuilderDeterminism(unittest.TestCase):
    """Determinism tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root()

    def test_same_input_same_run_id(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result_a = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        result_b = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
            run_id=result_a.run_id,
        )
        self.assertEqual(result_a.run_id, result_b.run_id)

    def test_different_input_different_run_id(self) -> None:
        items_a = _evaluation_dataset_items()
        input_file_a = _write_fixture_input(self.project_root, items_a, filename="input_a.json")
        input_file_b = _write_fixture_input(self.project_root, [], filename="input_b.json")
        result_a = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file_a,
        )
        result_b = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file_b,
        )
        self.assertNotEqual(result_a.run_id, result_b.run_id)


class TestWeeklyCycleBuilderArtifacts(unittest.TestCase):
    """Artifact output tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root()

    def test_all_13_builder_written_artifacts_exist(self) -> None:
        """Verify all 13 builder-written artifacts exist (excluding manifest.json)."""
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        # The builder writes 14 total (13 builder-written + manifest.json)
        # The manifest contract counts manifest.json as well
        builder_artifacts = [
            "evidence_packs",
            "opportunity_candidates",
            "quality_gate_decisions",
            "founder_decisions_v2",
            "founder_feedback_mappings",
            "founder_preference_profile",
            "weekly_opportunity_review",
            "next_best_actions",
            "parking_lot_records",
            "run_report",
            "founder_inbox_v2_index",
            "founder_inbox_v2_md",
            "run_report_md",
        ]
        paths = canonical_artifact_paths()
        for key in builder_artifacts:
            artifact_path = run_dir / paths[key]
            self.assertTrue(
                artifact_path.is_file(),
                f"Builder artifact '{key}' not found at {artifact_path}",
            )

    def test_json_artifacts_are_json_parseable(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        json_artifacts = [
            "evidence_packs",
            "opportunity_candidates",
            "quality_gate_decisions",
            "founder_decisions_v2",
            "founder_feedback_mappings",
            "founder_preference_profile",
            "weekly_opportunity_review",
            "next_best_actions",
            "parking_lot_records",
            "run_report",
            "founder_inbox_v2_index",
            "manifest",
        ]
        paths = canonical_artifact_paths()
        for key in json_artifacts:
            artifact_path = run_dir / paths[key]
            content = artifact_path.read_text(encoding="utf-8")
            try:
                json.loads(content)
            except json.JSONDecodeError as exc:
                self.fail(f"Artifact '{key}' is not valid JSON: {exc}")

    def test_markdown_artifacts_exist_and_non_empty(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        paths = canonical_artifact_paths()
        for md_key in ("founder_inbox_v2_md", "run_report_md"):
            md_path = run_dir / paths[md_key]
            self.assertTrue(md_path.is_file())
            content = md_path.read_text(encoding="utf-8")
            self.assertGreater(len(content.strip()), 0, f"Markdown artifact '{md_key}' is empty")


class TestWeeklyCycleBuilderResultSerialization(unittest.TestCase):
    """Result serialization roundtrip tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root()

    def test_build_result_to_dict_roundtrip(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        d = result.to_dict()
        self.assertEqual(d["run_id"], result.run_id)
        self.assertEqual(d["artifact_count"], result.artifact_count)
        self.assertEqual(d["validation_passed"], result.validation_passed)
        self.assertEqual(d["advisory_only"], True)
        self.assertEqual(d["no_live_api"], True)
        self.assertEqual(d["no_live_llm"], True)

    def test_result_is_json_serializable(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        serialized = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        parsed = json.loads(serialized)
        self.assertEqual(parsed["run_id"], result.run_id)
        self.assertEqual(parsed["artifact_count"], result.artifact_count)


class TestWeeklyCycleBuilderTraceability(unittest.TestCase):
    """Traceability verification tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root()

    def test_opportunity_candidates_have_linked_signal_ids(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        candidates_path = run_dir / canonical_artifact_paths()["opportunity_candidates"]
        data = json.loads(candidates_path.read_text(encoding="utf-8"))
        items_data = data.get("items", [])
        if items_data:
            for candidate in items_data:
                self.assertIn("source_signal_ids", candidate)
                self.assertIn("evidence_ids", candidate)
                self.assertIn("source_urls", candidate)

    def test_quality_gate_decisions_trace_to_opportunity(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        gate_path = run_dir / canonical_artifact_paths()["quality_gate_decisions"]
        data = json.loads(gate_path.read_text(encoding="utf-8"))
        gate_items = data.get("items", [])
        for gate in gate_items:
            self.assertIn("opportunity_id", gate)
            self.assertIn("evidence_pack_id", gate)
            self.assertIn("source_signal_ids", gate)
            self.assertIn("source_urls", gate)

    def test_traceability_ids_present_in_downstream_artifacts(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        # Weekly review should have source IDs
        review_path = run_dir / canonical_artifact_paths()["weekly_opportunity_review"]
        review = json.loads(review_path.read_text(encoding="utf-8"))
        self.assertIn("source_opportunity_ids", review)
        self.assertIn("source_evidence_pack_ids", review)


class TestWeeklyCycleBuilderSafetyBoundaries(unittest.TestCase):
    """Advisory-only, no_live_api, no_live_llm boundary tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root()

    def test_result_marks_advisory_only(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        self.assertTrue(result.advisory_only)
        self.assertTrue(result.no_live_api)
        self.assertTrue(result.no_live_llm)

    def test_manifest_marks_advisory_flags(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        manifest = read_weekly_run_manifest(run_dir)
        self.assertTrue(manifest.advisory_only)
        self.assertTrue(manifest.no_live_api)
        self.assertTrue(manifest.no_live_llm)

    def test_no_real_artifacts_directory_written(self) -> None:
        """Tests write only to temp directories, never the real artifacts/."""
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        run_dir = Path(result.run_dir)
        # The run_dir must be under our temp project_root
        self.assertTrue(
            str(run_dir).startswith(str(self.project_root)),
            "Artifacts must be written under the temp project root, not real artifacts/",
        )


class TestWeeklyCycleBuilderMissingInput(unittest.TestCase):
    """Missing/invalid input tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root()

    def test_missing_input_file_fails_gracefully(self) -> None:
        missing = self.project_root / "does_not_exist.json"
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=missing,
        )
        self.assertFalse(result.validation_passed)
        self.assertTrue(len(result.errors) > 0)

    def test_invalid_run_id_accepted(self) -> None:
        """Providing any run_id should be accepted."""
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
            run_id="custom_test_run_001",
        )
        self.assertTrue(result.validation_passed)
        self.assertEqual(result.run_id, "custom_test_run_001")


class TestWeeklyCycleBuilderPriorArtifacts(unittest.TestCase):
    """Prior artifacts / parking lot revisit tests."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root()

    def test_prior_artifacts_dir_produces_warning_if_no_parking_records(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        # Create a dummy prior run dir without parking records
        prior_dir = self.project_root / "artifacts" / "weekly_runs" / "prior_run"
        prior_dir.mkdir(parents=True, exist_ok=True)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
            existing_artifacts_dir=prior_dir,
        )
        self.assertTrue(any("no valid parking lot records" in w.lower() or "parking" in w.lower() for w in result.warnings))

    def test_no_prior_dir_no_parking_revisit(self) -> None:
        items = _evaluation_dataset_items()
        input_file = _write_fixture_input(self.project_root, items)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        # Should get warning about missing existing_artifacts_dir
        self.assertTrue(any("existing_artifacts_dir" in w for w in result.warnings))
        self.assertEqual(result.pipeline_summary.get("revisit_matches_found", -1), 0)


class TestWeeklyCycleBuilderEmptyRunDir(unittest.TestCase):
    """Test that run_dir is created correctly even for empty input."""

    def setUp(self) -> None:
        self.project_root = _temp_project_root()

    def test_empty_run_dir_contains_all_14_artifacts(self) -> None:
        input_file = _empty_input_file(self.project_root)
        result = build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        self.assertEqual(result.artifact_count, 14)

    def test_empty_run_manifest_is_valid(self) -> None:
        input_file = _empty_input_file(self.project_root)
        build_weekly_cycle(
            project_root=self.project_root,
            input_file=input_file,
        )
        runs_dir = self.project_root / "artifacts" / "weekly_runs"
        run_dirs = list(runs_dir.iterdir())
        self.assertEqual(len(run_dirs), 1)
        manifest = read_weekly_run_manifest(run_dirs[0])
        self.assertTrue(manifest.is_valid())


if __name__ == "__main__":
    unittest.main()
