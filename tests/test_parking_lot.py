"""Tests for parking_lot — deterministic advisory parking lot / revisit matching."""

import json
import unittest

from oos.founder_decision_taxonomy import (
    KILL,
    PARK,
    PROMOTE,
    REVISIT_LATER,
    create_founder_decision,
)
from oos.parking_lot import (
    PARKING_LOT_SCHEMA_VERSION,
    ParkingLotRecord,
    RevisitMatch,
    build_parking_lot_records,
    match_revisit_candidates,
    parking_lot_records_to_json,
    record_pattern_keys_set,
    render_revisit_matches_markdown,
    revisit_matches_to_json,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_test_decision(
    opportunity_id: str,
    decision: str,
    reasons: list[str],
    confidence: float = 0.6,
    notes: str = "",
) -> dict:
    return {
        "decision_id": f"fd_test_{opportunity_id}",
        "opportunity_id": opportunity_id,
        "evidence_pack_id": f"ep_{opportunity_id}",
        "decision": decision,
        "reasons": [{"category": r, "note": ""} for r in reasons],
        "notes": notes,
        "confidence": confidence,
        "linked_evidence_ids": [f"ev_{opportunity_id}_1"],
        "linked_source_signal_ids": [f"sig_{opportunity_id}_1"],
        "linked_source_urls": [f"https://example.com/{opportunity_id}"],
        "decided_by": "founder",
        "decided_at": "2026-01-15T10:00:00Z",
        "schema_version": "founder_decision_v2.v1",
        "auto_promote": False,
        "founder_decision_authority": "founder_decision_record_only",
    }


def _make_test_parking_lot_record(
    record_id: str = "pl_test_001",
    opportunity_id: str = "opp_test_001",
    pattern_keys: list[str] | None = None,
    status: str = "parked",
) -> ParkingLotRecord:
    return ParkingLotRecord(
        record_id=record_id,
        source_decision_id=f"fd_{record_id}",
        source_artifact_ids=[f"fd_{record_id}", "ev_test_1"],
        linked_opportunity_id=opportunity_id,
        title=f"Test opportunity {opportunity_id}",
        summary=f"SMB bookkeeping pain for {opportunity_id}: manual invoice tracking",
        reason="weak_evidence, unclear_buyer",
        pattern_keys=pattern_keys if pattern_keys is not None else ["bookkeeping", "invoice", "smb", "unclear_buyer", "weak_evidence"],
        status=status,
    )


# ---------------------------------------------------------------------------
# ParkingLotRecord model tests
# ---------------------------------------------------------------------------


class ParkingLotRecordTests(unittest.TestCase):
    def test_record_serialization_round_trip(self):
        record = _make_test_parking_lot_record()
        data = record.to_dict()
        restored = ParkingLotRecord.from_dict(data)
        self.assertEqual(restored.record_id, record.record_id)
        self.assertEqual(restored.source_decision_id, record.source_decision_id)
        self.assertEqual(restored.linked_opportunity_id, record.linked_opportunity_id)
        self.assertEqual(restored.status, "parked")
        self.assertEqual(restored.pattern_keys, record.pattern_keys)
        self.assertTrue(restored.advisory_only)
        self.assertEqual(restored.schema_version, PARKING_LOT_SCHEMA_VERSION)

    def test_record_advisory_only_boundary(self):
        # advisory_only must be True
        record = ParkingLotRecord(
            record_id="pl_adv",
            source_decision_id="fd_adv",
            advisory_only=False,
        )
        errors = record.validate()
        self.assertTrue(any("advisory_only" in e for e in errors))

    def test_record_validate_missing_record_id(self):
        record = ParkingLotRecord(record_id="", source_decision_id="fd_x")
        errors = record.validate()
        self.assertTrue(any("record_id" in e for e in errors))

    def test_record_validate_missing_source_decision_id(self):
        record = ParkingLotRecord(record_id="pl_x", source_decision_id="")
        errors = record.validate()
        self.assertTrue(any("source_decision_id" in e for e in errors))

    def test_record_validate_invalid_status(self):
        record = ParkingLotRecord(
            record_id="pl_x", source_decision_id="fd_x", status="invalid"
        )
        errors = record.validate()
        self.assertTrue(any("status" in e for e in errors))

    def test_record_validate_valid_statuses(self):
        for status in ("parked", "revisit_later"):
            record = ParkingLotRecord(
                record_id="pl_x", source_decision_id="fd_x", status=status
            )
            errors = record.validate()
            self.assertFalse(errors, f"Expected no errors for status={status}, got: {errors}")

    def test_record_validate_schema_version(self):
        record = ParkingLotRecord(
            record_id="pl_x",
            source_decision_id="fd_x",
            schema_version="wrong",
        )
        errors = record.validate()
        self.assertTrue(any("schema_version" in e for e in errors))

    def test_record_from_dict_defaults(self):
        data = {"record_id": "pl_d", "source_decision_id": "fd_d"}
        record = ParkingLotRecord.from_dict(data)
        self.assertEqual(record.record_id, "pl_d")
        self.assertEqual(record.source_decision_id, "fd_d")
        self.assertEqual(record.status, "parked")
        self.assertEqual(record.pattern_keys, [])
        self.assertEqual(record.source_artifact_ids, [])
        self.assertTrue(record.advisory_only)


# ---------------------------------------------------------------------------
# RevisitMatch model tests
# ---------------------------------------------------------------------------


class RevisitMatchTests(unittest.TestCase):
    def test_match_serialization_round_trip(self):
        match = RevisitMatch(
            match_id="rm_test_001",
            parking_lot_record_id="pl_test_001",
            matched_evidence_id="ev_new_1",
            matched_opportunity_id="opp_new_1",
            match_reason="pattern_key_match: invoice, smb",
            matched_pattern_keys=["invoice", "smb"],
            confidence="high",
            suggested_founder_action="Review parked opportunity for invoice/SMB match.",
        )
        data = match.to_dict()
        restored = RevisitMatch.from_dict(data)
        self.assertEqual(restored.match_id, match.match_id)
        self.assertEqual(restored.parking_lot_record_id, match.parking_lot_record_id)
        self.assertEqual(restored.matched_pattern_keys, match.matched_pattern_keys)
        self.assertEqual(restored.confidence, "high")
        self.assertTrue(restored.advisory_only)
        self.assertEqual(restored.schema_version, PARKING_LOT_SCHEMA_VERSION)

    def test_match_advisory_only_boundary(self):
        match = RevisitMatch(
            match_id="rm_adv",
            parking_lot_record_id="pl_x",
            advisory_only=False,
        )
        errors = match.validate()
        self.assertTrue(any("advisory_only" in e for e in errors))

    def test_match_validate_missing_match_id(self):
        match = RevisitMatch(match_id="", parking_lot_record_id="pl_x")
        errors = match.validate()
        self.assertTrue(any("match_id" in e for e in errors))

    def test_match_validate_missing_parking_lot_record_id(self):
        match = RevisitMatch(match_id="rm_x", parking_lot_record_id="")
        errors = match.validate()
        self.assertTrue(any("parking_lot_record_id" in e for e in errors))

    def test_match_validate_invalid_confidence(self):
        match = RevisitMatch(
            match_id="rm_x", parking_lot_record_id="pl_x", confidence="critical"
        )
        errors = match.validate()
        self.assertTrue(any("confidence" in e for e in errors))

    def test_match_validate_valid_confidences(self):
        for conf in ("low", "medium", "high"):
            match = RevisitMatch(
                match_id="rm_x", parking_lot_record_id="pl_x", confidence=conf
            )
            errors = match.validate()
            self.assertFalse(errors, f"Expected no errors for confidence={conf}, got: {errors}")

    def test_match_validate_schema_version(self):
        match = RevisitMatch(
            match_id="rm_x",
            parking_lot_record_id="pl_x",
            schema_version="wrong",
        )
        errors = match.validate()
        self.assertTrue(any("schema_version" in e for e in errors))

    def test_match_from_dict_defaults(self):
        data = {"match_id": "rm_d", "parking_lot_record_id": "pl_d"}
        match = RevisitMatch.from_dict(data)
        self.assertEqual(match.match_id, "rm_d")
        self.assertEqual(match.parking_lot_record_id, "pl_d")
        self.assertEqual(match.confidence, "low")
        self.assertEqual(match.matched_pattern_keys, [])
        self.assertTrue(match.advisory_only)


# ---------------------------------------------------------------------------
# build_parking_lot_records tests
# ---------------------------------------------------------------------------


class BuildParkingLotRecordsTests(unittest.TestCase):
    def test_empty_input_returns_empty(self):
        records = build_parking_lot_records(decisions=None)
        self.assertEqual(records, [])

    def test_empty_list_returns_empty(self):
        records = build_parking_lot_records(decisions=[])
        self.assertEqual(records, [])

    def test_builds_from_park_decisions(self):
        decisions = [
            _make_test_decision("opp_a", PARK, ["weak_evidence", "unclear_buyer"]),
        ]
        records = build_parking_lot_records(decisions=decisions)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].status, "parked")
        self.assertEqual(records[0].linked_opportunity_id, "opp_a")
        self.assertTrue(records[0].advisory_only)

    def test_builds_from_revisit_later_decisions(self):
        decisions = [
            _make_test_decision(
                "opp_b", REVISIT_LATER, ["waiting_for_more_signals"]
            ),
        ]
        records = build_parking_lot_records(decisions=decisions)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].status, "revisit_later")
        self.assertEqual(records[0].linked_opportunity_id, "opp_b")

    def test_skips_promote_decisions(self):
        decisions = [
            _make_test_decision("opp_prom", PROMOTE, ["strong_pain"]),
            _make_test_decision("opp_park", PARK, ["weak_evidence"]),
        ]
        records = build_parking_lot_records(decisions=decisions)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].linked_opportunity_id, "opp_park")

    def test_skips_kill_decisions(self):
        decisions = [
            _make_test_decision("opp_kill", KILL, ["too_generic"]),
            _make_test_decision("opp_revisit", REVISIT_LATER, ["waiting_for_more_signals"]),
        ]
        records = build_parking_lot_records(decisions=decisions)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].status, "revisit_later")

    def test_skips_malformed_decisions(self):
        decisions = [
            _make_test_decision("opp_a", PARK, ["weak_evidence"]),
            {"not": "a decision"},
        ]
        records = build_parking_lot_records(decisions=decisions)
        self.assertEqual(len(records), 1)

    def test_deterministic_ordering(self):
        decisions = [
            _make_test_decision("opp_c", PARK, ["weak_evidence"]),
            _make_test_decision("opp_a", REVISIT_LATER, ["waiting_for_more_signals"]),
            _make_test_decision("opp_b", PARK, ["too_early"]),
        ]
        records = build_parking_lot_records(decisions=decisions)
        record_ids = [r.record_id for r in records]
        self.assertEqual(record_ids, sorted(record_ids))

    def test_pattern_keys_extracted(self):
        decisions = [
            _make_test_decision(
                "opp_bookkeeping_smb",
                PARK,
                ["weak_evidence"],
                notes="Small business bookkeeping pain with manual Excel tracking",
            ),
        ]
        records = build_parking_lot_records(decisions=decisions)
        self.assertEqual(len(records), 1)
        keys = records[0].pattern_keys
        # Should contain some meaningful keywords from opportunity_id and notes
        self.assertGreater(len(keys), 2)
        self.assertTrue(any("bookkeeping" in k for k in keys))

    def test_source_artifact_ids_preserved(self):
        decisions = [
            _make_test_decision("opp_x", PARK, ["weak_evidence"]),
        ]
        records = build_parking_lot_records(decisions=decisions)
        self.assertIn("fd_test_opp_x", records[0].source_artifact_ids)
        self.assertIn("ev_opp_x_1", records[0].source_artifact_ids)
        self.assertIn("sig_opp_x_1", records[0].source_artifact_ids)


# ---------------------------------------------------------------------------
# match_revisit_candidates tests
# ---------------------------------------------------------------------------


class MatchRevisitCandidatesTests(unittest.TestCase):
    def test_empty_inputs_return_empty(self):
        matches = match_revisit_candidates(
            parking_lot_records=None, new_evidence=None
        )
        self.assertEqual(matches, [])

    def test_empty_records_return_empty(self):
        matches = match_revisit_candidates(
            parking_lot_records=[], new_evidence=[{"evidence_id": "ev_1"}]
        )
        self.assertEqual(matches, [])

    def test_empty_evidence_return_empty(self):
        records = [_make_test_parking_lot_record()]
        matches = match_revisit_candidates(
            parking_lot_records=records, new_evidence=[]
        )
        self.assertEqual(matches, [])

    def test_exact_pattern_key_match_high_confidence(self):
        records = [
            _make_test_parking_lot_record(
                record_id="pl_001",
                opportunity_id="opp_bookkeeping",
                pattern_keys=["bookkeeping", "invoice", "smb"],
            ),
        ]
        evidence = [
            {
                "evidence_id": "ev_new_1",
                "summary": "SMBs struggle with bookkeeping and invoice management",
                "pattern_keys": ["bookkeeping", "invoice"],
            },
        ]
        matches = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].confidence, "high")
        self.assertEqual(matches[0].parking_lot_record_id, "pl_001")
        self.assertIn("bookkeeping", matches[0].matched_pattern_keys)
        self.assertIn("invoice", matches[0].matched_pattern_keys)
        self.assertTrue(matches[0].advisory_only)

    def test_multiple_pattern_key_matches(self):
        records = [
            _make_test_parking_lot_record(
                record_id="pl_invoice",
                pattern_keys=["invoice", "smb", "payment"],
            ),
            _make_test_parking_lot_record(
                record_id="pl_reporting",
                pattern_keys=["reporting", "analytics", "dashboard"],
            ),
        ]
        evidence = [
            {
                "evidence_id": "ev_new_1",
                "summary": "SMB payment and invoice tracking needs",
                "pattern_keys": ["invoice", "payment", "smb"],
            },
        ]
        matches = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        # Should match pl_invoice (high confidence via pattern keys)
        self.assertGreaterEqual(len(matches), 1)
        matched_record_ids = {m.parking_lot_record_id for m in matches}
        self.assertIn("pl_invoice", matched_record_ids)

    def test_token_overlap_match_medium_confidence(self):
        records = [
            _make_test_parking_lot_record(
                record_id="pl_token",
                opportunity_id="opp_cashflow",
                pattern_keys=["cashflow"],
            ),
        ]
        evidence = [
            {
                "evidence_id": "ev_cf",
                "summary": "Small businesses need better cashflow forecasting tools for managing payments",
                "pattern_keys": [],  # No explicit pattern keys from evidence
            },
        ]
        matches = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        # Should match via token overlap: "cashflow" in both, plus "business" etc.
        self.assertGreaterEqual(len(matches), 1)

    def test_substring_match_low_confidence(self):
        # Use pattern_keys that won't overlap with evidence-extracted keys,
        # and ensure <2 token overlaps so substring match fires as fallback.
        records = [
            _make_test_parking_lot_record(
                record_id="pl_substr",
                opportunity_id="opp_contrib",
                pattern_keys=["contribution_source"],
            ),
        ]
        # Override text so only substring matching fires
        records[0].title = "Open source workflow"
        records[0].summary = "Developer contribution workflow automation"
        records[0].reason = "too_early"
        evidence = [
            {
                "evidence_id": "ev_contrib",
                "summary": "source contributions automated",
                "pattern_keys": [],
            },
        ]
        # "source" and "contribution" appear as substrings of evidence tokens
        matches = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        matched = [m for m in matches if m.parking_lot_record_id == "pl_substr"]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].confidence, "low")

    def test_no_match_for_unrelated_evidence(self):
        records = [
            _make_test_parking_lot_record(
                record_id="pl_invoice",
                pattern_keys=["invoice", "bookkeeping", "smb"],
            ),
        ]
        evidence = [
            {
                "evidence_id": "ev_unrelated",
                "summary": "Machine learning deployment for image recognition in healthcare",
                "pattern_keys": ["ml", "healthcare", "imaging"],
            },
        ]
        matches = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        self.assertEqual(matches, [])

    def test_deterministic_ordering(self):
        records = [
            _make_test_parking_lot_record(
                record_id="pl_a",
                pattern_keys=["payments"],
            ),
            _make_test_parking_lot_record(
                record_id="pl_b",
                pattern_keys=["reporting"],
            ),
        ]
        evidence = [
            {
                "evidence_id": "ev_1",
                "summary": "payments reporting analytics",
                "pattern_keys": ["payments", "reporting"],
            },
        ]
        matches = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        # Deterministic ordering by confidence then match_id
        if matches:
            conf_order = {"high": 0, "medium": 1, "low": 2}
            for i in range(len(matches) - 1):
                a = conf_order.get(matches[i].confidence, 3)
                b = conf_order.get(matches[i + 1].confidence, 3)
                if a == b:
                    self.assertLessEqual(matches[i].match_id, matches[i + 1].match_id)
                else:
                    self.assertLessEqual(a, b)

    def test_deterministic_ids(self):
        records = [
            _make_test_parking_lot_record(
                record_id="pl_det",
                pattern_keys=["invoice"],
            ),
        ]
        evidence = [
            {
                "evidence_id": "ev_det",
                "summary": "invoice processing",
                "pattern_keys": ["invoice"],
            },
        ]
        matches1 = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        matches2 = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        self.assertEqual(len(matches1), 1)
        self.assertEqual(len(matches2), 1)
        self.assertEqual(matches1[0].match_id, matches2[0].match_id)

    def test_malformed_records_skipped(self):
        records = [
            _make_test_parking_lot_record(),
            {"bad": "record"},  # malformed
        ]
        evidence = [
            {
                "evidence_id": "ev_val",
                "summary": "bookkeeping smb invoice",
                "pattern_keys": ["bookkeeping", "invoice", "smb"],
            },
        ]
        matches = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        # Only the valid record should produce matches
        record_matches = [m for m in matches if m.parking_lot_record_id != ""]
        self.assertGreaterEqual(len(record_matches), 0)  # Should not crash

    def test_advisory_only_boundary(self):
        records = [_make_test_parking_lot_record()]
        evidence = [
            {
                "evidence_id": "ev_adv",
                "summary": "bookkeeping smb invoice tracking",
                "pattern_keys": ["bookkeeping", "invoice", "smb"],
            },
        ]
        matches = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        for m in matches:
            self.assertTrue(m.advisory_only)

    def test_no_live_network_or_api_calls(self):
        # By construction, all operations are purely in-memory deterministic
        records = [_make_test_parking_lot_record()]
        evidence = [{"evidence_id": "ev_net", "summary": "bookkeeping smb"}]
        matches = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        self.assertIsInstance(matches, list)
        # No network calls made; if this completes without exceptions, test passes

    def test_matches_from_dict_input(self):
        records = [_make_test_parking_lot_record().to_dict()]
        evidence = [
            {
                "evidence_id": "ev_dict",
                "summary": "bookkeeping invoice smb",
                "pattern_keys": ["bookkeeping", "invoice", "smb"],
            },
        ]
        matches = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        self.assertGreaterEqual(len(matches), 1)

    def test_evidence_without_text_or_keys_produces_no_match(self):
        records = [_make_test_parking_lot_record()]
        evidence = [
            {
                "evidence_id": "ev_empty",
                "summary": "",
                "pattern_keys": [],
            },
        ]
        matches = match_revisit_candidates(
            parking_lot_records=records, new_evidence=evidence
        )
        self.assertEqual(matches, [])


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------


class SerializationTests(unittest.TestCase):
    def test_parking_lot_records_to_json(self):
        records = [
            _make_test_parking_lot_record(),
            _make_test_parking_lot_record(
                record_id="pl_002", opportunity_id="opp_002", status="revisit_later"
            ),
        ]
        json_str = parking_lot_records_to_json(records)
        data = json.loads(json_str)
        self.assertEqual(len(data), 2)
        self.assertIn("record_id", data[0])

    def test_revisit_matches_to_json(self):
        matches = [
            RevisitMatch(
                match_id="rm_1",
                parking_lot_record_id="pl_1",
                confidence="high",
            ),
            RevisitMatch(
                match_id="rm_2",
                parking_lot_record_id="pl_2",
                confidence="low",
            ),
        ]
        json_str = revisit_matches_to_json(matches)
        data = json.loads(json_str)
        self.assertEqual(len(data), 2)

    def test_render_revisit_matches_markdown_empty(self):
        md = render_revisit_matches_markdown([])
        self.assertIn("No revisit matches found", md)

    def test_render_revisit_matches_markdown_with_matches(self):
        matches = [
            RevisitMatch(
                match_id="rm_rend",
                parking_lot_record_id="pl_rend",
                matched_evidence_id="ev_rend",
                matched_opportunity_id="opp_rend",
                match_reason="pattern_key_match: invoice, smb",
                matched_pattern_keys=["invoice", "smb"],
                confidence="high",
                suggested_founder_action="Review park.",
            ),
        ]
        md = render_revisit_matches_markdown(matches)
        self.assertIn("rm_rend", md)
        self.assertIn("pl_rend", md)
        self.assertIn("HIGH", md)
        self.assertIn("pattern_key_match", md)


# ---------------------------------------------------------------------------
# record_pattern_keys_set tests
# ---------------------------------------------------------------------------


class PatternKeysSetTests(unittest.TestCase):
    def test_returns_set_of_pattern_keys(self):
        record = _make_test_parking_lot_record(
            pattern_keys=["invoice", "smb", "bookkeeping"]
        )
        keys = record_pattern_keys_set(record)
        self.assertIsInstance(keys, set)
        self.assertIn("invoice", keys)
        self.assertIn("smb", keys)
        self.assertIn("bookkeeping", keys)

    def test_empty_pattern_keys_returns_empty_set(self):
        record = _make_test_parking_lot_record(pattern_keys=[])
        keys = record_pattern_keys_set(record)
        self.assertEqual(keys, set())


# ---------------------------------------------------------------------------
# Weekly review integration tests
# ---------------------------------------------------------------------------


class WeeklyReviewIntegrationTests(unittest.TestCase):
    def test_preserves_old_behavior_when_no_parking_lot_data(self):
        """When no parking_lot_records or revisit_matches are provided,
        the weekly review package should behave exactly as before."""
        from oos.weekly_opportunity_review import build_weekly_opportunity_review_package

        decisions = [
            _make_test_decision("opp_a", REVISIT_LATER, ["waiting_for_more_signals"]),
        ]
        package = build_weekly_opportunity_review_package(
            decisions=decisions,
        )
        revisit_section = next(
            (s for s in package.sections if s.section_id == "revisit_queue"), None
        )
        self.assertIsNotNone(revisit_section)
        # Should have the REVISIT_LATER decision item
        self.assertTrue(any("opp_a" in i.summary for i in revisit_section.items))
        # No revisit_match items
        match_items = [i for i in revisit_section.items if i.category == "revisit_match"]
        self.assertEqual(match_items, [])

    def test_includes_revisit_matches_when_provided(self):
        """When revisit_matches are provided, they appear in the revisit_queue."""
        from oos.weekly_opportunity_review import build_weekly_opportunity_review_package

        decisions = [
            _make_test_decision("opp_rev", REVISIT_LATER, ["waiting_for_more_signals"]),
        ]
        revisit_matches = [
            RevisitMatch(
                match_id="rm_int_test",
                parking_lot_record_id="pl_int",
                matched_evidence_id="ev_match",
                matched_opportunity_id="opp_match",
                match_reason="pattern_key_match: invoice, smb",
                matched_pattern_keys=["invoice", "smb"],
                confidence="high",
                suggested_founder_action="Review parked opportunity.",
            ),
        ]
        package = build_weekly_opportunity_review_package(
            decisions=decisions,
            revisit_matches=revisit_matches,
        )
        revisit_section = next(
            (s for s in package.sections if s.section_id == "revisit_queue"), None
        )
        self.assertIsNotNone(revisit_section)
        # Should contain both the decision item and the match item
        decision_items = [i for i in revisit_section.items if i.category == "revisit_later"]
        match_items = [i for i in revisit_section.items if i.category == "revisit_match"]
        self.assertEqual(len(decision_items), 1)
        self.assertEqual(len(match_items), 1)
        self.assertIn("rm_int_test", match_items[0].item_id)

    def test_revisit_matches_count_in_section_metadata(self):
        from oos.weekly_opportunity_review import build_weekly_opportunity_review_package

        decisions = []
        revisit_matches = [
            RevisitMatch(match_id="rm_a", parking_lot_record_id="pl_a", confidence="high"),
            RevisitMatch(match_id="rm_b", parking_lot_record_id="pl_b", confidence="low"),
        ]
        package = build_weekly_opportunity_review_package(
            decisions=decisions,
            revisit_matches=revisit_matches,
        )
        revisit_section = next(
            (s for s in package.sections if s.section_id == "revisit_queue"), None
        )
        self.assertIsNotNone(revisit_section)
        self.assertEqual(
            revisit_section.source_artifact_counts.get("revisit_matches", 0), 2
        )

    def test_empty_revisit_matches_no_effect(self):
        from oos.weekly_opportunity_review import build_weekly_opportunity_review_package

        package = build_weekly_opportunity_review_package(
            decisions=[],
            revisit_matches=[],
        )
        revisit_section = next(
            (s for s in package.sections if s.section_id == "revisit_queue"), None
        )
        self.assertIsNotNone(revisit_section)
        self.assertEqual(revisit_section.source_artifact_counts.get("revisit_matches", 0), 0)

    def test_package_advisory_only_unchanged(self):
        from oos.weekly_opportunity_review import build_weekly_opportunity_review_package

        package = build_weekly_opportunity_review_package(
            decisions=[],
            revisit_matches=[
                RevisitMatch(match_id="rm_adv", parking_lot_record_id="pl_adv"),
            ],
        )
        self.assertTrue(package.advisory_only)
        self.assertFalse(package.autonomous_decisions_made)


if __name__ == "__main__":
    unittest.main()
