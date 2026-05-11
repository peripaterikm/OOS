"""Tests for correction_undo — undo-last validation and behavior.

Roadmap v2.10 item 3.1 substep A: focused deterministic unit tests.

All tests are deterministic. No live APIs. No live LLMs. No portfolio mutations.
Uses temp directories and inline fixture builders.

Test categories:
 1. missing import_history.json rejected
 2. empty import_history.json rejected
 3. most recent entry already undo rejected
 4. unknown correction_mode rejected
 5. replace_all rejected
 6. missing founder_decisions_v2.json rejected
 7. corrupt founder_decisions_v2.json rejected
 8. missing replaced_decisions archive rejected
 9. corrupt replaced_decisions archive rejected
10. missing amended_decisions archive rejected
11. corrupt amended_decisions archive rejected
12. undo-amend target decision not found rejected
13. undo CorrectionEntry is not appended on failure
14. successful undo-amend restores previous notes
15. successful undo-replace restores archived decisions
16. report/dashboard regeneration failure prevents history append
17. advisory_only is preserved in undo entry
18. source URL traceability failure prevents undo
19. repeat undo does not silently undo more than intended
20. ASCII-safe formatted output for success/failure
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oos.correction_undo import (
    UNDO_LAST_SCHEMA_VERSION,
    UndoResult,
    _append_undo_history_entry,
    _precheck_source_url_traceability,
    format_undo_result_output,
    undo_last_correction,
)
from oos.founder_decision_taxonomy import (
    KILL,
    PARK,
    PROMOTE,
    FounderDecisionV2,
    create_founder_decision,
)

# ---------------------------------------------------------------------------
# Fixture builder helpers
# ---------------------------------------------------------------------------


def _make_decision_dict(
    decision_id: str = "dec_001",
    opportunity_id: str = "opp_001",
    decision: str = PROMOTE,
    notes: str = "original notes",
    linked_source_urls: list[str] | None = None,
    reasons: list[dict] | None = None,
) -> dict:
    """Build a minimal FounderDecisionV2-compatible dict for fixtures."""
    if linked_source_urls is None:
        linked_source_urls = [f"https://example.com/{opportunity_id}"]
    if reasons is None:
        reasons = [{"category": "strong_pain", "note": ""}]
    return {
        "decision_id": decision_id,
        "opportunity_id": opportunity_id,
        "evidence_pack_id": f"ep_{opportunity_id}",
        "decision": decision,
        "reasons": list(reasons),
        "notes": notes,
        "confidence": 0.8,
        "linked_evidence_ids": [f"ev_{opportunity_id}_1"],
        "linked_source_signal_ids": [f"sig_{opportunity_id}_1"],
        "linked_source_urls": list(linked_source_urls),
        "decided_by": "founder",
        "decided_at": "2026-05-01T10:00:00Z",
        "schema_version": "founder_decision_v2.v1",
        "auto_promote": False,
        "founder_decision_authority": "founder_decision_record_only",
    }


def _make_correction_entry(
    correction_id: str = "correction_abc123",
    corrected_at: str = "2026-05-10T14:30:00Z",
    correction_mode: str = "replace",
    old_decision_ids: list[str] | None = None,
    new_decision_ids: list[str] | None = None,
) -> dict:
    """Build a minimal CorrectionEntry dict for import_history.json."""
    return {
        "correction_id": correction_id,
        "corrected_at": corrected_at,
        "correction_mode": correction_mode,
        "replaced_review_item_ids": [],
        "old_decision_ids": old_decision_ids or [],
        "new_decision_ids": new_decision_ids or [],
        "old_artifact_checksums": {},
        "new_artifact_checksums": {},
        "warnings": [],
        "errors": [],
        "advisory_only": True,
        "no_live_api": True,
        "no_live_llm": True,
    }


def _make_minimal_artifact_file(path: Path, empty: bool = True) -> None:
    """Write a minimal empty artifact JSON file."""
    path.write_text(
        json.dumps({"empty": empty, "items": [], "schema_version": "test.v1"}),
        encoding="utf-8",
    )


class FixtureBuilder:
    """Build a temp directory structure suitable for undo_last_correction tests.

    Creates: <tmp>/artifacts/weekly_runs/<run_id>/ with needed files.
    project_root = <tmp>
    """

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.run_id = "run_test_001"
        self.weekly_runs = self.base / "artifacts" / "weekly_runs"
        self.run_dir = self.weekly_runs / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def cleanup(self) -> None:
        self._tmp.cleanup()

    def write_manifest(self, run_id: str | None = None) -> Path:
        rid = run_id or self.run_id
        data = {
            "run_id": rid,
            "run_started_at": "2026-05-01T00:00:00Z",
            "run_completed_at": "2026-05-01T01:00:00Z",
            "schema_versions": {},
            "empty_states": {},
            "advisory_only": True,
        }
        p = self.run_dir / "manifest.json"
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return p

    def write_import_history(self, entries: list[dict]) -> Path:
        data = {
            "schema_version": "import_history.v1",
            "entries": entries,
        }
        p = self.run_dir / "import_history.json"
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return p

    def write_decisions(self, items: list[dict]) -> Path:
        data = {
            "items": items,
            "schema_version": "founder_decision_v2.v1",
            "empty": len(items) == 0,
            "imported": True,
        }
        p = self.run_dir / "founder_decisions_v2.json"
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return p

    def write_replace_archive(
        self,
        decisions: list[dict],
        filename: str = "founder_decisions_v2_replaced_2026-05-10T14_30_00Z.json",
    ) -> Path:
        archive_dir = self.run_dir / "replaced_decisions"
        archive_dir.mkdir(exist_ok=True)
        data = {
            "decisions": decisions,
            "replaced_decision_ids": [d["decision_id"] for d in decisions],
            "replaced_at": "2026-05-10T14:30:00Z",
        }
        p = archive_dir / filename
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return p

    def write_amend_archive(
        self,
        items: list[dict],
        filename: str = "founder_decisions_v2_amended_2026-05-10T15_00_00Z.json",
    ) -> Path:
        archive_dir = self.run_dir / "amended_decisions"
        archive_dir.mkdir(exist_ok=True)
        data = {
            "items": items,
            "amended_decision_ids": [d["decision_id"] for d in items],
            "amended_at": "2026-05-10T15:00:00Z",
        }
        p = archive_dir / filename
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return p

    def write_minimal_derived_artifacts(self) -> None:
        """Write minimal empty derived artifact files needed by report regeneration."""
        for fname in [
            "founder_feedback_mappings.json",
            "founder_preference_profile.json",
            "parking_lot_records.json",
            "evidence_packs.json",
            "opportunity_candidates.json",
            "quality_gate_decisions.json",
            "next_best_actions.json",
            "weekly_opportunity_review.json",
            "founder_inbox_v2_index.json",
        ]:
            _make_minimal_artifact_file(self.run_dir / fname)

    def build_replace_fixture(
        self,
        old_decisions: list[dict] | None = None,
        new_decisions: list[dict] | None = None,
    ) -> None:
        """Build a complete fixture for testing undo-replace."""
        if old_decisions is None:
            old_decisions = [
                _make_decision_dict("dec_old_1", "opp_old_1", PROMOTE, "old notes 1"),
            ]
        if new_decisions is None:
            new_decisions = [
                _make_decision_dict("dec_new_1", "opp_new_1", PARK, "new notes 1"),
            ]

        entry = _make_correction_entry(
            correction_id="correction_replace_001",
            correction_mode="replace",
            old_decision_ids=[d["decision_id"] for d in old_decisions],
            new_decision_ids=[d["decision_id"] for d in new_decisions],
        )
        self.write_manifest()
        self.write_import_history([entry])
        self.write_decisions(new_decisions)
        self.write_replace_archive(old_decisions)
        self.write_minimal_derived_artifacts()

    def build_amend_fixture(
        self,
        original_notes: str = "original notes before amend",
        amended_notes: str = "amended notes",
        decision_id: str = "dec_001",
    ) -> None:
        """Build a complete fixture for testing undo-amend."""
        original = _make_decision_dict(decision_id, "opp_001", PROMOTE, original_notes)
        amended = _make_decision_dict(decision_id, "opp_001", PROMOTE, amended_notes)

        entry = _make_correction_entry(
            correction_id="correction_amend_001",
            correction_mode="amend",
            old_decision_ids=[decision_id],
            new_decision_ids=[decision_id],
        )
        self.write_manifest()
        self.write_import_history([entry])
        self.write_decisions([amended])
        self.write_amend_archive([original])
        self.write_minimal_derived_artifacts()


# ---------------------------------------------------------------------------
# Tests: Pre-validation rejection (categories 1–7, 12–13)
# ---------------------------------------------------------------------------


class TestCorrectionUndoPreValidation(unittest.TestCase):
    """Tests for pre-write validation rejections (fail-closed)."""

    def setUp(self) -> None:
        self.fx = FixtureBuilder()

    def tearDown(self) -> None:
        self.fx.cleanup()

    # --- 1. missing import_history.json rejected ---

    def test_missing_import_history_rejected(self) -> None:
        self.fx.write_manifest()
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("No import history found", result.errors[0])

    # --- 2. empty import_history.json rejected ---

    def test_empty_import_history_rejected(self) -> None:
        self.fx.write_manifest()
        self.fx.write_import_history([])
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("Import history is empty", result.errors[0])

    # --- 3. most recent entry already undo rejected ---

    def test_most_recent_entry_already_undo_rejected(self) -> None:
        # Need a non-undo entry first, followed by an undo entry
        replace_entry = _make_correction_entry(
            correction_id="correction_r_001",
            correction_mode="replace",
            old_decision_ids=["dec_old_1"],
            new_decision_ids=["dec_new_1"],
        )
        undo_entry = _make_correction_entry(
            correction_id="correction_undo_001",
            correction_mode="undo",
        )
        self.fx.write_manifest()
        self.fx.write_import_history([replace_entry, undo_entry])
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("Most recent correction was already undone", result.errors[0])

    # --- 4. unknown correction_mode rejected ---

    def test_unknown_correction_mode_rejected(self) -> None:
        entry = _make_correction_entry(
            correction_id="correction_bad_001",
            correction_mode="bananas",
        )
        self.fx.write_manifest()
        self.fx.write_import_history([entry])
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("Unknown correction mode", result.errors[0])

    # --- 5. replace_all rejected ---

    def test_replace_all_rejected(self) -> None:
        entry = _make_correction_entry(
            correction_id="correction_ra_001",
            correction_mode="replace_all",
        )
        self.fx.write_manifest()
        self.fx.write_import_history([entry])
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("replace_all", result.errors[0])
        self.assertIn("not yet implemented", result.errors[0])

    # --- 6. missing founder_decisions_v2.json rejected ---

    def test_missing_founder_decisions_rejected(self) -> None:
        entry = _make_correction_entry(
            correction_id="correction_r_001",
            correction_mode="replace",
            old_decision_ids=["dec_old_1"],
            new_decision_ids=["dec_new_1"],
        )
        self.fx.write_manifest()
        self.fx.write_import_history([entry])
        # Do NOT write founder_decisions_v2.json
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("Primary artifact missing or corrupt", result.errors[0])

    # --- 7. corrupt founder_decisions_v2.json rejected ---

    def test_corrupt_founder_decisions_rejected(self) -> None:
        entry = _make_correction_entry(
            correction_id="correction_r_001",
            correction_mode="replace",
            old_decision_ids=["dec_old_1"],
            new_decision_ids=["dec_new_1"],
        )
        self.fx.write_manifest()
        self.fx.write_import_history([entry])
        # Write invalid JSON
        (self.fx.run_dir / "founder_decisions_v2.json").write_text(
            "not valid json{{{", encoding="utf-8"
        )
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("Primary artifact is corrupt", result.errors[0])

    # --- 12. undo-amend target decision not found rejected ---

    def test_undo_amend_target_not_found_rejected(self) -> None:
        """When the decision in old_decision_ids doesn't exist in current decisions."""
        original = _make_decision_dict("dec_001", "opp_001", PROMOTE, "original notes")
        entry = _make_correction_entry(
            correction_id="correction_amend_001",
            correction_mode="amend",
            old_decision_ids=["dec_001"],
            new_decision_ids=["dec_001"],
        )
        self.fx.write_manifest()
        self.fx.write_import_history([entry])
        # Write decisions WITHOUT dec_001
        other = _make_decision_dict("dec_002", "opp_002", PROMOTE, "other notes")
        self.fx.write_decisions([other])
        self.fx.write_amend_archive([original])
        self.fx.write_minimal_derived_artifacts()
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("not found in current founder_decisions_v2.json", result.errors[0])

    # --- 13. undo CorrectionEntry is not appended on failure ---

    def test_no_history_append_on_failure(self) -> None:
        """Verify that when undo fails, import_history.json is unchanged."""
        entry = _make_correction_entry(
            correction_id="correction_r_001",
            correction_mode="replace",
            old_decision_ids=["dec_old_1"],
            new_decision_ids=["dec_new_1"],
        )
        self.fx.write_manifest()
        self.fx.write_import_history([entry])
        # No founder_decisions_v2.json — will fail
        history_before = (self.fx.run_dir / "import_history.json").read_text(
            encoding="utf-8"
        )
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        history_after = (self.fx.run_dir / "import_history.json").read_text(
            encoding="utf-8"
        )
        self.assertEqual(history_before, history_after)
        # Verify no undo entry was appended
        data = json.loads(history_after)
        entries = data.get("entries", [])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["correction_mode"], "replace")


# ---------------------------------------------------------------------------
# Tests: Archive validation (categories 8–11)
# ---------------------------------------------------------------------------


class TestCorrectionUndoArchiveValidation(unittest.TestCase):
    """Tests for archive validation during undo."""

    def setUp(self) -> None:
        self.fx = FixtureBuilder()

    def tearDown(self) -> None:
        self.fx.cleanup()

    # --- 8. missing replaced_decisions archive rejected ---

    def test_missing_replaced_archive_rejected(self) -> None:
        old = [_make_decision_dict("dec_old_1", "opp_old_1", PROMOTE, "old")]
        new = [_make_decision_dict("dec_new_1", "opp_new_1", PARK, "new")]
        entry = _make_correction_entry(
            correction_id="correction_r_001",
            correction_mode="replace",
            old_decision_ids=["dec_old_1"],
            new_decision_ids=["dec_new_1"],
        )
        self.fx.write_manifest()
        self.fx.write_import_history([entry])
        self.fx.write_decisions(new)
        # Do NOT create replaced_decisions/ directory
        self.fx.write_minimal_derived_artifacts()
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("Archive not found", result.errors[0])

    # --- 9. corrupt replaced_decisions archive rejected ---

    def test_corrupt_replaced_archive_rejected(self) -> None:
        old = [_make_decision_dict("dec_old_1", "opp_old_1", PROMOTE, "old")]
        new = [_make_decision_dict("dec_new_1", "opp_new_1", PARK, "new")]
        entry = _make_correction_entry(
            correction_id="correction_r_001",
            correction_mode="replace",
            old_decision_ids=["dec_old_1"],
            new_decision_ids=["dec_new_1"],
        )
        self.fx.write_manifest()
        self.fx.write_import_history([entry])
        self.fx.write_decisions(new)
        self.fx.write_minimal_derived_artifacts()
        # Write corrupt archive file
        archive_dir = self.fx.run_dir / "replaced_decisions"
        archive_dir.mkdir(exist_ok=True)
        (archive_dir / "founder_decisions_v2_replaced_bad.json").write_text(
            "{{corrupt json!!", encoding="utf-8"
        )
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("Archive is corrupt", result.errors[0])

    # --- 10. missing amended_decisions archive rejected ---

    def test_missing_amended_archive_rejected(self) -> None:
        original = _make_decision_dict("dec_001", "opp_001", PROMOTE, "original notes")
        amended = _make_decision_dict("dec_001", "opp_001", PROMOTE, "amended notes")
        entry = _make_correction_entry(
            correction_id="correction_amend_001",
            correction_mode="amend",
            old_decision_ids=["dec_001"],
            new_decision_ids=["dec_001"],
        )
        self.fx.write_manifest()
        self.fx.write_import_history([entry])
        self.fx.write_decisions([amended])
        # Do NOT create amended_decisions/ directory
        self.fx.write_minimal_derived_artifacts()
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("Archive not found", result.errors[0])

    # --- 11. corrupt amended_decisions archive rejected ---

    def test_corrupt_amended_archive_rejected(self) -> None:
        original = _make_decision_dict("dec_001", "opp_001", PROMOTE, "original notes")
        amended = _make_decision_dict("dec_001", "opp_001", PROMOTE, "amended notes")
        entry = _make_correction_entry(
            correction_id="correction_amend_001",
            correction_mode="amend",
            old_decision_ids=["dec_001"],
            new_decision_ids=["dec_001"],
        )
        self.fx.write_manifest()
        self.fx.write_import_history([entry])
        self.fx.write_decisions([amended])
        self.fx.write_minimal_derived_artifacts()
        # Write corrupt archive
        archive_dir = self.fx.run_dir / "amended_decisions"
        archive_dir.mkdir(exist_ok=True)
        (archive_dir / "founder_decisions_v2_amended_bad.json").write_text(
            "}}}corrupt", encoding="utf-8"
        )
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("Archive is corrupt", result.errors[0])


# ---------------------------------------------------------------------------
# Tests: Happy path (categories 14–15)
# ---------------------------------------------------------------------------


class TestCorrectionUndoHappyPath(unittest.TestCase):
    """Tests for successful undo operations."""

    def setUp(self) -> None:
        self.fx = FixtureBuilder()

    def tearDown(self) -> None:
        self.fx.cleanup()

    # --- 14. successful undo-amend restores previous notes ---

    def test_undo_amend_restores_previous_notes(self) -> None:
        self.fx.build_amend_fixture(
            original_notes="original notes before amend",
            amended_notes="amended notes",
            decision_id="dec_001",
        )
        result = undo_last_correction(self.fx.run_dir)
        self.assertTrue(
            result.validation_passed,
            f"Undo-amend failed: {result.errors}",
        )
        self.assertEqual(result.undone_correction_mode, "amend")
        self.assertEqual(result.restored_decision_ids, ["dec_001"])
        self.assertFalse(result.derived_artifacts_rebuilt)

        # Verify decisions file was updated
        decisions_path = self.fx.run_dir / "founder_decisions_v2.json"
        data = json.loads(decisions_path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["notes"], "original notes before amend")

        # Verify undo entry was appended
        history_path = self.fx.run_dir / "import_history.json"
        history = json.loads(history_path.read_text(encoding="utf-8"))
        entries = history.get("entries", [])
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1]["correction_mode"], "undo")

    # --- 15. successful undo-replace restores archived decisions ---

    def test_undo_replace_restores_archived_decisions(self) -> None:
        old = [
            _make_decision_dict("dec_old_1", "opp_old_1", PROMOTE, "old notes 1",
                                reasons=[{"category": "strong_pain", "note": ""}]),
            _make_decision_dict("dec_old_2", "opp_old_2", PARK, "old notes 2",
                                reasons=[{"category": "weak_evidence", "note": ""}]),
        ]
        new = [
            _make_decision_dict("dec_new_1", "opp_new_1", KILL, "new notes 1",
                                reasons=[{"category": "too_generic", "note": ""}]),
            _make_decision_dict("dec_new_2", "opp_new_2", PROMOTE, "new notes 2",
                                reasons=[{"category": "strong_pain", "note": ""}]),
        ]

        self.fx.build_replace_fixture(old_decisions=old, new_decisions=new)
        result = undo_last_correction(self.fx.run_dir)
        self.assertTrue(
            result.validation_passed,
            f"Undo-replace failed: {result.errors}",
        )
        self.assertEqual(result.undone_correction_mode, "replace")
        self.assertTrue(result.derived_artifacts_rebuilt)
        self.assertEqual(sorted(result.restored_decision_ids), ["dec_old_1", "dec_old_2"])
        self.assertEqual(sorted(result.removed_decision_ids), ["dec_new_1", "dec_new_2"])

        # Verify decisions restored
        decisions_path = self.fx.run_dir / "founder_decisions_v2.json"
        data = json.loads(decisions_path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        item_ids = {item["decision_id"] for item in items}
        self.assertIn("dec_old_1", item_ids)
        self.assertIn("dec_old_2", item_ids)
        self.assertNotIn("dec_new_1", item_ids)
        self.assertNotIn("dec_new_2", item_ids)

        # Verify derived artifacts were written
        self.assertTrue(
            (self.fx.run_dir / "founder_feedback_mappings.json").is_file()
        )
        self.assertTrue(
            (self.fx.run_dir / "founder_preference_profile.json").is_file()
        )
        self.assertTrue((self.fx.run_dir / "parking_lot_records.json").is_file())

        # Verify undo entry appended
        history = json.loads(
            (self.fx.run_dir / "import_history.json").read_text(encoding="utf-8")
        )
        entries = history.get("entries", [])
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1]["correction_mode"], "undo")
        self.assertEqual(entries[1]["undone_correction_mode"], "replace")


# ---------------------------------------------------------------------------
# Tests: Edge cases (categories 16–20)
# ---------------------------------------------------------------------------


class TestCorrectionUndoEdgeCases(unittest.TestCase):
    """Tests for edge cases, output formatting, and safety properties."""

    def setUp(self) -> None:
        self.fx = FixtureBuilder()

    def tearDown(self) -> None:
        self.fx.cleanup()

    # --- 16. report/dashboard regeneration failure prevents history append ---

    def test_report_regeneration_failure_prevents_history_append(self) -> None:
        """When report regeneration raises, no undo entry is appended."""
        old = [_make_decision_dict("dec_old_1", "opp_old_1", PROMOTE, "old")]
        new = [_make_decision_dict("dec_new_1", "opp_new_1", PARK, "new")]

        self.fx.build_replace_fixture(old_decisions=old, new_decisions=new)
        history_before = (self.fx.run_dir / "import_history.json").read_text(
            encoding="utf-8"
        )

        with patch(
            "oos.correction_undo.build_weekly_run_report",
            side_effect=RuntimeError("simulated report build failure"),
        ):
            result = undo_last_correction(self.fx.run_dir)

        self.assertFalse(result.validation_passed)
        self.assertIn("Report/dashboard regeneration failed", result.errors[0])

        # History should be unchanged
        history_after = (self.fx.run_dir / "import_history.json").read_text(
            encoding="utf-8"
        )
        self.assertEqual(history_before, history_after)

    # --- 17. advisory_only is preserved in undo entry ---

    def test_advisory_only_preserved_in_undo_entry(self) -> None:
        self.fx.build_amend_fixture(
            original_notes="original notes",
            amended_notes="amended notes",
            decision_id="dec_001",
        )
        result = undo_last_correction(self.fx.run_dir)
        self.assertTrue(result.validation_passed)
        self.assertTrue(result.advisory_only)
        self.assertTrue(result.no_live_api)
        self.assertTrue(result.no_live_llm)

        # Verify the undo entry in history
        history = json.loads(
            (self.fx.run_dir / "import_history.json").read_text(encoding="utf-8")
        )
        undo_entry = history["entries"][-1]
        self.assertTrue(undo_entry["advisory_only"])
        self.assertTrue(undo_entry["no_live_api"])
        self.assertTrue(undo_entry["no_live_llm"])

    # --- 18. source URL traceability failure prevents undo ---

    def test_source_url_traceability_failure_prevents_undo(self) -> None:
        """Decisions with placeholder URNs should be rejected before writes.

        Placeholder URNs in archived decisions cause founder_decision_from_dict
        validation to fail, which is caught as an archive decision parse failure
        during undo-replace. This is a fail-closed safety net before traceability
        pre-check even runs.
        """
        old = [
            _make_decision_dict(
                "dec_old_1", "opp_old_1", PROMOTE, "old",
                linked_source_urls=["urn:oos:placeholder:test"],
                reasons=[{"category": "strong_pain", "note": ""}],
            )
        ]
        new = [
            _make_decision_dict(
                "dec_new_1", "opp_new_1", PARK, "new",
                reasons=[{"category": "weak_evidence", "note": ""}],
            ),
        ]

        self.fx.build_replace_fixture(old_decisions=old, new_decisions=new)
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("Archive decision parse failure", result.errors[0])

    # --- 19. repeat undo does not silently undo more than intended ---

    def test_repeat_undo_rejected(self) -> None:
        """First undo succeeds, second undo is rejected."""
        self.fx.build_amend_fixture(
            original_notes="original notes",
            amended_notes="amended notes",
            decision_id="dec_001",
        )
        # First undo
        result1 = undo_last_correction(self.fx.run_dir)
        self.assertTrue(result1.validation_passed)

        # Second undo — should be rejected
        result2 = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result2.validation_passed)
        self.assertIn("already undone", result2.errors[0])

    # --- 20. ASCII-safe formatted output for success/failure ---

    def test_ascii_safe_output_success(self) -> None:
        result = UndoResult(
            run_id="run_001",
            run_dir="/tmp/test",
            undone_correction_id="correction_abc",
            undone_correction_mode="replace",
            undone_at="2026-05-10T14:30:00Z",
            restored_decision_ids=["dec_old_1"],
            removed_decision_ids=["dec_new_1"],
            derived_artifacts_rebuilt=True,
            artifacts_updated=[
                "founder_decisions_v2",
                "founder_feedback_mappings",
                "founder_preference_profile",
                "parking_lot_records",
                "manifest",
            ],
            validation_passed=True,
            advisory_only=True,
            no_live_api=True,
            no_live_llm=True,
            source_url_placeholder_count=0,
            source_url_missing_count=0,
        )
        output = format_undo_result_output(result, use_utf8=False)
        # ASCII-safe success
        self.assertIn("Undo-last correction: OK", output)
        self.assertIn("Undone correction:", output)
        self.assertIn("correction_id:   correction_abc", output)
        self.assertIn("correction_mode: replace", output)
        self.assertIn("Restored:", output)
        self.assertIn("Total restored: 1", output)
        self.assertIn("Removed:", output)
        self.assertIn("Total removed: 1", output)
        self.assertIn("Derived artifacts rebuilt:", output)
        self.assertIn("Source URL traceability: OK", output)
        self.assertIn("Undo complete.", output)

        # UTF-8 mode
        output_utf8 = format_undo_result_output(result, use_utf8=True)
        self.assertIn("\u2713", output_utf8)
        self.assertNotIn("OK", output_utf8.split("\n")[0])

    def test_ascii_safe_output_failure(self) -> None:
        result = UndoResult(
            run_dir="/tmp/test",
            errors=["Test error message"],
            validation_passed=False,
            advisory_only=True,
            no_live_api=True,
            no_live_llm=True,
        )
        output = format_undo_result_output(result, use_utf8=False)
        self.assertIn("Undo-last correction: FAIL", output)
        self.assertIn("Error: Test error message", output)
        self.assertIn("No artifacts were modified.", output)

        # UTF-8 failure output
        output_utf8 = format_undo_result_output(result, use_utf8=True)
        self.assertIn("\u2717", output_utf8)


# ---------------------------------------------------------------------------
# Additional focused low-level tests
# ---------------------------------------------------------------------------


class TestCorrectionUndoLowLevel(unittest.TestCase):
    """Focused low-level tests on internal helpers."""

    def test_precheck_traceability_catches_placeholder_urls(self) -> None:
        from oos.founder_decision_taxonomy import FounderDecisionReason
        d = FounderDecisionV2(
            decision_id="dec_001",
            opportunity_id="opp_001",
            evidence_pack_id="ep_001",
            decision=PROMOTE,
            reasons=[FounderDecisionReason(category="strong_pain")],
            notes="",
            confidence=0.8,
            linked_evidence_ids=["ev_opp_001_1"],
            linked_source_signal_ids=["sig_opp_001_1"],
            linked_source_urls=["urn:oos:placeholder:test"],
            decided_by="founder",
            decided_at="2026-05-01T10:00:00Z",
        )
        result = _precheck_source_url_traceability(decisions=[d])
        self.assertIsNotNone(result)
        self.assertFalse(result["validation_passed"])
        self.assertGreater(result["placeholder_count"], 0)

    def test_precheck_traceability_passes_with_real_urls(self) -> None:
        d = create_founder_decision(
            opportunity_id="opp_001",
            evidence_pack_id="ep_001",
            decision=PROMOTE,
            reasons=["strong_pain"],
            linked_source_urls=["https://example.com/test"],
        )
        result = _precheck_source_url_traceability(decisions=[d])
        self.assertIsNotNone(result)
        self.assertTrue(result["validation_passed"])
        self.assertEqual(result["placeholder_count"], 0)
        self.assertEqual(result["missing_count"], 0)

    def test_precheck_traceability_catches_missing_urls(self) -> None:
        d = create_founder_decision(
            opportunity_id="opp_001",
            evidence_pack_id="ep_001",
            decision=PROMOTE,
            reasons=["strong_pain"],
            linked_source_urls=[],
        )
        result = _precheck_source_url_traceability(decisions=[d])
        self.assertIsNotNone(result)
        self.assertFalse(result["validation_passed"])
        self.assertGreater(result["missing_count"], 0)

    def test_append_undo_history_entry_writes_deterministic_id(self) -> None:
        """Verify undo entry has deterministic correction_id and correct fields."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            history_path = run_dir / "import_history.json"
            history_data = {
                "schema_version": "import_history.v1",
                "entries": [
                    _make_correction_entry(
                        correction_id="correction_r_001",
                        correction_mode="replace",
                        old_decision_ids=["dec_old_1"],
                        new_decision_ids=["dec_new_1"],
                    )
                ],
            }
            history_path.write_text(
                json.dumps(history_data, indent=2), encoding="utf-8"
            )

            _append_undo_history_entry(
                run_dir=run_dir,
                run_id="run_test",
                corrected_at="2026-05-10T15:00:00Z",
                undone_correction_id="correction_r_001",
                undone_correction_mode="replace",
                undone_decision_ids=["dec_old_1"],
                source_history_entry_index=0,
                archive_refs={"replaced_decisions": "replaced_decisions/test.json"},
                history_data=history_data,
                entries_list=list(history_data["entries"]),
                warnings=[],
            )

            # Read back and verify
            updated = json.loads(history_path.read_text(encoding="utf-8"))
            entries = updated["entries"]
            self.assertEqual(len(entries), 2)

            undo_entry = entries[1]
            self.assertEqual(undo_entry["correction_mode"], "undo")
            self.assertEqual(undo_entry["undone_correction_id"], "correction_r_001")
            self.assertEqual(undo_entry["undone_correction_mode"], "replace")
            self.assertEqual(undo_entry["undone_decision_ids"], ["dec_old_1"])
            self.assertEqual(undo_entry["source_history_entry_index"], 0)
            self.assertTrue(undo_entry["advisory_only"])
            self.assertTrue(undo_entry["no_live_api"])
            self.assertTrue(undo_entry["no_live_llm"])
            self.assertTrue(
                undo_entry["correction_id"].startswith("undo_"),
                f"correction_id should start with 'undo_': {undo_entry['correction_id']}",
            )

    def test_undo_result_to_dict_roundtrip(self) -> None:
        """Verify UndoResult.to_dict() is complete and roundtrippable."""
        result = UndoResult(
            run_id="run_001",
            run_dir="/tmp/run_001",
            undone_correction_id="correction_abc",
            undone_correction_mode="replace",
            undone_at="2026-05-10T14:30:00Z",
            restored_decision_ids=["dec_1", "dec_2"],
            removed_decision_ids=["dec_3"],
            derived_artifacts_rebuilt=True,
            warnings=["test warning"],
            errors=[],
            artifacts_updated=["founder_decisions_v2"],
            validation_passed=True,
            advisory_only=True,
            no_live_api=True,
            no_live_llm=True,
            schema_version=UNDO_LAST_SCHEMA_VERSION,
            source_url_placeholder_count=0,
            source_url_missing_count=0,
            archive_refs={"replaced_decisions": "replaced_decisions/test.json"},
        )
        d = result.to_dict()
        self.assertEqual(d["run_id"], "run_001")
        self.assertEqual(d["undone_correction_id"], "correction_abc")
        self.assertEqual(d["restored_decision_ids"], ["dec_1", "dec_2"])
        self.assertEqual(d["removed_decision_ids"], ["dec_3"])
        self.assertTrue(d["advisory_only"])
        self.assertTrue(d["validation_passed"])
        self.assertIn("replaced_decisions", d["archive_refs"])

    def test_fail_result_has_all_safety_flags(self) -> None:
        """Verify that even failure results carry advisory_only and safety flags."""
        from oos.correction_undo import _fail as correction_undo_fail

        import tempfile

        with tempfile.TemporaryDirectory() as td:
            result = correction_undo_fail(
                run_dir=Path(td),
                corrected_at="2026-05-10T14:30:00Z",
                message="test failure",
            )
            self.assertFalse(result.validation_passed)
            self.assertTrue(result.advisory_only)
            self.assertTrue(result.no_live_api)
            self.assertTrue(result.no_live_llm)
            self.assertEqual(result.errors, ["test failure"])

    def test_format_output_amend_success_ascii(self) -> None:
        """Amend undo output is formatted correctly."""
        result = UndoResult(
            run_id="run_001",
            run_dir="/tmp/test",
            undone_correction_id="correction_xyz",
            undone_correction_mode="amend",
            undone_at="2026-05-10T15:00:00Z",
            restored_decision_ids=["dec_abc"],
            removed_decision_ids=[],
            derived_artifacts_rebuilt=False,
            artifacts_updated=["founder_decisions_v2"],
            validation_passed=True,
            advisory_only=True,
            no_live_api=True,
            no_live_llm=True,
            source_url_placeholder_count=0,
            source_url_missing_count=0,
        )
        output = format_undo_result_output(result, use_utf8=False)
        self.assertIn("Undo-last correction: OK", output)
        self.assertIn("correction_mode: amend", output)
        self.assertIn("No rebuild needed", output)

    def test_undo_only_entries_all_rejected(self) -> None:
        """When all entries in history are undo, undo should be rejected."""
        self.fx = FixtureBuilder()
        self.fx.write_manifest()
        self.fx.write_import_history([
            _make_correction_entry(
                correction_id="correction_undo_001",
                correction_mode="undo",
            ),
            _make_correction_entry(
                correction_id="correction_undo_002",
                correction_mode="undo",
            ),
        ])
        result = undo_last_correction(self.fx.run_dir)
        self.assertFalse(result.validation_passed)
        self.assertIn("contains only undo entries", result.errors[0])
        self.fx.cleanup()


# ---------------------------------------------------------------------------
# CLI tests: import-founder-decisions-v2 --undo-last
# ---------------------------------------------------------------------------


import io
from contextlib import redirect_stdout

from oos.cli import main as cli_main


class TestCliUndoLast(unittest.TestCase):
    """Focused CLI coverage for import-founder-decisions-v2 --undo-last.

    Uses FixtureBuilder from this module for deterministic temp directory setup.
    Covers items 1–10 from substep 3.1-B task specification.
    No live APIs. No live LLMs. No uncontrolled artifact writes.
    """

    def setUp(self) -> None:
        self.fx = FixtureBuilder()
        self.project_root = str(self.fx.base)

    def tearDown(self) -> None:
        self.fx.cleanup()

    # -- helpers --

    def _run_cli(self, *extra_args: str) -> tuple[int, str]:
        """Run cli_main with import-founder-decisions-v2 and collect exit code + stdout."""
        args = [
            "import-founder-decisions-v2",
            "--project-root",
            self.project_root,
            "--run-id",
            self.fx.run_id,
            *extra_args,
        ]
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cli_main(args)
        return exit_code, buf.getvalue()

    # ------------------------------------------------------------------
    # 0. --help lists --undo-last and --utf8
    # ------------------------------------------------------------------

    def test_help_lists_undo_last(self) -> None:
        """import-founder-decisions-v2 --help must list --undo-last (v2.10 item 3.1)."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            try:
                cli_main(["import-founder-decisions-v2", "--help"])
            except SystemExit:
                pass
        output = stdout.getvalue()
        self.assertIn("--undo-last", output)

    def test_help_lists_utf8(self) -> None:
        """import-founder-decisions-v2 --help must list --utf8
        (undo-last contract Section 9.1 requires --utf8 support)."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            try:
                cli_main(["import-founder-decisions-v2", "--help"])
            except SystemExit:
                pass
        output = stdout.getvalue()
        self.assertIn("--utf8", output)

    # ------------------------------------------------------------------
    # 1. --undo-last succeeds on a valid deterministic fixture
    # ------------------------------------------------------------------

    def test_undo_last_succeeds_on_valid_fixture(self) -> None:
        self.fx.build_amend_fixture(
            original_notes="original notes before amend",
            amended_notes="amended notes",
            decision_id="dec_001",
        )
        exit_code, output = self._run_cli("--undo-last")
        self.assertEqual(exit_code, 0)
        self.assertIn("Undo-last correction: OK", output)
        self.assertIn("Undo complete.", output)

    # ------------------------------------------------------------------
    # 2. --undo-last works without --decisions-file
    # ------------------------------------------------------------------

    def test_undo_last_without_decisions_file(self) -> None:
        self.fx.build_amend_fixture(
            original_notes="original notes",
            amended_notes="amended notes",
            decision_id="dec_001",
        )
        exit_code, output = self._run_cli("--undo-last")
        self.assertEqual(exit_code, 0)
        self.assertIn("Undo-last correction: OK", output)

    # ------------------------------------------------------------------
    # 3. --undo-last rejects conflicting flag: --replace-review-items
    # ------------------------------------------------------------------

    def test_undo_last_rejects_replace_review_items(self) -> None:
        self.fx.build_amend_fixture(
            original_notes="original",
            amended_notes="amended",
            decision_id="dec_001",
        )
        exit_code, output = self._run_cli(
            "--undo-last", "--replace-review-items", "some_rid"
        )
        self.assertEqual(exit_code, 2)
        self.assertIn("Conflicting flags", output)
        self.assertIn("--replace-review-items", output)

    # ------------------------------------------------------------------
    # 4. --undo-last rejects conflicting flag: --amend-notes-only
    # ------------------------------------------------------------------

    def test_undo_last_rejects_amend_notes_only(self) -> None:
        self.fx.build_amend_fixture(
            original_notes="original",
            amended_notes="amended",
            decision_id="dec_001",
        )
        exit_code, output = self._run_cli(
            "--undo-last", "--amend-notes-only"
        )
        self.assertEqual(exit_code, 2)
        self.assertIn("Conflicting flags", output)
        self.assertIn("--amend-notes-only", output)

    # ------------------------------------------------------------------
    # 5. Failure case returns non-zero exit code
    # ------------------------------------------------------------------

    def test_undo_last_failure_returns_non_zero(self) -> None:
        """Undo on a fixture with missing import_history returns exit code 1."""
        self.fx.write_manifest()
        # No import_history.json, no decisions — will fail pre-validation
        exit_code, output = self._run_cli("--undo-last")
        self.assertEqual(exit_code, 1)
        self.assertIn("Undo-last correction: FAIL", output)
        self.assertIn("No import history found", output)

    # ------------------------------------------------------------------
    # 6. Default CLI output is ASCII-safe
    # ------------------------------------------------------------------

    def test_default_output_is_ascii_safe(self) -> None:
        self.fx.build_amend_fixture(
            original_notes="original notes before amend",
            amended_notes="amended notes",
            decision_id="dec_001",
        )
        exit_code, output = self._run_cli("--undo-last")
        self.assertEqual(exit_code, 0)
        self.assertIn("Undo-last correction: OK", output)
        self.assertNotIn("\u2713", output)

    # ------------------------------------------------------------------
    # 7. --undo-last does not introduce terminal encoding auto-detection
    #    (--utf8 remains opt-in; default is always ASCII-safe)
    # ------------------------------------------------------------------

    def test_undo_last_no_encoding_auto_detection(self) -> None:
        """Default output must be ASCII-safe; Unicode only appears with --utf8."""
        # Use two separate fixtures — undo modifies state, so re-using
        # the same run_dir causes the second invocation to fail with
        # "already undone".
        fx2 = FixtureBuilder()

        try:
            # Default (no --utf8): ASCII-safe
            self.fx.build_amend_fixture(
                original_notes="original notes",
                amended_notes="amended notes",
                decision_id="dec_001",
            )
            exit_code, output = self._run_cli("--undo-last")
            self.assertEqual(exit_code, 0)
            self.assertNotIn("\u2713", output)

            # With --utf8: Unicode checkmark (fresh fixture)
            fx2.run_id = "run_test_002"
            fx2.weekly_runs = fx2.base / "artifacts" / "weekly_runs"
            fx2.run_dir = fx2.weekly_runs / fx2.run_id
            fx2.run_dir.mkdir(parents=True, exist_ok=True)
            fx2.build_amend_fixture(
                original_notes="original notes",
                amended_notes="amended notes",
                decision_id="dec_002",
            )
            # Override project_root to fx2.base for the second invocation
            args2 = [
                "import-founder-decisions-v2",
                "--project-root",
                str(fx2.base),
                "--run-id",
                fx2.run_id,
                "--undo-last",
                "--utf8",
            ]
            buf2 = io.StringIO()
            with redirect_stdout(buf2):
                exit_code2 = cli_main(args2)
            output2 = buf2.getvalue()
            self.assertEqual(exit_code2, 0)
            self.assertIn("\u2713", output2)
        finally:
            fx2.cleanup()

    # ------------------------------------------------------------------
    # 8. CLI output is deterministic enough for tests
    #    (assert stable key phrases, not fragile full output)
    # ------------------------------------------------------------------

    def test_cli_output_stable_key_phrases(self) -> None:
        self.fx.build_amend_fixture(
            original_notes="original notes before amend",
            amended_notes="amended notes",
            decision_id="dec_001",
        )
        exit_code, output = self._run_cli("--undo-last")
        self.assertEqual(exit_code, 0)
        self.assertIn("Undone correction:", output)
        self.assertIn("correction_id:", output)
        self.assertIn("correction_mode: amend", output)
        self.assertIn("Restored:", output)
        self.assertIn("Undo complete.", output)
        self.assertIn("Original correction entry preserved.", output)

    # ------------------------------------------------------------------
    # 9. No live APIs/LLMs — satisfied by FixtureBuilder (no mock needed)
    # ------------------------------------------------------------------

    def test_no_live_api_llm_calls(self) -> None:
        """All fixtures are deterministic; nothing calls external services."""
        self.fx.build_amend_fixture(
            original_notes="original",
            amended_notes="amended",
            decision_id="dec_001",
        )
        exit_code, output = self._run_cli("--undo-last")
        self.assertEqual(exit_code, 0)
        # The safety flags are always set
        self.assertIn("Undo complete.", output)

    # ------------------------------------------------------------------
    # Additional: --decisions-file + --undo-last conflict
    # ------------------------------------------------------------------

    def test_undo_last_rejects_decisions_file(self) -> None:
        self.fx.build_amend_fixture(
            original_notes="original",
            amended_notes="amended",
            decision_id="dec_001",
        )
        # Create a dummy decisions file to pass as argument
        decisions_file = self.fx.base / "dummy_decisions.json"
        decisions_file.write_text("[]", encoding="utf-8")
        exit_code, output = self._run_cli(
            "--undo-last", "--decisions-file", str(decisions_file)
        )
        self.assertEqual(exit_code, 2)
        self.assertIn("Conflicting flags", output)
        self.assertIn("--decisions-file", output)

    # ------------------------------------------------------------------
    # Additional: --utf8 success output uses Unicode checkmark
    # ------------------------------------------------------------------

    def test_utf8_output_uses_unicode_checkmark(self) -> None:
        self.fx.build_amend_fixture(
            original_notes="original notes",
            amended_notes="amended notes",
            decision_id="dec_001",
        )
        exit_code, output = self._run_cli("--undo-last", "--utf8")
        self.assertEqual(exit_code, 0)
        self.assertIn("\u2713", output)
        # The first line should not contain ASCII "OK" when UTF-8 is used
        first_line = output.strip().split("\n")[0]
        self.assertNotIn("OK", first_line)
