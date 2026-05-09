"""Tests for decision_correction_rebuild — parking lot orphan cleanup and
derived artifact rebuild model.

Roadmap v2.8 item 1.2 focused tests (>=16).

All tests are deterministic. No live APIs. No live LLMs. No portfolio mutations.
No files are written to disk.
"""

from __future__ import annotations

import json
import unittest

from oos.decision_correction_rebuild import (
    DECISION_CORRECTION_REBUILD_SCHEMA_VERSION,
    DerivedArtifactRebuildPlan,
    DerivedArtifactRebuildResult,
    ParkingLotCleanupResult,
    _is_placeholder_urn,
    _is_real_source_url,
    _validate_source_urls,
    cleanup_orphaned_parking_lot_records,
    identify_orphaned_parking_lot_records,
    plan_derived_artifact_rebuild,
    rebuild_founder_decision_derived_artifacts,
    validate_rebuild_inputs,
)
from oos.founder_decision_taxonomy import (
    KILL,
    NEEDS_MORE_EVIDENCE,
    PARK,
    PROMOTE,
    REVISIT_LATER,
    create_founder_decision,
)
from oos.parking_lot import ParkingLotRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_test_decision(
    opportunity_id: str = "opp_test_001",
    decision: str = PROMOTE,
    reasons: list[str] | None = None,
    linked_source_urls: list[str] | None = None,
    notes: str = "",
    decision_id: str | None = None,
) -> dict:
    """Create a minimal test decision dict for use in rebuild tests."""
    if reasons is None:
        reasons = ["strong_pain"]
    if linked_source_urls is None:
        linked_source_urls = [f"https://example.com/{opportunity_id}"]
    did = decision_id or f"fd_v2_test_{opportunity_id}"
    return {
        "decision_id": did,
        "opportunity_id": opportunity_id,
        "evidence_pack_id": f"ep_{opportunity_id}",
        "decision": decision,
        "reasons": [{"category": r, "note": ""} for r in reasons],
        "notes": notes,
        "confidence": 0.9,
        "linked_evidence_ids": [f"ev_{opportunity_id}_1"],
        "linked_source_signal_ids": [f"sig_{opportunity_id}_1"],
        "linked_source_urls": list(linked_source_urls),
        "decided_by": "founder",
        "decided_at": "2026-05-01T10:00:00Z",
        "schema_version": "founder_decision_v2.v1",
        "auto_promote": False,
        "founder_decision_authority": "founder_decision_record_only",
    }


def _make_test_parking_lot_record(
    record_id: str = "pl_test_001",
    source_decision_id: str = "fd_v2_test_opp_001",
    linked_opportunity_id: str = "opp_test_001",
    status: str = "parked",
) -> ParkingLotRecord:
    """Create a minimal test parking lot record."""
    return ParkingLotRecord(
        record_id=record_id,
        source_decision_id=source_decision_id,
        source_artifact_ids=[source_decision_id, "ev_test_1"],
        linked_opportunity_id=linked_opportunity_id,
        title=f"Test {linked_opportunity_id}",
        summary=f"Summary for {linked_opportunity_id}",
        reason="weak_evidence",
        pattern_keys=["test", "weak_evidence"],
        status=status,
    )


# ---------------------------------------------------------------------------
# Model serialization tests
# ---------------------------------------------------------------------------


class ParkingLotCleanupResultSerializationTests(unittest.TestCase):
    """Test 1: ParkingLotCleanupResult serializes to JSON."""

    def test_serializes_to_json(self):
        result = ParkingLotCleanupResult(
            schema_version=DECISION_CORRECTION_REBUILD_SCHEMA_VERSION,
            active_record_count_before=5,
            active_record_count_after=3,
            orphaned_record_count=2,
            retained_record_ids=["pl_1", "pl_2", "pl_3"],
            orphaned_record_ids=["pl_4", "pl_5"],
            warnings=["Test warning"],
            errors=[],
            validation_passed=True,
        )
        data = result.to_dict()
        json_str = json.dumps(data, indent=2)
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["active_record_count_before"], 5)
        self.assertEqual(parsed["active_record_count_after"], 3)
        self.assertEqual(parsed["orphaned_record_count"], 2)
        self.assertTrue(parsed["advisory_only"])
        self.assertTrue(parsed["no_live_api"])
        self.assertTrue(parsed["no_live_llm"])


class DerivedArtifactRebuildResultSerializationTests(unittest.TestCase):
    """Test 2: DerivedArtifactRebuildResult serializes to JSON."""

    def test_serializes_to_json(self):
        result = DerivedArtifactRebuildResult(
            schema_version=DECISION_CORRECTION_REBUILD_SCHEMA_VERSION,
            active_founder_decision_count=3,
            feedback_mapping_count=3,
            preference_profile_present=True,
            parking_lot_record_count=1,
            orphaned_parking_lot_record_count=0,
            validation_passed=True,
        )
        data = result.to_dict()
        json_str = json.dumps(data, indent=2)
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["active_founder_decision_count"], 3)
        self.assertEqual(parsed["feedback_mapping_count"], 3)
        self.assertTrue(parsed["preference_profile_present"])
        self.assertTrue(parsed["advisory_only"])
        self.assertTrue(parsed["no_live_api"])
        self.assertTrue(parsed["no_live_llm"])


class DerivedArtifactRebuildPlanSerializationTests(unittest.TestCase):
    """DerivedArtifactRebuildPlan serializes to JSON."""

    def test_serializes_to_json(self):
        plan = DerivedArtifactRebuildPlan(
            active_decision_count=4,
            expected_feedback_mapping_count=4,
            expected_preference_profile_present=True,
            expected_parking_lot_record_count=2,
            parking_lot_orphans_to_remove=1,
            parking_lot_new_records_to_add=1,
            validation_passed=True,
        )
        data = plan.to_dict()
        json_str = json.dumps(data, indent=2)
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["active_decision_count"], 4)
        self.assertEqual(parsed["expected_feedback_mapping_count"], 4)


# ---------------------------------------------------------------------------
# Orphan detection tests
# ---------------------------------------------------------------------------


class OrphanDetectionTests(unittest.TestCase):
    """Test 3-6: Orphan parking lot records are correctly identified and retained."""

    def test_orphan_records_detected(self):
        """Test 3: Orphan parking lot records are detected when source_decision_id
        is not in active decision IDs."""
        pl_records = [
            _make_test_parking_lot_record(
                record_id="pl_001",
                source_decision_id="fd_active_1",
                linked_opportunity_id="opp_1",
            ),
            _make_test_parking_lot_record(
                record_id="pl_002",
                source_decision_id="fd_orphan_1",
                linked_opportunity_id="opp_2",
            ),
            _make_test_parking_lot_record(
                record_id="pl_003",
                source_decision_id="fd_active_2",
                linked_opportunity_id="opp_3",
            ),
        ]
        active_ids = {"fd_active_1", "fd_active_2"}

        active, orphaned = identify_orphaned_parking_lot_records(
            parking_lot_records=pl_records,
            active_decision_ids=active_ids,
        )

        self.assertEqual(len(active), 2)
        self.assertEqual(len(orphaned), 1)
        self.assertEqual(orphaned[0].record_id, "pl_002")
        self.assertEqual(orphaned[0].source_decision_id, "fd_orphan_1")

    def test_valid_records_retained(self):
        """Test 4: Valid parking lot records are retained when source_decision_id
        exists in active decision IDs."""
        pl_records = [
            _make_test_parking_lot_record(
                record_id="pl_001",
                source_decision_id="fd_active_1",
            ),
        ]
        active_ids = {"fd_active_1"}

        active, orphaned = identify_orphaned_parking_lot_records(
            parking_lot_records=pl_records,
            active_decision_ids=active_ids,
        )

        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].record_id, "pl_001")
        self.assertEqual(len(orphaned), 0)

    def test_cleanup_returns_orphan_ids_without_deleting(self):
        """Test 5: Cleanup result returns orphan IDs without deleting files."""
        pl_records = [
            _make_test_parking_lot_record("pl_001", "fd_active"),
            _make_test_parking_lot_record("pl_002", "fd_orphan"),
        ]
        active_ids = {"fd_active"}

        retained, result = cleanup_orphaned_parking_lot_records(
            parking_lot_records=pl_records,
            active_decision_ids=active_ids,
        )

        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0].record_id, "pl_001")
        self.assertEqual(result.orphaned_record_count, 1)
        self.assertEqual(result.orphaned_record_ids, ["pl_002"])
        self.assertEqual(result.retained_record_ids, ["pl_001"])
        self.assertEqual(result.active_record_count_before, 2)
        self.assertEqual(result.active_record_count_after, 1)
        self.assertTrue(result.validation_passed)

    def test_cleanup_is_deterministic(self):
        """Test 6: Cleanup is deterministic — same input yields same output."""
        pl_records = [
            _make_test_parking_lot_record("pl_002", "fd_orphan"),
            _make_test_parking_lot_record("pl_001", "fd_active"),
            _make_test_parking_lot_record("pl_003", "fd_active_2"),
        ]
        active_ids = {"fd_active", "fd_active_2"}

        retained1, cleanup1 = cleanup_orphaned_parking_lot_records(pl_records, active_ids)
        retained2, cleanup2 = cleanup_orphaned_parking_lot_records(pl_records, active_ids)

        # Same retained records
        self.assertEqual(
            [r.record_id for r in retained1],
            [r.record_id for r in retained2],
        )
        # Same cleanup result
        self.assertEqual(cleanup1.to_dict(), cleanup2.to_dict())

    def test_empty_input_handled_gracefully(self):
        """Empty parking lot records returns empty results."""
        active, orphaned = identify_orphaned_parking_lot_records(
            parking_lot_records=[],
            active_decision_ids={"fd_1"},
        )
        self.assertEqual(len(active), 0)
        self.assertEqual(len(orphaned), 0)

    def test_empty_active_ids_all_orphaned(self):
        """All records are orphaned when active_decision_ids is empty."""
        pl_records = [
            _make_test_parking_lot_record("pl_001", "fd_1"),
            _make_test_parking_lot_record("pl_002", "fd_2"),
        ]
        active, orphaned = identify_orphaned_parking_lot_records(
            parking_lot_records=pl_records,
            active_decision_ids=set(),
        )
        self.assertEqual(len(active), 0)
        self.assertEqual(len(orphaned), 2)


# ---------------------------------------------------------------------------
# Source URL traceability tests
# ---------------------------------------------------------------------------


class SourceURLTraceabilityTests(unittest.TestCase):
    """Test 7-9: Source URL traceability checks."""

    def test_rebuild_preserves_source_urls_in_feedback_mappings(self):
        """Test 7: Rebuild result preserves source URLs in feedback mappings."""
        decisions = [
            _make_test_decision(
                opportunity_id="opp_1",
                decision=PROMOTE,
                reasons=["strong_pain"],
                linked_source_urls=["https://hn.algolia.com/item?id=1"],
            ),
            _make_test_decision(
                opportunity_id="opp_2",
                decision=PARK,
                reasons=["weak_evidence"],
                linked_source_urls=["https://github.com/user/repo/issues/2"],
            ),
        ]

        result = rebuild_founder_decision_derived_artifacts(decisions=decisions)

        self.assertTrue(result.validation_passed,
                       f"Expected validation passed, got errors: {result.errors}")
        self.assertEqual(len(result.feedback_mappings), 2)
        for m in result.feedback_mappings:
            self.assertGreater(len(m.source_urls), 0)
            for url in m.source_urls:
                self.assertTrue(
                    url.startswith("http://") or url.startswith("https://"),
                    f"URL '{url}' is not a real http/https URL",
                )
                self.assertFalse(
                    url.startswith("urn:oos:"),
                    f"URL '{url}' is a placeholder URN",
                )

    def test_rebuild_rejects_urn_oos_source_urls(self):
        """Test 8: Rebuild rejects urn:oos:* source URLs."""
        decisions = [
            _make_test_decision(
                opportunity_id="opp_1",
                decision=PROMOTE,
                linked_source_urls=["urn:oos:placeholder:1"],
            ),
        ]

        result = rebuild_founder_decision_derived_artifacts(decisions=decisions)

        self.assertFalse(result.validation_passed)
        self.assertGreater(len(result.errors), 0)
        # Check for either "placeholder" or "urn:oos" in errors (error messages
        # may come from FounderDecisionV2 validation or our own source URL check)
        urn_error = any(
            ("placeholder" in e.lower() or "urn:oos" in e.lower())
            for e in result.errors
        )
        self.assertTrue(urn_error,
                       f"Expected placeholder/URN error, got: {result.errors}")

    def test_rebuild_fails_closed_on_missing_source_urls(self):
        """Test 9: Rebuild fails closed on missing required source URLs."""
        decisions = [
            _make_test_decision(
                opportunity_id="opp_1",
                decision=PROMOTE,
                linked_source_urls=[],  # No source URLs
            ),
        ]

        result = rebuild_founder_decision_derived_artifacts(decisions=decisions)

        self.assertFalse(result.validation_passed)
        self.assertGreater(len(result.errors), 0)
        url_error = any(
            ("no source" in e.lower() or "no real" in e.lower())
            for e in result.errors
        )
        self.assertTrue(url_error,
                       f"Expected missing URL error, got: {result.errors}")

    def test_validate_source_urls_accepts_real_urls(self):
        """_validate_source_urls accepts real http/https URLs."""
        errors, warnings = _validate_source_urls(
            source_urls=["https://example.com/page"],
            context_label="test",
        )
        self.assertEqual(len(errors), 0)

    def test_validate_source_urls_rejects_placeholder_urns(self):
        """_validate_source_urls rejects placeholder URNs."""
        errors, warnings = _validate_source_urls(
            source_urls=["urn:oos:placeholder:1"],
            context_label="test",
        )
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("placeholder" in e.lower() for e in errors))

    def test_validate_source_urls_rejects_empty_list(self):
        """_validate_source_urls rejects empty URL list."""
        errors, warnings = _validate_source_urls(
            source_urls=[],
            context_label="test",
        )
        self.assertGreater(len(errors), 0)

    def test_is_real_source_url(self):
        """_is_real_source_url correctly identifies real URLs."""
        self.assertTrue(_is_real_source_url("https://example.com"))
        self.assertTrue(_is_real_source_url("http://example.com"))
        self.assertFalse(_is_real_source_url("urn:oos:placeholder"))
        self.assertFalse(_is_real_source_url("ftp://example.com"))
        self.assertFalse(_is_real_source_url(""))

    def test_is_placeholder_urn(self):
        """_is_placeholder_urn correctly identifies placeholder URNs."""
        self.assertTrue(_is_placeholder_urn("urn:oos:test"))
        self.assertTrue(_is_placeholder_urn("URN:OOS:test"))
        self.assertFalse(_is_placeholder_urn("https://example.com"))
        self.assertFalse(_is_placeholder_urn(""))


# ---------------------------------------------------------------------------
# Rebuild tests
# ---------------------------------------------------------------------------


class RebuildTests(unittest.TestCase):
    """Test 10-13: Derived artifact rebuild behavior."""

    def test_rebuild_creates_expected_feedback_mapping_count(self):
        """Test 10: Rebuild creates expected feedback mapping count from active decisions."""
        decisions = [
            _make_test_decision("opp_1", PROMOTE, reasons=["strong_pain"]),
            _make_test_decision("opp_2", PARK, reasons=["weak_evidence"]),
            _make_test_decision("opp_3", KILL, reasons=["too_generic"]),
        ]

        result = rebuild_founder_decision_derived_artifacts(decisions=decisions)

        self.assertTrue(result.validation_passed,
                       f"Expected validation passed, got errors: {result.errors}")
        self.assertEqual(result.active_founder_decision_count, 3)
        self.assertEqual(result.feedback_mapping_count, 3)
        self.assertEqual(len(result.feedback_mappings), 3)

    def test_rebuild_creates_preference_profile(self):
        """Test 11: Rebuild creates/updates preference profile using existing logic."""
        decisions = [
            _make_test_decision("opp_1", PROMOTE, reasons=["strong_pain", "clear_buyer"]),
            _make_test_decision("opp_2", PARK, reasons=["weak_evidence"]),
            _make_test_decision("opp_3", KILL, reasons=["too_generic"]),
        ]

        result = rebuild_founder_decision_derived_artifacts(decisions=decisions)

        self.assertTrue(result.validation_passed,
                       f"Expected validation passed, got errors: {result.errors}")
        self.assertTrue(result.preference_profile_present)
        self.assertIsNotNone(result.preference_profile)
        self.assertEqual(result.preference_profile.decision_count, 3)
        self.assertEqual(result.preference_profile.promote_count, 1)
        self.assertEqual(result.preference_profile.park_count, 1)
        self.assertEqual(result.preference_profile.kill_count, 1)

    def test_rebuild_creates_parking_lot_records_for_park_revisit(self):
        """Test 12: Rebuild creates parking lot records for PARK/REVISIT decisions."""
        decisions = [
            _make_test_decision("opp_1", PROMOTE, reasons=["strong_pain"]),
            _make_test_decision("opp_2", PARK, reasons=["weak_evidence"]),
            _make_test_decision("opp_3", REVISIT_LATER, reasons=["waiting_for_more_signals"]),
        ]

        result = rebuild_founder_decision_derived_artifacts(decisions=decisions)

        self.assertTrue(result.validation_passed,
                       f"Expected validation passed, got errors: {result.errors}")
        self.assertEqual(result.parking_lot_record_count, 2)
        statuses = {r.status for r in result.parking_lot_records}
        self.assertIn("parked", statuses)
        self.assertIn("revisit_later", statuses)

    def test_rebuild_excludes_promote_kill_nme_from_parking_lot(self):
        """Test 13: Rebuild does not create parking lot records for
        PROMOTE/KILL/NEEDS_MORE_EVIDENCE."""
        decisions = [
            _make_test_decision("opp_1", PROMOTE, reasons=["strong_pain"]),
            _make_test_decision("opp_2", KILL, reasons=["too_generic"]),
            _make_test_decision("opp_3", NEEDS_MORE_EVIDENCE,
                              reasons=["need_customer_voice"]),
        ]

        result = rebuild_founder_decision_derived_artifacts(decisions=decisions)

        self.assertTrue(result.validation_passed,
                       f"Expected validation passed, got errors: {result.errors}")
        self.assertEqual(result.parking_lot_record_count, 0)

    def test_rebuild_with_existing_parking_lot_and_replaced_ids(self):
        """Rebuild with existing parking lot records correctly handles orphans."""
        decisions = [
            _make_test_decision(
                "opp_1", PROMOTE, reasons=["strong_pain"],
                decision_id="fd_active_1",
            ),
            _make_test_decision(
                "opp_2", PARK, reasons=["weak_evidence"],
                decision_id="fd_active_2",
            ),
        ]

        existing_pl = [
            _make_test_parking_lot_record(
                record_id="pl_active",
                source_decision_id="fd_active_2",  # Still valid
                linked_opportunity_id="opp_2",
            ),
            _make_test_parking_lot_record(
                record_id="pl_orphan",
                source_decision_id="fd_replaced_1",  # No longer exists
                linked_opportunity_id="opp_old",
            ),
        ]

        result = rebuild_founder_decision_derived_artifacts(
            decisions=decisions,
            existing_parking_lot_records=existing_pl,
            replaced_decision_ids={"fd_replaced_1"},
        )

        self.assertTrue(result.validation_passed,
                       f"Expected validation passed, got errors: {result.errors}")
        # Orphan should be detected
        self.assertEqual(result.orphaned_parking_lot_record_count, 1)
        # Orphan should NOT be in the final parking lot records
        self.assertNotIn("pl_orphan", [r.record_id for r in result.parking_lot_records])

    def test_rebuild_is_deterministic(self):
        """Rebuild is deterministic: same input yields same output."""
        decisions = [
            _make_test_decision("opp_1", PROMOTE, reasons=["strong_pain"]),
            _make_test_decision("opp_2", PARK, reasons=["weak_evidence"]),
        ]

        result1 = rebuild_founder_decision_derived_artifacts(decisions=decisions)
        result2 = rebuild_founder_decision_derived_artifacts(decisions=decisions)

        self.assertEqual(result1.feedback_mapping_count, result2.feedback_mapping_count)
        self.assertEqual(result1.parking_lot_record_count, result2.parking_lot_record_count)
        self.assertEqual(result1.validation_passed, result2.validation_passed)

        # Deep compare feedback mapping IDs
        map_ids1 = sorted(m.mapping_id for m in result1.feedback_mappings)
        map_ids2 = sorted(m.mapping_id for m in result2.feedback_mappings)
        self.assertEqual(map_ids1, map_ids2)


# ---------------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------------


class InputValidationTests(unittest.TestCase):
    """Test 14-16: Input validation behavior."""

    def test_validate_rebuild_inputs_accepts_valid_decisions(self):
        """Validate rebuild inputs accepts valid decisions."""
        decisions = [
            _make_test_decision("opp_1", PROMOTE),
        ]

        normalized, pl_records, errors, warnings = validate_rebuild_inputs(
            decisions=decisions,
        )

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(normalized), 1)

    def test_validate_rebuild_inputs_rejects_invalid_decision(self):
        """Validate rebuild inputs rejects decisions with invalid fields."""
        decisions = [
            {
                "decision_id": "",
                "opportunity_id": "",
                "evidence_pack_id": "",
                "decision": "INVALID",
                "reasons": [],
                "notes": "",
                "confidence": 0.5,
                "linked_evidence_ids": [],
                "linked_source_signal_ids": [],
                "linked_source_urls": ["https://example.com/test"],
                "decided_by": "founder",
                "decided_at": "",
                "schema_version": "founder_decision_v2.v1",
                "auto_promote": False,
                "founder_decision_authority": "founder_decision_record_only",
            },
        ]

        normalized, pl_records, errors, warnings = validate_rebuild_inputs(
            decisions=decisions,
        )

        self.assertGreater(len(errors), 0)

    def test_validate_rebuild_inputs_rejects_auto_promote(self):
        """Validate rebuild inputs rejects decisions with auto_promote=True."""
        decision = _make_test_decision("opp_1", PROMOTE)
        decision["auto_promote"] = True

        normalized, pl_records, errors, warnings = validate_rebuild_inputs(
            decisions=[decision],
        )

        self.assertGreater(len(errors), 0)
        # Error may come from FounderDecisionV2 validation (uses "auto-promote"
        # with hyphen) or from our own advisory-only check (uses "auto_promote"
        # with underscore). Accept either form.
        auto_error = any(
            ("auto_promote" in e.lower() or "auto-promote" in e.lower())
            for e in errors
        )
        self.assertTrue(auto_error,
                       f"Expected auto-promote error, got: {errors}")

    def test_validate_rebuild_inputs_rejects_wrong_authority(self):
        """Validate rebuild inputs rejects decisions with wrong authority."""
        decision = _make_test_decision("opp_1", PROMOTE)
        decision["founder_decision_authority"] = "autonomous"

        normalized, pl_records, errors, warnings = validate_rebuild_inputs(
            decisions=[decision],
        )

        self.assertGreater(len(errors), 0)
        self.assertTrue(any("authority" in e.lower() for e in errors))

    def test_empty_decisions_produces_empty_rebuild(self):
        """Empty decision list produces empty rebuild."""
        result = rebuild_founder_decision_derived_artifacts(decisions=[])

        self.assertTrue(result.validation_passed)
        self.assertEqual(result.active_founder_decision_count, 0)
        self.assertEqual(result.feedback_mapping_count, 0)
        self.assertFalse(result.preference_profile_present)
        self.assertEqual(result.parking_lot_record_count, 0)

    def test_plan_reflects_expected_counts(self):
        """DerivedArtifactRebuildPlan reflects expected counts."""
        # Build proper FounderDecisionV2 objects via create_founder_decision
        d1 = create_founder_decision(
            opportunity_id="opp_1",
            evidence_pack_id="ep_opp_1",
            decision=PROMOTE,
            reasons=["strong_pain"],
            linked_source_urls=["https://example.com/opp_1"],
        )
        d2 = create_founder_decision(
            opportunity_id="opp_2",
            evidence_pack_id="ep_opp_2",
            decision=PARK,
            reasons=["weak_evidence"],
            linked_source_urls=["https://example.com/opp_2"],
        )
        d3 = create_founder_decision(
            opportunity_id="opp_3",
            evidence_pack_id="ep_opp_3",
            decision=KILL,
            reasons=["too_generic"],
            linked_source_urls=["https://example.com/opp_3"],
        )

        plan = plan_derived_artifact_rebuild(
            decisions=[d1, d2, d3],
        )

        self.assertTrue(plan.validation_passed)
        self.assertEqual(plan.active_decision_count, 3)
        self.assertEqual(plan.expected_feedback_mapping_count, 3)
        self.assertTrue(plan.expected_preference_profile_present)
        self.assertEqual(plan.parking_lot_new_records_to_add, 1)  # Only PARK


# ---------------------------------------------------------------------------
# Advisory and no-live flags tests
# ---------------------------------------------------------------------------


class AdvisoryAndNoLiveTests(unittest.TestCase):
    """Verify advisory_only, no_live_api, no_live_llm flags always True."""

    def test_parking_lot_cleanup_result_flags(self):
        result = ParkingLotCleanupResult()
        self.assertTrue(result.advisory_only)
        self.assertTrue(result.no_live_api)
        self.assertTrue(result.no_live_llm)

    def test_derived_artifact_rebuild_result_flags(self):
        result = DerivedArtifactRebuildResult()
        self.assertTrue(result.advisory_only)
        self.assertTrue(result.no_live_api)
        self.assertTrue(result.no_live_llm)

    def test_derived_artifact_rebuild_plan_flags(self):
        plan = DerivedArtifactRebuildPlan()
        self.assertTrue(plan.advisory_only)
        self.assertTrue(plan.no_live_api)
        self.assertTrue(plan.no_live_llm)

    def test_rebuild_result_always_advisory(self):
        """Rebuild result always has advisory flags set to True."""
        decisions = [
            _make_test_decision("opp_1", PROMOTE),
        ]
        result = rebuild_founder_decision_derived_artifacts(decisions=decisions)
        self.assertTrue(result.advisory_only)
        self.assertTrue(result.no_live_api)
        self.assertTrue(result.no_live_llm)

    def test_cleanup_result_always_advisory(self):
        """Cleanup result always has advisory flags set to True."""
        pl_records = [_make_test_parking_lot_record("pl_1", "fd_1")]
        _, result = cleanup_orphaned_parking_lot_records(
            parking_lot_records=pl_records,
            active_decision_ids={"fd_1"},
        )
        self.assertTrue(result.advisory_only)
        self.assertTrue(result.no_live_api)
        self.assertTrue(result.no_live_llm)


# ---------------------------------------------------------------------------
# Rebuild with mixed decision types
# ---------------------------------------------------------------------------


class MixedDecisionRebuildTests(unittest.TestCase):
    """Test rebuild with all 5 decision types."""

    def test_all_five_decision_types(self):
        """Rebuild handles all five decision types correctly."""
        decisions = [
            _make_test_decision("opp_1", PROMOTE, reasons=["strong_pain"]),
            _make_test_decision("opp_2", PARK, reasons=["weak_evidence"]),
            _make_test_decision("opp_3", KILL, reasons=["too_generic"]),
            _make_test_decision("opp_4", REVISIT_LATER,
                              reasons=["waiting_for_more_signals"]),
            _make_test_decision("opp_5", NEEDS_MORE_EVIDENCE,
                              reasons=["need_customer_voice"]),
        ]

        result = rebuild_founder_decision_derived_artifacts(decisions=decisions)

        self.assertTrue(result.validation_passed,
                       f"Expected validation passed, got errors: {result.errors}")
        self.assertEqual(result.active_founder_decision_count, 5)
        self.assertEqual(result.feedback_mapping_count, 5)
        self.assertTrue(result.preference_profile_present)

        # Only PARK and REVISIT_LATER go to parking lot
        self.assertEqual(result.parking_lot_record_count, 2)

        # Verify preference profile counts
        self.assertIsNotNone(result.preference_profile)
        self.assertEqual(result.preference_profile.decision_count, 5)
        self.assertEqual(result.preference_profile.promote_count, 1)
        self.assertEqual(result.preference_profile.park_count, 1)
        self.assertEqual(result.preference_profile.kill_count, 1)
        self.assertEqual(result.preference_profile.revisit_count, 1)
        self.assertEqual(result.preference_profile.needs_more_evidence_count, 1)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()
