"""Tests for founder decision import (Roadmap v2.6 item 5.1).

All tests use temp directories — no real artifacts/ are written.
No live APIs, no live LLMs, no portfolio mutations.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from oos.founder_decision_import import (
    FounderDecisionImportInput,
    FounderDecisionImportResult,
    _dedupe_sorted,
    _extract_reason_categories,
    _merge_decisions,
    _merge_parking_lot_records,
    _safe_string_list,
    import_founder_decisions,
    load_founder_decision_inputs,
    validate_founder_decision_inputs,
)
from oos.founder_decision_taxonomy import (
    PARK,
    FounderDecisionReason,
    FounderDecisionV2,
    create_founder_decision,
)
from oos.founder_inbox_v2 import DECISION_OPTIONS


# ---------------------------------------------------------------------------
# Helpers for building test fixtures
# ---------------------------------------------------------------------------


def _make_temp_decisions_file(decisions: list[dict]) -> Path:
    """Write decisions to a temp JSON file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        suffix=".json", mode="w", encoding="utf-8", delete=False
    )
    json.dump(decisions, tmp, indent=2)
    tmp.close()
    return Path(tmp.name)


def _make_temp_jsonl_decisions_file(decisions: list[dict]) -> Path:
    """Write decisions to a temp JSONL file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        suffix=".jsonl", mode="w", encoding="utf-8", delete=False
    )
    for d in decisions:
        tmp.write(json.dumps(d) + "\n")
    tmp.close()
    return Path(tmp.name)


def _make_minimal_inbox_index(review_items: list[dict]) -> dict:
    """Create a minimal inbox index dict for validation."""
    return {
        "review_items": review_items,
        "schema_version": "founder_inbox_v2.v1",
    }


def _make_inbox_item(
    review_item_id: str,
    section_id: str = "top_opportunities_to_review",
    linked_opportunity_ids: list[str] | None = None,
    linked_evidence_pack_ids: list[str] | None = None,
    linked_evidence_ids: list[str] | None = None,
    decision_options: list[str] | None = None,
    linked_source_urls: list[str] | None = None,
) -> dict:
    return {
        "review_item_id": review_item_id,
        "section_id": section_id,
        "title": f"Test item {review_item_id}",
        "summary": "A test review item.",
        "recommended_founder_action": "Review and decide.",
        "decision_options": decision_options or list(DECISION_OPTIONS),
        "linked_opportunity_ids": linked_opportunity_ids or [f"opp_{review_item_id}"],
        "linked_evidence_pack_ids": linked_evidence_pack_ids or [f"ep_{review_item_id}"],
        "linked_evidence_ids": linked_evidence_ids or [f"ev_{review_item_id}"],
        "linked_quality_gate_ids": [f"qg_{review_item_id}"],
        "linked_action_ids": [],
        "linked_parking_lot_record_ids": [],
        "linked_revisit_match_ids": [],
        "linked_source_artifact_ids": [],
        "linked_source_urls": linked_source_urls if linked_source_urls is not None else [f"https://example.com/{review_item_id}"],
        "source_section": section_id,
        "advisory_only": True,
    }


def _build_mock_weekly_run(
    project_root: Path,
    run_id: str,
    *,
    with_inbox: bool = True,
    with_decisions: bool = False,
    existing_decisions: list[dict] | None = None,
    inbox_items: list[dict] | None = None,
) -> Path:
    """Build a minimal mock weekly run directory for testing.

    Returns the run directory path.
    """
    run_dir = project_root / "artifacts" / "weekly_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Write manifest.json
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "weekly_run_manifest.v1",
        "artifact_paths": {
            "manifest": "manifest.json",
            "evidence_packs": "evidence_packs.json",
            "opportunity_candidates": "opportunity_candidates.json",
            "quality_gate_decisions": "quality_gate_decisions.json",
            "founder_decisions_v2": "founder_decisions_v2.json",
            "founder_feedback_mappings": "founder_feedback_mappings.json",
            "founder_preference_profile": "founder_preference_profile.json",
            "weekly_opportunity_review": "weekly_opportunity_review.json",
            "next_best_actions": "next_best_actions.json",
            "parking_lot_records": "parking_lot_records.json",
            "run_report": "run_report.json",
            "founder_inbox_v2_index": "founder_inbox_v2_index.json",
            "founder_inbox_v2_md": "founder_inbox_v2.md",
            "run_report_md": "run_report.md",
        },
        "artifact_schema_versions": {
            "manifest": "weekly_run_manifest.v1",
            "evidence_packs": "evidence_pack.v1",
            "opportunity_candidates": "opportunity_sketch.v1",
            "quality_gate_decisions": "opportunity_quality_gate.v1",
            "founder_decisions_v2": "founder_decision_v2.v1",
            "founder_feedback_mappings": "founder_feedback_mapping.v1",
            "founder_preference_profile": "founder_preference_profile.v1",
            "weekly_opportunity_review": "weekly_opportunity_review.v1",
            "next_best_actions": "founder_action.v1",
            "parking_lot_records": "parking_lot.v1",
            "run_report": "weekly_run_report.v1",
            "founder_inbox_v2_index": "founder_inbox_v2_index.v1",
            "founder_inbox_v2_md": "founder_inbox_v2_md.v1",
            "run_report_md": "run_report_md.v1",
        },
        "empty_states": {
            "manifest": False,
            "evidence_packs": False,
            "opportunity_candidates": False,
            "quality_gate_decisions": False,
            "founder_decisions_v2": True,
            "founder_feedback_mappings": True,
            "founder_preference_profile": True,
            "weekly_opportunity_review": False,
            "next_best_actions": False,
            "parking_lot_records": True,
            "run_report": False,
            "founder_inbox_v2_index": False,
            "founder_inbox_v2_md": False,
            "run_report_md": False,
        },
        "advisory_only": True,
        "no_live_api": True,
        "no_live_llm": True,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Evidence packs placeholder
    (run_dir / "evidence_packs.json").write_text(
        json.dumps({"items": [], "schema_version": "evidence_pack.v1", "empty": True}, indent=2),
        encoding="utf-8",
    )

    # Opportunity candidates placeholder
    (run_dir / "opportunity_candidates.json").write_text(
        json.dumps({"items": [], "schema_version": "opportunity_sketch.v1", "empty": True}, indent=2),
        encoding="utf-8",
    )

    # Quality gate decisions placeholder
    (run_dir / "quality_gate_decisions.json").write_text(
        json.dumps({"items": [], "schema_version": "opportunity_quality_gate.v1", "empty": True}, indent=2),
        encoding="utf-8",
    )

    # Founder decisions v2
    if existing_decisions:
        (run_dir / "founder_decisions_v2.json").write_text(
            json.dumps({
                "items": existing_decisions,
                "schema_version": "founder_decision_v2.v1",
                "empty": len(existing_decisions) == 0,
            }, indent=2),
            encoding="utf-8",
        )
    else:
        (run_dir / "founder_decisions_v2.json").write_text(
            json.dumps({
                "items": [],
                "schema_version": "founder_decision_v2.v1",
                "empty": True,
                "note": "Founder decisions are imported separately.",
            }, indent=2),
            encoding="utf-8",
        )

    # Feedback mappings placeholder
    (run_dir / "founder_feedback_mappings.json").write_text(
        json.dumps({"items": [], "schema_version": "founder_feedback_mapping.v1", "empty": True}, indent=2),
        encoding="utf-8",
    )

    # Preference profile placeholder
    (run_dir / "founder_preference_profile.json").write_text(
        json.dumps({
            "profile_id": "empty_profile",
            "preferred_pain_types": [],
            "rejected_patterns": [],
            "promoted_patterns": [],
            "recurring_kill_reasons": [],
            "areas_needing_more_evidence": [],
            "source_decision_ids": [],
            "source_feedback_mapping_ids": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "decision_count": 0,
            "promote_count": 0,
            "park_count": 0,
            "kill_count": 0,
            "revisit_count": 0,
            "needs_more_evidence_count": 0,
            "schema_version": "founder_preference_profile.v1",
            "ml_training_claimed": False,
            "autonomous_decisions_made": False,
            "empty": True,
        }, indent=2),
        encoding="utf-8",
    )

    # Weekly opportunity review placeholder
    (run_dir / "weekly_opportunity_review.json").write_text(
        json.dumps({"package_id": "test", "schema_version": "weekly_opportunity_review.v1", "sections": []}, indent=2),
        encoding="utf-8",
    )

    # Next best actions placeholder
    (run_dir / "next_best_actions.json").write_text(
        json.dumps({"items": [], "schema_version": "founder_action.v1", "empty": True}, indent=2),
        encoding="utf-8",
    )

    # Parking lot placeholder
    (run_dir / "parking_lot_records.json").write_text(
        json.dumps({"items": [], "schema_version": "parking_lot.v1", "empty": True}, indent=2),
        encoding="utf-8",
    )

    # Run report placeholder
    (run_dir / "run_report.json").write_text(
        json.dumps({"run_id": run_id, "placeholder": True}, indent=2),
        encoding="utf-8",
    )

    # Inbox index
    if with_inbox:
        items = inbox_items or [
            _make_inbox_item("inbox_review_001"),
            _make_inbox_item("inbox_review_002"),
            _make_inbox_item("inbox_review_003"),
        ]
        inbox_index = _make_minimal_inbox_index(items)
        (run_dir / "founder_inbox_v2_index.json").write_text(
            json.dumps(inbox_index, indent=2),
            encoding="utf-8",
        )
        # Inbox markdown placeholder
        (run_dir / "founder_inbox_v2.md").write_text("# Founder Inbox v2\n\nPlaceholder.\n", encoding="utf-8")
        # Run report markdown placeholder
        (run_dir / "run_report.md").write_text("# Run Report\n\nPlaceholder.\n", encoding="utf-8")

    return run_dir


# ---------------------------------------------------------------------------
# Tests: Unit helpers
# ---------------------------------------------------------------------------


class TestLoadFounderDecisionInputs(unittest.TestCase):
    """Tests for load_founder_decision_inputs()."""

    def test_load_json_array(self):
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
            {"review_item_id": "inbox_review_002", "decision": "KILL", "reason_categories": ["too_generic"]},
        ]
        path = _make_temp_decisions_file(decisions)
        try:
            result = load_founder_decision_inputs(path)
            self.assertIsInstance(result, FounderDecisionImportInput)
            self.assertEqual(len(result.decisions), 2)
        finally:
            path.unlink(missing_ok=True)

    def test_load_jsonl(self):
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
            {"review_item_id": "inbox_review_002", "decision": "KILL", "reason_categories": ["too_generic"]},
        ]
        path = _make_temp_jsonl_decisions_file(decisions)
        try:
            result = load_founder_decision_inputs(path)
            self.assertIsInstance(result, FounderDecisionImportInput)
            self.assertEqual(len(result.decisions), 2)
        finally:
            path.unlink(missing_ok=True)

    def test_load_single_object(self):
        decisions = {"review_item_id": "inbox_review_001", "decision": "PARK"}
        path = _make_temp_decisions_file(decisions)  # writes an object, not array
        try:
            result = load_founder_decision_inputs(path)
            self.assertEqual(len(result.decisions), 1)
        finally:
            path.unlink(missing_ok=True)

    def test_load_empty_array_fails(self):
        path = _make_temp_decisions_file([])
        try:
            with self.assertRaises(ValueError):
                load_founder_decision_inputs(path)
        finally:
            path.unlink(missing_ok=True)

    def test_load_missing_file_fails(self):
        path = Path(tempfile.mkdtemp()) / "nonexistent.json"
        with self.assertRaises(FileNotFoundError):
            load_founder_decision_inputs(path)

    def test_load_empty_file_fails(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".json", mode="w", encoding="utf-8", delete=False)
        tmp.write("")
        tmp.close()
        path = Path(tmp.name)
        try:
            with self.assertRaises(ValueError):
                load_founder_decision_inputs(path)
        finally:
            path.unlink(missing_ok=True)

    def test_load_malformed_json_fails(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".json", mode="w", encoding="utf-8", delete=False)
        tmp.write("{malformed")
        tmp.close()
        path = Path(tmp.name)
        try:
            with self.assertRaises(ValueError):
                load_founder_decision_inputs(path)
        finally:
            path.unlink(missing_ok=True)

    def test_load_malformed_jsonl_fails(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", encoding="utf-8", delete=False)
        tmp.write('{"valid": true}\n{not valid json}\n')
        tmp.close()
        path = Path(tmp.name)
        try:
            with self.assertRaises(ValueError):
                load_founder_decision_inputs(path)
        finally:
            path.unlink(missing_ok=True)


class TestValidateFounderDecisionInputs(unittest.TestCase):
    """Tests for validate_founder_decision_inputs()."""

    def test_valid_decisions_pass(self):
        inbox = _make_minimal_inbox_index([
            _make_inbox_item("inbox_review_001"),
            _make_inbox_item("inbox_review_002"),
        ])
        inputs = FounderDecisionImportInput(decisions=[
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
            {"review_item_id": "inbox_review_002", "decision": "PROMOTE", "reason_categories": ["strong_pain", "clear_buyer"]},
        ])
        valid, errors = validate_founder_decision_inputs(inputs, inbox)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(valid), 2)

    def test_unknown_review_item_id_fails_closed(self):
        inbox = _make_minimal_inbox_index([
            _make_inbox_item("inbox_review_001"),
        ])
        inputs = FounderDecisionImportInput(decisions=[
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
            {"review_item_id": "inbox_review_unknown", "decision": "PARK", "reason_categories": ["weak_evidence"]},
        ])
        valid, errors = validate_founder_decision_inputs(inputs, inbox)
        self.assertGreater(len(errors), 0)
        self.assertEqual(len(valid), 0)  # fail-closed

    def test_duplicate_review_item_id_fails_closed(self):
        inbox = _make_minimal_inbox_index([
            _make_inbox_item("inbox_review_001"),
        ])
        inputs = FounderDecisionImportInput(decisions=[
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
            {"review_item_id": "inbox_review_001", "decision": "KILL", "reason_categories": ["too_generic"]},
        ])
        valid, errors = validate_founder_decision_inputs(inputs, inbox)
        self.assertGreater(len(errors), 0)
        self.assertEqual(len(valid), 0)

    def test_invalid_decision_value_fails_closed(self):
        inbox = _make_minimal_inbox_index([
            _make_inbox_item("inbox_review_001"),
        ])
        inputs = FounderDecisionImportInput(decisions=[
            {"review_item_id": "inbox_review_001", "decision": "INVALID_DECISION", "reason_categories": ["unclear_buyer"]},
        ])
        valid, errors = validate_founder_decision_inputs(inputs, inbox)
        self.assertGreater(len(errors), 0)
        self.assertEqual(len(valid), 0)

    def test_invalid_reason_categories_fails_closed(self):
        inbox = _make_minimal_inbox_index([
            _make_inbox_item("inbox_review_001"),
        ])
        inputs = FounderDecisionImportInput(decisions=[
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["completely_invalid_reason"]},
        ])
        valid, errors = validate_founder_decision_inputs(inputs, inbox)
        self.assertGreater(len(errors), 0)
        self.assertEqual(len(valid), 0)

    def test_missing_reason_categories_fails_closed(self):
        inbox = _make_minimal_inbox_index([
            _make_inbox_item("inbox_review_001"),
        ])
        inputs = FounderDecisionImportInput(decisions=[
            {"review_item_id": "inbox_review_001", "decision": "PARK"},
        ])
        valid, errors = validate_founder_decision_inputs(inputs, inbox)
        self.assertGreater(len(errors), 0)
        self.assertEqual(len(valid), 0)

    def test_mixed_valid_and_invalid_fails_closed(self):
        inbox = _make_minimal_inbox_index([
            _make_inbox_item("inbox_review_001"),
            _make_inbox_item("inbox_review_002"),
        ])
        inputs = FounderDecisionImportInput(decisions=[
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
            {"review_item_id": "inbox_review_002", "decision": "INVALID"},
        ])
        valid, errors = validate_founder_decision_inputs(inputs, inbox)
        self.assertGreater(len(errors), 0)
        self.assertEqual(len(valid), 0)  # fail-closed: one bad -> all rejected

    def test_missing_review_item_id_fails(self):
        inbox = _make_minimal_inbox_index([
            _make_inbox_item("inbox_review_001"),
        ])
        inputs = FounderDecisionImportInput(decisions=[
            {"review_item_id": "", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
        ])
        valid, errors = validate_founder_decision_inputs(inputs, inbox)
        self.assertGreater(len(errors), 0)
        self.assertEqual(len(valid), 0)

    def test_empty_inbox_index_produces_error(self):
        inbox = _make_minimal_inbox_index([])
        inputs = FounderDecisionImportInput(decisions=[
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
        ])
        valid, errors = validate_founder_decision_inputs(inputs, inbox)
        self.assertGreater(len(errors), 0)
        self.assertEqual(len(valid), 0)

    def test_all_decision_values_accepted(self):
        """Test all 5 canonical decision values pass validation."""
        inbox = _make_minimal_inbox_index([
            _make_inbox_item(f"inbox_review_{i:03d}") for i in range(1, 6)
        ])
        decisions_data = [
            ("inbox_review_001", "PROMOTE", ["strong_pain", "clear_buyer"]),
            ("inbox_review_002", "PARK", ["unclear_buyer"]),
            ("inbox_review_003", "KILL", ["too_generic"]),
            ("inbox_review_004", "NEEDS_MORE_EVIDENCE", ["need_customer_voice"]),
            ("inbox_review_005", "REVISIT_LATER", ["waiting_for_more_signals"]),
        ]
        inputs = FounderDecisionImportInput(decisions=[
            {"review_item_id": rid, "decision": dec, "reason_categories": reasons}
            for rid, dec, reasons in decisions_data
        ])
        valid, errors = validate_founder_decision_inputs(inputs, inbox)
        self.assertEqual(len(errors), 0, msg=f"errors: {errors}")
        self.assertEqual(len(valid), 5)

    def test_reject_decision_not_in_item_options(self):
        """If inbox item has restricted decision_options, reject invalid."""
        inbox = _make_minimal_inbox_index([
            _make_inbox_item("inbox_review_001", decision_options=["PARK", "KILL"]),
        ])
        inputs = FounderDecisionImportInput(decisions=[
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE", "reason_categories": ["strong_pain"]},
        ])
        valid, errors = validate_founder_decision_inputs(inputs, inbox)
        self.assertGreater(len(errors), 0)
        self.assertEqual(len(valid), 0)


class TestMergeHelpers(unittest.TestCase):
    """Tests for internal merge/sort helpers."""

    def test_merge_decisions_replace_by_opportunity_id(self):
        d1 = create_founder_decision(
            opportunity_id="opp_1",
            evidence_pack_id="ep_1",
            decision="park",
            reasons=["unclear_buyer"],
            linked_source_urls=["https://example.com/opp_1"],
        )
        d2 = create_founder_decision(
            opportunity_id="opp_1",
            evidence_pack_id="ep_1",
            decision="kill",
            reasons=["too_generic"],
            linked_source_urls=["https://example.com/opp_1"],
        )
        merged = _merge_decisions([d1], [d2])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].decision, "kill")

    def test_merge_decisions_new_added(self):
        d1 = create_founder_decision(
            opportunity_id="opp_1",
            evidence_pack_id="ep_1",
            decision="park",
            reasons=["unclear_buyer"],
            linked_source_urls=["https://example.com/opp_1"],
        )
        d2 = create_founder_decision(
            opportunity_id="opp_2",
            evidence_pack_id="ep_2",
            decision="kill",
            reasons=["too_generic"],
            linked_source_urls=["https://example.com/opp_2"],
        )
        merged = _merge_decisions([d1], [d2])
        self.assertEqual(len(merged), 2)

    def test_safe_string_list_filters_empty(self):
        result = _safe_string_list(["a", "", "b", None, "  "])
        self.assertEqual(result, ["a", "b"])

    def test_extract_reason_categories_list(self):
        result = _extract_reason_categories(["unclear_buyer", "weak_evidence"])
        self.assertEqual(result, ["unclear_buyer", "weak_evidence"])

    def test_extract_reason_categories_none(self):
        result = _extract_reason_categories(None)
        self.assertEqual(result, [])

    def test_extract_reason_categories_comma_string(self):
        result = _extract_reason_categories("unclear_buyer, weak_evidence")
        self.assertEqual(result, ["unclear_buyer", "weak_evidence"])

    def test_dedupe_sorted(self):
        result = _dedupe_sorted(["b", "a", "b", "c"])
        self.assertEqual(result, ["a", "b", "c"])


# ---------------------------------------------------------------------------
# Tests: Full import function
# ---------------------------------------------------------------------------


class TestImportFounderDecisions(unittest.TestCase):
    """End-to-end tests for import_founder_decisions()."""

    def setUp(self):
        self.tmp_root = Path(tempfile.mkdtemp())
        self.run_id = "weekly_run_2026_01_01_test0001"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _make_run(self, **kwargs):
        return _build_mock_weekly_run(self.tmp_root, self.run_id, **kwargs)

    def test_valid_import_writes_founder_decisions_json(self):
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"], "notes": "Need more buyer examples"},
            {"review_item_id": "inbox_review_002", "decision": "KILL", "reason_categories": ["too_generic"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed, msg=f"errors: {result.errors}")
            self.assertEqual(result.imported_count, 2)
            self.assertEqual(result.rejected_count, 0)
            self.assertTrue(result.advisory_only)
            self.assertTrue(result.no_live_api)
            self.assertTrue(result.no_live_llm)

            # Check file was written
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            decisions_path = run_dir / "founder_decisions_v2.json"
            self.assertTrue(decisions_path.is_file())
            data = json.loads(decisions_path.read_text(encoding="utf-8"))
            self.assertEqual(len(data["items"]), 2)
            self.assertTrue(data["imported"])
        finally:
            dec_file.unlink(missing_ok=True)

    def test_valid_import_writes_feedback_mappings_json(self):
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            mappings_path = run_dir / "founder_feedback_mappings.json"
            self.assertTrue(mappings_path.is_file())
            data = json.loads(mappings_path.read_text(encoding="utf-8"))
            self.assertEqual(len(data["items"]), 1)
        finally:
            dec_file.unlink(missing_ok=True)

    def test_valid_import_writes_preference_profile_json(self):
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE", "reason_categories": ["strong_pain", "clear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            profile_path = run_dir / "founder_preference_profile.json"
            self.assertTrue(profile_path.is_file())
            data = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertEqual(data["decision_count"], 1)
            self.assertEqual(data["promote_count"], 1)
        finally:
            dec_file.unlink(missing_ok=True)

    def test_valid_import_updates_manifest_empty_states(self):
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            empty_states = manifest["empty_states"]
            self.assertFalse(empty_states["founder_decisions_v2"])
            self.assertFalse(empty_states["founder_feedback_mappings"])
            self.assertFalse(empty_states["founder_preference_profile"])
        finally:
            dec_file.unlink(missing_ok=True)

    def test_unknown_review_item_id_fails_closed(self):
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
            {"review_item_id": "inbox_review_nonexistent", "decision": "KILL", "reason_categories": ["too_generic"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertFalse(result.validation_passed)
            self.assertGreater(len(result.errors), 0)
            # Verify no artifacts were partially written (fail-closed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            decisions_path = run_dir / "founder_decisions_v2.json"
            if decisions_path.is_file():
                data = json.loads(decisions_path.read_text(encoding="utf-8"))
                # should still show empty (not updated)
                self.assertTrue(data.get("empty", True) or len(data.get("items", [])) == 0)
        finally:
            dec_file.unlink(missing_ok=True)

    def test_import_is_idempotent(self):
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result1 = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result1.validation_passed)

            # Now try importing again — should reject duplicate
            dec_file2 = _make_temp_decisions_file(decisions)
            try:
                result2 = import_founder_decisions(self.tmp_root, self.run_id, dec_file2)
                self.assertFalse(result2.validation_passed)
                self.assertGreater(len(result2.errors), 0)
                # Should not have duplicated
            finally:
                dec_file2.unlink(missing_ok=True)
        finally:
            dec_file.unlink(missing_ok=True)

    def test_import_same_file_twice_is_stable(self):
        """Re-running with same decisions file should produce stable output."""
        self._make_run()
        # Use a fresh run_id so there are no existing decisions
        run_id2 = "weekly_run_2026_01_02_test0002"
        _build_mock_weekly_run(self.tmp_root, run_id2)
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result1 = import_founder_decisions(self.tmp_root, run_id2, dec_file)
            self.assertTrue(result1.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / run_id2
            data1 = json.loads((run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8"))
        finally:
            dec_file.unlink(missing_ok=True)

        # Rebuild clean and re-import
        # Remove old run dir and rebuild
        import shutil
        shutil.rmtree(run_dir, ignore_errors=True)
        _build_mock_weekly_run(self.tmp_root, run_id2)

        dec_file2 = _make_temp_decisions_file(decisions)
        try:
            result2 = import_founder_decisions(self.tmp_root, run_id2, dec_file2)
            self.assertTrue(result2.validation_passed)
            data2 = json.loads((run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8"))
        finally:
            dec_file2.unlink(missing_ok=True)

        # Same number of items
        self.assertEqual(len(data1["items"]), len(data2["items"]))

    def test_preserves_inbox_traceability_ids(self):
        self._make_run()
        decisions = [
            {
                "review_item_id": "inbox_review_001",
                "decision": "PARK",
                "reason_categories": ["unclear_buyer"],
                "notes": "Test",
            },
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            data = json.loads((run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8"))
            item = data["items"][0]
            self.assertEqual(item["opportunity_id"], "opp_inbox_review_001")
            self.assertEqual(item["evidence_pack_id"], "ep_inbox_review_001")
            self.assertIn("ev_inbox_review_001", item["linked_evidence_ids"])
            self.assertIn("qg_inbox_review_001", item["linked_source_signal_ids"])
            # Source URLs from inbox linked_source_urls are propagated
            self.assertIn("https://example.com/inbox_review_001", item["linked_source_urls"])
        finally:
            dec_file.unlink(missing_ok=True)

    def test_source_urls_propagate_to_founder_decision(self):
        """Source URLs from inbox linked_source_urls appear in FounderDecisionV2."""
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed, msg=f"errors: {result.errors}")
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            data = json.loads((run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8"))
            item = data["items"][0]
            self.assertEqual(item["linked_source_urls"], ["https://example.com/inbox_review_001"])
        finally:
            dec_file.unlink(missing_ok=True)

    def test_source_urls_propagate_to_feedback_mapping(self):
        """Source URLs from inbox linked_source_urls appear in FounderFeedbackMapping."""
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            data = json.loads((run_dir / "founder_feedback_mappings.json").read_text(encoding="utf-8"))
            item = data["items"][0]
            self.assertEqual(item["source_urls"], ["https://example.com/inbox_review_001"])
            self.assertEqual(item["target"]["source_urls"], ["https://example.com/inbox_review_001"])
        finally:
            dec_file.unlink(missing_ok=True)

    def test_no_placeholder_urn_in_imported_artifacts(self):
        """No urn:oos:* appears in any import-created artifacts."""
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
            {"review_item_id": "inbox_review_002", "decision": "KILL", "reason_categories": ["too_generic"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            # Check all import-written files for placeholder URNs
            for filename in ["founder_decisions_v2.json", "founder_feedback_mappings.json",
                              "founder_preference_profile.json", "parking_lot_records.json"]:
                path = run_dir / filename
                if path.is_file():
                    content = path.read_text(encoding="utf-8")
                    self.assertNotIn("urn:oos:", content,
                        f"Found urn:oos:* placeholder in {filename}")
                    self.assertNotIn("urn:oos:founder_import:placeholder", content,
                        f"Found placeholder in {filename}")
        finally:
            dec_file.unlink(missing_ok=True)

    def test_missing_linked_source_urls_non_exempt_fails_closed(self):
        """Import with inbox items that have empty linked_source_urls fails closed."""
        # Build a mock run with an inbox item that has NO linked_source_urls
        inbox_items = [
            _make_inbox_item("inbox_review_001", linked_source_urls=[]),
        ]
        self._make_run(inbox_items=inbox_items)
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            # Should fail closed because empty source_urls on a non-exempt decision
            # violates feedback mapping validation (source_urls must preserve at least one source URL)
            self.assertFalse(result.validation_passed)
            self.assertGreater(len(result.errors), 0)
            # No partial artifacts should exist/change
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            decisions_path = run_dir / "founder_decisions_v2.json"
            if decisions_path.is_file():
                data = json.loads(decisions_path.read_text(encoding="utf-8"))
                self.assertTrue(data.get("empty", True) or len(data.get("items", [])) == 0)
        finally:
            dec_file.unlink(missing_ok=True)

    def test_placeholder_urls_filtered_from_inbox_source_urls(self):
        """Placeholder URNs in inbox linked_source_urls are filtered out."""
        inbox_items = [
            _make_inbox_item("inbox_review_001",
                linked_source_urls=["https://real.example.com", "urn:oos:should_be_removed"]),
        ]
        self._make_run(inbox_items=inbox_items)
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE", "reason_categories": ["strong_pain", "clear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed, msg=f"errors: {result.errors}")
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            data = json.loads((run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8"))
            urls = data["items"][0]["linked_source_urls"]
            self.assertIn("https://real.example.com", urls)
            self.assertNotIn("urn:oos:should_be_removed", urls)
            self.assertNotIn("urn:oos:", str(urls))
        finally:
            dec_file.unlink(missing_ok=True)

    def test_multiple_source_urls_deduplicated(self):
        """Duplicate source URLs in inbox linked_source_urls are deduplicated."""
        inbox_items = [
            _make_inbox_item("inbox_review_001",
                linked_source_urls=["https://example.com/a", "https://example.com/b", "https://example.com/a"]),
        ]
        self._make_run(inbox_items=inbox_items)
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            data = json.loads((run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8"))
            urls = data["items"][0]["linked_source_urls"]
            self.assertEqual(len(urls), 2)
            self.assertEqual(urls, sorted(urls))
        finally:
            dec_file.unlink(missing_ok=True)

    def test_taxonomy_rejects_placeholder_urns(self):
        """FounderDecisionV2 validation rejects urn:oos:* in linked_source_urls."""
        from oos.founder_decision_taxonomy import create_founder_decision
        with self.assertRaises(ValueError) as ctx:
            create_founder_decision(
                opportunity_id="opp_test",
                evidence_pack_id="ep_test",
                decision="park",
                reasons=["unclear_buyer"],
                linked_source_urls=["urn:oos:founder_import:placeholder"],
            )
        self.assertIn("placeholder URNs", str(ctx.exception))

    def test_feedback_mapping_rejects_placeholder_urns(self):
        """FounderFeedbackMapping validation rejects urn:oos:* in source_urls."""
        from oos.founder_feedback_mapping import (
            FounderFeedbackMapping, FounderFeedbackTarget, FounderFeedbackSignalImpact,
            make_founder_feedback_mapping_id,
        )
        target = FounderFeedbackTarget(
            opportunity_id="opp_test",
            evidence_pack_id="ep_test",
            cluster_id="unknown",
            evidence_ids=["e1"],
            source_signal_ids=["s1"],
            source_urls=["urn:oos:placeholder"],
        )
        mapping = FounderFeedbackMapping(
            mapping_id=make_founder_feedback_mapping_id(
                decision_id="d1", opportunity_id="opp_test",
                evidence_pack_id="ep_test", cluster_id="unknown",
            ),
            decision_id="d1",
            opportunity_id="opp_test",
            evidence_pack_id="ep_test",
            cluster_id="unknown",
            evidence_ids=["e1"],
            source_signal_ids=["s1"],
            source_urls=["urn:oos:placeholder"],
            decision="park",
            reasons=["unclear_buyer"],
            feedback_tags=["parked_pattern"],
            signal_impact="needs_more_evidence",
            recommended_future_handling=["park_similar_until_more_evidence"],
            target=target,
            impact_detail=FounderFeedbackSignalImpact(
                impact="needs_more_evidence",
                feedback_tags=["parked_pattern"],
                recommended_future_handling=["park_similar_until_more_evidence"],
                reason_categories=["unclear_buyer"],
            ),
        )
        with self.assertRaises(ValueError) as ctx:
            mapping.validate()
        self.assertIn("placeholder URNs", str(ctx.exception))

    def test_jsonl_input_supported(self):
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
            {"review_item_id": "inbox_review_002", "decision": "KILL", "reason_categories": ["too_generic"]},
        ]
        dec_file = _make_temp_jsonl_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed)
            self.assertEqual(result.imported_count, 2)
        finally:
            dec_file.unlink(missing_ok=True)

    def test_missing_run_id_fails(self):
        result = import_founder_decisions(
            self.tmp_root,
            "nonexistent_run",
            Path("dummy.json"),
        )
        self.assertFalse(result.validation_passed)
        self.assertIn("Run directory not found", result.errors[0])

    def test_missing_inbox_index_fails(self):
        run_dir = _build_mock_weekly_run(self.tmp_root, self.run_id, with_inbox=False)
        decisions = [{"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]}]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertFalse(result.validation_passed)
            self.assertIn("not found", result.errors[0])
        finally:
            dec_file.unlink(missing_ok=True)

    def test_parking_lot_records_created_for_park(self):
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed)
            self.assertIn("parking_lot_records", result.artifacts_updated)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            pl_data = json.loads((run_dir / "parking_lot_records.json").read_text(encoding="utf-8"))
            self.assertTrue(len(pl_data["items"]) >= 1)
        finally:
            dec_file.unlink(missing_ok=True)

    def test_parking_lot_records_created_for_revisit_later(self):
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "REVISIT_LATER", "reason_categories": ["waiting_for_more_signals"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            pl_data = json.loads((run_dir / "parking_lot_records.json").read_text(encoding="utf-8"))
            self.assertTrue(len(pl_data["items"]) >= 1)
        finally:
            dec_file.unlink(missing_ok=True)

    def test_result_serializes_to_json(self):
        result = FounderDecisionImportResult(
            run_id="test", imported_count=3, rejected_count=1,
            errors=[], warnings=["test warning"],
            artifacts_updated=["founder_decisions_v2"],
            validation_passed=True,
        )
        d = result.to_dict()
        self.assertEqual(d["imported_count"], 3)
        self.assertEqual(d["rejected_count"], 1)
        self.assertTrue(d["advisory_only"])
        self.assertTrue(d["no_live_api"])
        self.assertTrue(d["no_live_llm"])

    def test_advisory_flags_always_true(self):
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK", "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertTrue(result.advisory_only)
            self.assertTrue(result.no_live_api)
            self.assertTrue(result.no_live_llm)
            self.assertEqual(result.schema_version, "founder_decision_import.v1")
        finally:
            dec_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Tests: Default behavior preservation (v2.8 item 1.3 — safety)
# ---------------------------------------------------------------------------


class TestDefaultRejectOnReimportPreserved(unittest.TestCase):
    """Default behavior: re-import without flags still fails closed."""

    def setUp(self):
        self.tmp_root = Path(tempfile.mkdtemp())
        self.run_id = "weekly_run_test_replace_default"

    def tearDown(self):
        _safe_rmtree(self.tmp_root)

    def _make_run(self, with_existing_decisions: bool = False):
        items = [
            _make_inbox_item("inbox_review_001"),
            _make_inbox_item("inbox_review_002"),
        ]
        if with_existing_decisions:
            existing = [
                {
                    "decision_id": "fd_opp_inbox_review_001",
                    "opportunity_id": "opp_inbox_review_001",
                    "evidence_pack_id": "ep_inbox_review_001",
                    "decision": "park",
                    "reasons": [{"category": "unclear_buyer", "note": ""}],
                    "notes": "Initial decision",
                    "confidence": 0.9,
                    "linked_evidence_ids": ["ev_inbox_review_001"],
                    "linked_source_signal_ids": ["sig_inbox_review_001"],
                    "linked_source_urls": ["https://example.com/inbox_review_001"],
                    "decided_by": "founder",
                    "decided_at": "2026-05-01T10:00:00Z",
                    "schema_version": "founder_decision_v2.v1",
                    "auto_promote": False,
                    "founder_decision_authority": "founder_decision_record_only",
                }
            ]
        else:
            existing = None
        _build_mock_weekly_run(
            self.tmp_root, self.run_id,
            inbox_items=items,
            existing_decisions=existing,
        )

    def test_default_reimport_without_flags_still_fails_closed(self):
        """Without any correction flags, duplicate reimport is still rejected."""
        self._make_run(with_existing_decisions=True)
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE",
             "reason_categories": ["strong_pain"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertFalse(result.validation_passed)
            self.assertIn("idempotent", result.errors[0] if result.errors else "")
        finally:
            dec_file.unlink(missing_ok=True)

    def test_duplicate_rid_still_rejected_by_default(self):
        """Duplicate review_item_id (no correction flags) still rejected."""
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK",
             "reason_categories": ["unclear_buyer"]},
            {"review_item_id": "inbox_review_001", "decision": "KILL",
             "reason_categories": ["too_generic"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertFalse(result.validation_passed)
            self.assertIn("duplicate", result.errors[0] if result.errors else "")
        finally:
            dec_file.unlink(missing_ok=True)

    def test_unknown_rid_still_rejected(self):
        """Unknown review_item_id still rejected without correction flags."""
        self._make_run()
        decisions = [
            {"review_item_id": "nonexistent_rid", "decision": "PARK",
             "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertFalse(result.validation_passed)
            self.assertIn("not found", result.errors[0] if result.errors else "")
        finally:
            dec_file.unlink(missing_ok=True)

    def test_invalid_decision_still_rejected(self):
        """Invalid decision value still rejected without correction flags."""
        self._make_run()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "INVALID",
             "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(self.tmp_root, self.run_id, dec_file)
            self.assertFalse(result.validation_passed)
        finally:
            dec_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Tests: Replace mode
# ---------------------------------------------------------------------------


class TestReplaceMode(unittest.TestCase):
    """Replace mode tests (v2.8 item 1.3)."""

    def setUp(self):
        self.tmp_root = Path(tempfile.mkdtemp())
        self.run_id = "weekly_run_test_replace_mode"

    def tearDown(self):
        _safe_rmtree(self.tmp_root)

    def _make_run_with_decisions(self, decisions: list[dict] | None = None):
        items = [
            _make_inbox_item("inbox_review_001"),
            _make_inbox_item("inbox_review_002"),
            _make_inbox_item("inbox_review_003"),
        ]
        existing = decisions or [
            {
                "decision_id": "fd_opp_inbox_review_001",
                "opportunity_id": "opp_inbox_review_001",
                "evidence_pack_id": "ep_inbox_review_001",
                "review_item_id": "inbox_review_001",
                "decision": "park",
                "reasons": [{"category": "unclear_buyer", "note": ""}],
                "notes": "Initial decision",
                "confidence": 0.9,
                "linked_evidence_ids": ["ev_inbox_review_001"],
                "linked_source_signal_ids": ["sig_inbox_review_001"],
                "linked_source_urls": ["https://example.com/inbox_review_001"],
                "decided_by": "founder",
                "decided_at": "2026-05-01T10:00:00Z",
                "schema_version": "founder_decision_v2.v1",
                "auto_promote": False,
                "founder_decision_authority": "founder_decision_record_only",
            },
            {
                "decision_id": "fd_opp_inbox_review_002",
                "opportunity_id": "opp_inbox_review_002",
                "evidence_pack_id": "ep_inbox_review_002",
                "review_item_id": "inbox_review_002",
                "decision": "kill",
                "reasons": [{"category": "too_generic", "note": ""}],
                "notes": "Killed for being generic.",
                "confidence": 0.9,
                "linked_evidence_ids": ["ev_inbox_review_002"],
                "linked_source_signal_ids": ["sig_inbox_review_002"],
                "linked_source_urls": ["https://example.com/inbox_review_002"],
                "decided_by": "founder",
                "decided_at": "2026-05-01T10:01:00Z",
                "schema_version": "founder_decision_v2.v1",
                "auto_promote": False,
                "founder_decision_authority": "founder_decision_record_only",
            },
        ]
        _build_mock_weekly_run(
            self.tmp_root, self.run_id,
            inbox_items=items,
            existing_decisions=existing,
        )

    def test_replace_mode_succeeds_for_listed_rid(self):
        """Replace mode succeeds for explicitly listed existing review_item_id."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE",
             "reason_categories": ["strong_pain"], "notes": "Re-evaluated — promoting."},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                replace_review_item_ids=["inbox_review_001"],
            )
            self.assertTrue(result.validation_passed, f"Errors: {result.errors}")
            self.assertEqual(result.imported_count, 1)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            data = json.loads((run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8"))
            decisions_list = data["items"]
            self.assertEqual(len(decisions_list), 2)
            # Verify the replaced one is now PROMOTE
            opp_001 = [d for d in decisions_list if d["opportunity_id"] == "opp_inbox_review_001"]
            self.assertEqual(len(opp_001), 1)
            self.assertEqual(opp_001[0]["decision"], "promote")
            # Verify the other one is untouched
            opp_002 = [d for d in decisions_list if d["opportunity_id"] == "opp_inbox_review_002"]
            self.assertEqual(len(opp_002), 1)
            self.assertEqual(opp_002[0]["decision"], "kill")
        finally:
            dec_file.unlink(missing_ok=True)

    def test_replace_mode_rejects_rid_not_in_replace_list(self):
        """Replace mode rejects incoming rid not in --replace-review-items."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE",
             "reason_categories": ["strong_pain"]},
            {"review_item_id": "inbox_review_003", "decision": "PARK",
             "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                replace_review_item_ids=["inbox_review_001"],
            )
            self.assertFalse(result.validation_passed)
            self.assertIn("not in --replace-review-items", result.errors[0] if result.errors else "")
        finally:
            dec_file.unlink(missing_ok=True)

    def test_replace_mode_rejects_nonexisting_rid(self):
        """Replace mode rejects review_item_id with no existing decision."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_003", "decision": "PARK",
             "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                replace_review_item_ids=["inbox_review_003"],
            )
            self.assertFalse(result.validation_passed)
            self.assertIn("no existing decision", result.errors[0] if result.errors else "")
        finally:
            dec_file.unlink(missing_ok=True)

    def test_replace_mode_preserves_unrelated_decisions(self):
        """Replace mode keeps unrelated existing decisions untouched."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE",
             "reason_categories": ["strong_pain"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                replace_review_item_ids=["inbox_review_001"],
            )
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            data = json.loads((run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8"))
            # second decision must still be "kill"
            opp_002 = [d for d in data["items"] if d["opportunity_id"] == "opp_inbox_review_002"]
            self.assertEqual(len(opp_002), 1)
            self.assertEqual(opp_002[0]["decision"], "kill")
            self.assertEqual(opp_002[0]["notes"], "Killed for being generic.")
        finally:
            dec_file.unlink(missing_ok=True)

    def test_replace_mode_rebuilds_feedback_mappings(self):
        """Replace mode rebuilds feedback mappings."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE",
             "reason_categories": ["strong_pain"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                replace_review_item_ids=["inbox_review_001"],
            )
            self.assertTrue(result.validation_passed)
            self.assertIn("founder_feedback_mappings", result.artifacts_updated)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            fb_data = json.loads((run_dir / "founder_feedback_mappings.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(fb_data["items"]), 2)
        finally:
            dec_file.unlink(missing_ok=True)

    def test_replace_mode_rebuilds_preference_profile(self):
        """Replace mode rebuilds preference profile."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE",
             "reason_categories": ["strong_pain"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                replace_review_item_ids=["inbox_review_001"],
            )
            self.assertTrue(result.validation_passed)
            self.assertIn("founder_preference_profile", result.artifacts_updated)
        finally:
            dec_file.unlink(missing_ok=True)

    def test_replace_mode_preserves_real_source_urls(self):
        """Replace mode preserves real source URLs."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "KILL",
             "reason_categories": ["too_generic"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                replace_review_item_ids=["inbox_review_001"],
            )
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            data = json.loads((run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8"))
            for item in data["items"]:
                urls = item.get("linked_source_urls", [])
                self.assertTrue(len(urls) >= 1, f"No source URLs for {item['decision_id']}")
                for url in urls:
                    self.assertTrue(url.startswith("https://"), f"Expected https:// URL, got {url}")
        finally:
            dec_file.unlink(missing_ok=True)

    def test_replace_mode_rejects_placeholder_urn(self):
        """Replace mode rejects urn:oos:* placeholder URLs in incoming decisions."""
        items = [
            _make_inbox_item("inbox_review_001", linked_source_urls=["urn:oos:placeholder"]),
            _make_inbox_item("inbox_review_002"),
        ]
        existing = [
            {
                "decision_id": "fd_opp_inbox_review_001",
                "opportunity_id": "opp_inbox_review_001",
                "evidence_pack_id": "ep_inbox_review_001",
                "review_item_id": "inbox_review_001",
                "decision": "park",
                "reasons": [{"category": "unclear_buyer", "note": ""}],
                "notes": "Initial",
                "confidence": 0.9,
                "linked_evidence_ids": ["ev_inbox_review_001"],
                "linked_source_signal_ids": ["sig_inbox_review_001"],
                "linked_source_urls": ["https://example.com/inbox_review_001"],
                "decided_by": "founder",
                "decided_at": "2026-05-01T10:00:00Z",
                "schema_version": "founder_decision_v2.v1",
                "auto_promote": False,
                "founder_decision_authority": "founder_decision_record_only",
            }
        ]
        _build_mock_weekly_run(
            self.tmp_root, self.run_id,
            inbox_items=items,
            existing_decisions=existing,
        )
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "KILL",
             "reason_categories": ["too_generic"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                replace_review_item_ids=["inbox_review_001"],
            )
            self.assertFalse(result.validation_passed)
        finally:
            dec_file.unlink(missing_ok=True)

    def test_replace_mode_writes_import_history(self):
        """Replace mode writes import_history.json."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE",
             "reason_categories": ["strong_pain"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                replace_review_item_ids=["inbox_review_001"],
            )
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            hist_path = run_dir / "import_history.json"
            self.assertTrue(hist_path.is_file(), "import_history.json not written")
            hist = json.loads(hist_path.read_text(encoding="utf-8"))
            self.assertEqual(hist["schema_version"], "import_history.v1")
            self.assertGreaterEqual(len(hist["entries"]), 1)
            entry = hist["entries"][0]
            self.assertEqual(entry["correction_mode"], "replace")
            self.assertTrue(entry["advisory_only"])
            self.assertTrue(entry["no_live_api"])
            self.assertTrue(entry["no_live_llm"])
        finally:
            dec_file.unlink(missing_ok=True)

    def test_replace_mode_is_deterministic(self):
        """Replace mode with identical input yields identical artifact state."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE",
             "reason_categories": ["strong_pain"]},
        ]

        # First replace
        dec_file1 = _make_temp_decisions_file(decisions)
        try:
            result1 = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file1,
                replace_review_item_ids=["inbox_review_001"],
            )
            self.assertTrue(result1.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            content1 = (run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8")
        finally:
            dec_file1.unlink(missing_ok=True)

        # Reset and do again
        self.tearDown()
        self.setUp()
        self._make_run_with_decisions()
        dec_file2 = _make_temp_decisions_file(decisions)
        try:
            result2 = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file2,
                replace_review_item_ids=["inbox_review_001"],
            )
            self.assertTrue(result2.validation_passed)
            run_dir2 = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            content2 = (run_dir2 / "founder_decisions_v2.json").read_text(encoding="utf-8")
        finally:
            dec_file2.unlink(missing_ok=True)

        # Compare decisions list (ignore timestamps in notes)
        items1 = json.loads(content1)["items"]
        items2 = json.loads(content2)["items"]
        self.assertEqual(len(items1), len(items2))
        for i1, i2 in zip(items1, items2):
            self.assertEqual(i1["decision"], i2["decision"])
            self.assertEqual(i1["decision_id"], i2["decision_id"])
            self.assertEqual(sorted(i1.get("linked_source_urls", [])),
                             sorted(i2.get("linked_source_urls", [])))

    def test_replace_mode_failure_no_partial_artifacts(self):
        """Replace mode failure writes no partial artifacts."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE",
             "reason_categories": ["strong_pain"]},
            {"review_item_id": "inbox_review_099", "decision": "PARK",
             "reason_categories": ["unclear_buyer"]},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                replace_review_item_ids=["inbox_review_001", "inbox_review_099"],
            )
            self.assertFalse(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            # Decisions file should be unchanged
            data = json.loads((run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8"))
            self.assertEqual(len(data["items"]), 2)
            opp_001 = [d for d in data["items"] if d["opportunity_id"] == "opp_inbox_review_001"]
            self.assertEqual(opp_001[0]["decision"], "park")
        finally:
            dec_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Tests: Amend mode
# ---------------------------------------------------------------------------


class TestAmendMode(unittest.TestCase):
    """Amend-notes-only mode tests (v2.8 item 1.3)."""

    def setUp(self):
        self.tmp_root = Path(tempfile.mkdtemp())
        self.run_id = "weekly_run_test_amend_mode"

    def tearDown(self):
        _safe_rmtree(self.tmp_root)

    def _make_run_with_decisions(self):
        items = [
            _make_inbox_item("inbox_review_001"),
            _make_inbox_item("inbox_review_002"),
        ]
        existing = [
            {
                "decision_id": "fd_opp_inbox_review_001",
                "opportunity_id": "opp_inbox_review_001",
                "evidence_pack_id": "ep_inbox_review_001",
                "review_item_id": "inbox_review_001",
                "decision": "park",
                "reasons": [{"category": "unclear_buyer", "note": ""}],
                "notes": "Initial notes.",
                "confidence": 0.9,
                "linked_evidence_ids": ["ev_inbox_review_001"],
                "linked_source_signal_ids": ["sig_inbox_review_001"],
                "linked_source_urls": ["https://example.com/inbox_review_001"],
                "decided_by": "founder",
                "decided_at": "2026-05-01T10:00:00Z",
                "schema_version": "founder_decision_v2.v1",
                "auto_promote": False,
                "founder_decision_authority": "founder_decision_record_only",
            },
            {
                "decision_id": "fd_opp_inbox_review_002",
                "opportunity_id": "opp_inbox_review_002",
                "evidence_pack_id": "ep_inbox_review_002",
                "review_item_id": "inbox_review_002",
                "decision": "kill",
                "reasons": [{"category": "too_generic", "note": ""}],
                "notes": "Killed for generic.",
                "confidence": 0.9,
                "linked_evidence_ids": ["ev_inbox_review_002"],
                "linked_source_signal_ids": ["sig_inbox_review_002"],
                "linked_source_urls": ["https://example.com/inbox_review_002"],
                "decided_by": "founder",
                "decided_at": "2026-05-01T10:01:00Z",
                "schema_version": "founder_decision_v2.v1",
                "auto_promote": False,
                "founder_decision_authority": "founder_decision_record_only",
            },
        ]
        _build_mock_weekly_run(
            self.tmp_root, self.run_id,
            inbox_items=items,
            existing_decisions=existing,
        )

    def test_amend_notes_updates_notes(self):
        """Amend-notes-only updates notes field."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK",
             "reason_categories": ["unclear_buyer"],
             "notes": "Updated notes — revised rationale."},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                amend_notes_only=True,
            )
            self.assertTrue(result.validation_passed, f"Errors: {result.errors}")
            self.assertEqual(result.imported_count, 1)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            data = json.loads((run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8"))
            opp_001 = [d for d in data["items"] if d["opportunity_id"] == "opp_inbox_review_001"][0]
            self.assertEqual(opp_001["decision"], "park")
            self.assertIn("Updated notes", opp_001["notes"])
        finally:
            dec_file.unlink(missing_ok=True)

    def test_amend_notes_rejects_decision_value_change(self):
        """Amend-notes-only rejects decision value change."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PROMOTE",
             "reason_categories": ["strong_pain"],
             "notes": "Changed my mind — promoting."},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                amend_notes_only=True,
            )
            self.assertFalse(result.validation_passed)
            self.assertIn("cannot change decision", result.errors[0] if result.errors else "")
        finally:
            dec_file.unlink(missing_ok=True)

    def test_amend_notes_no_parking_lot_rebuild_unnecessary(self):
        """Amend-notes-only does NOT rebuild parking lot records unnecessarily."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK",
             "reason_categories": ["unclear_buyer"],
             "notes": "Updated notes."},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                amend_notes_only=True,
            )
            self.assertTrue(result.validation_passed)
            # Should NOT include parking_lot_records in artifacts_updated
            self.assertNotIn("parking_lot_records", result.artifacts_updated)
        finally:
            dec_file.unlink(missing_ok=True)

    def test_amend_notes_writes_import_history(self):
        """Amend-notes-only writes import_history.json."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK",
             "reason_categories": ["unclear_buyer"],
             "notes": "Updated rationale for parking."},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                amend_notes_only=True,
            )
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            hist_path = run_dir / "import_history.json"
            self.assertTrue(hist_path.is_file())
            hist = json.loads(hist_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(hist["entries"]), 1)
            entry = hist["entries"][0]
            self.assertEqual(entry["correction_mode"], "amend")
        finally:
            dec_file.unlink(missing_ok=True)

    def test_amend_notes_preserves_source_urls(self):
        """Amend-notes-only preserves existing source URLs."""
        self._make_run_with_decisions()
        decisions = [
            {"review_item_id": "inbox_review_001", "decision": "PARK",
             "reason_categories": ["unclear_buyer"],
             "notes": "Updated notes."},
        ]
        dec_file = _make_temp_decisions_file(decisions)
        try:
            result = import_founder_decisions(
                self.tmp_root, self.run_id, dec_file,
                amend_notes_only=True,
            )
            self.assertTrue(result.validation_passed)
            run_dir = self.tmp_root / "artifacts" / "weekly_runs" / self.run_id
            data = json.loads((run_dir / "founder_decisions_v2.json").read_text(encoding="utf-8"))
            opp_001 = [d for d in data["items"] if d["decision_id"] == "fd_opp_inbox_review_001"][0]
            self.assertEqual(opp_001["linked_source_urls"], ["https://example.com/inbox_review_001"])
        finally:
            dec_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Helper for temp dir cleanup
# ---------------------------------------------------------------------------


def _safe_rmtree(path: Path):
    """Recursively remove a temporary directory tree."""
    try:
        for child in path.glob("**/*"):
            if child.is_file():
                child.unlink(missing_ok=True)
        for child in sorted(path.glob("**/*"), reverse=True):
            if child.is_dir():
                child.rmdir()
        if path.exists():
            path.rmdir()
    except (OSError, PermissionError):
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()
