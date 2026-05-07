import json
from pathlib import Path
import unittest

from oos.founder_decision_taxonomy import (
    KILL,
    NEEDS_MORE_EVIDENCE,
    PARK,
    PROMOTE,
    REVISIT_LATER,
    create_founder_decision,
)
from oos.founder_feedback_mapping import (
    map_founder_decision_to_feedback,
    founder_feedback_mapping_from_dict,
    founder_feedback_mapping_to_dict,
)
from oos.founder_preference_profile import (
    FOUNDER_PREFERENCE_PROFILE_SCHEMA_VERSION,
    FounderPreferenceProfile,
    FounderPreferenceScoringHint,
    FounderPreferencePackageWarning,
    build_founder_preference_profile,
    founder_preference_profile_from_dict,
    founder_preference_profile_to_dict,
    profile_scoring_adjustment,
    profile_founder_package_warnings,
    validate_founder_preference_profile,
)


class FounderPreferenceProfileTests(unittest.TestCase):
    def _decision(self, decision: str, reasons: list[str], notes: str = ""):
        return create_founder_decision(
            opportunity_id="opp_cash_collection",
            evidence_pack_id="evidence_pack_cash_collection",
            decision=decision,
            reasons=reasons,
            linked_evidence_ids=["ev_2", "ev_1"],
            linked_source_signal_ids=["sig_2", "sig_1"],
            linked_source_urls=["https://example.com/b", "https://example.com/a"],
            confidence=0.7,
            decided_by="founder",
            decided_at="2026-05-06T00:00:00Z",
            notes=notes,
        )

    def _promote_cash(self):
        return self._decision(PROMOTE, ["strong_pain"], notes="cash_collection pain: unpaid invoices")

    def _kill_generic(self):
        return self._decision(KILL, ["too_generic"], notes="generic dashboard idea")

    def _kill_vendor(self):
        return self._decision(KILL, ["vendor_promo_false_positive"], notes="vendor promo")

    def _park_no_buyer(self):
        return self._decision(PARK, ["unclear_buyer"])

    def _needs_evidence(self):
        return self._decision(NEEDS_MORE_EVIDENCE, ["need_price_evidence"])

    def _revisit(self):
        return self._decision(REVISIT_LATER, ["waiting_for_more_signals"])

    def _mapping(self, decision):
        return map_founder_decision_to_feedback(decision)

    def test_build_empty_decision_list_produces_sparse_profile(self):
        profile = build_founder_preference_profile([])

        self.assertEqual(0, profile.decision_count)
        self.assertEqual([], profile.preferred_pain_types)
        self.assertEqual([], profile.recurring_kill_reasons)

    def test_build_single_promote_creates_preferred_pain_type(self):
        profile = build_founder_preference_profile([self._promote_cash()])

        self.assertEqual(1, profile.decision_count)
        self.assertEqual(1, profile.promote_count)
        self.assertIn("cash_collection", profile.preferred_pain_types)

    def test_build_single_kill_creates_rejected_pattern_and_reason(self):
        profile = build_founder_preference_profile(
            [self._kill_generic()],
            feedback_mappings=[self._mapping(self._kill_generic())],
        )

        self.assertEqual(1, profile.kill_count)
        self.assertIn("too_generic", profile.recurring_kill_reasons)
        self.assertIn("too_generic", profile.rejected_patterns)

    def test_build_vendor_kill_creates_vendor_rejected_pattern(self):
        profile = build_founder_preference_profile(
            [self._kill_vendor()],
            feedback_mappings=[self._mapping(self._kill_vendor())],
        )

        self.assertIn("vendor_promo_false_positive", profile.rejected_patterns)
        self.assertIn("vendor_promo_false_positive", profile.recurring_kill_reasons)

    def test_build_park_creates_evidence_gaps(self):
        profile = build_founder_preference_profile(
            [self._park_no_buyer()],
            feedback_mappings=[self._mapping(self._park_no_buyer())],
        )

        self.assertEqual(1, profile.park_count)
        # unclear_buyer reason maps to "unclear_buyer" gap
        self.assertIn("unclear_buyer", profile.areas_needing_more_evidence)

    def test_build_needs_more_evidence_creates_gaps(self):
        profile = build_founder_preference_profile(
            [self._needs_evidence()],
            feedback_mappings=[self._mapping(self._needs_evidence())],
        )

        self.assertEqual(1, profile.needs_more_evidence_count)
        self.assertIn("need_price_evidence", profile.areas_needing_more_evidence)

    def test_build_revisit_is_counted(self):
        profile = build_founder_preference_profile([self._revisit()])

        self.assertEqual(1, profile.revisit_count)

    def test_build_mixed_decisions_aggregates_correctly(self):
        decisions = [
            self._promote_cash(),
            self._kill_generic(),
            self._kill_vendor(),
            self._park_no_buyer(),
            self._needs_evidence(),
            self._revisit(),
        ]
        mappings = [
            self._mapping(d)
            for d in decisions
        ]
        profile = build_founder_preference_profile(decisions, mappings)

        self.assertEqual(6, profile.decision_count)
        self.assertEqual(1, profile.promote_count)
        self.assertEqual(2, profile.kill_count)
        self.assertEqual(1, profile.park_count)
        self.assertEqual(1, profile.needs_more_evidence_count)
        self.assertEqual(1, profile.revisit_count)
        self.assertIn("too_generic", profile.recurring_kill_reasons)
        self.assertIn("vendor_promo_false_positive", profile.recurring_kill_reasons)
        self.assertIn("cash_collection", profile.preferred_pain_types)

    def test_serialization_round_trip_works(self):
        profile = build_founder_preference_profile(
            [self._promote_cash(), self._kill_generic()],
            feedback_mappings=[
                self._mapping(self._promote_cash()),
                self._mapping(self._kill_generic()),
            ],
        )
        data = founder_preference_profile_to_dict(profile)
        json.dumps(data)

        restored = founder_preference_profile_from_dict(data)

        self.assertEqual(profile.profile_id, restored.profile_id)
        self.assertEqual(profile.preferred_pain_types, restored.preferred_pain_types)
        self.assertEqual(profile.rejected_patterns, restored.rejected_patterns)
        self.assertEqual(profile.promoted_patterns, restored.promoted_patterns)
        self.assertEqual(profile.recurring_kill_reasons, restored.recurring_kill_reasons)
        self.assertEqual(profile.areas_needing_more_evidence, restored.areas_needing_more_evidence)
        self.assertEqual(profile.decision_count, restored.decision_count)
        self.assertEqual(profile.promote_count, restored.promote_count)
        self.assertEqual(profile.kill_count, restored.kill_count)

    def test_decision_count_must_match_sum(self):
        decisions = [self._promote_cash(), self._kill_generic()]
        profile = build_founder_preference_profile(decisions)

        self.assertEqual(2, profile.decision_count)
        self.assertEqual(
            profile.promote_count + profile.kill_count + profile.park_count
            + profile.revisit_count + profile.needs_more_evidence_count,
            profile.decision_count,
        )

    def test_validation_rejects_missing_profile_id(self):
        profile = build_founder_preference_profile([self._promote_cash()])
        data = founder_preference_profile_to_dict(profile)
        data["profile_id"] = ""

        with self.assertRaises(ValueError):
            founder_preference_profile_from_dict(data)

    def test_validation_rejects_wrong_schema_version(self):
        profile = build_founder_preference_profile([self._promote_cash()])
        data = founder_preference_profile_to_dict(profile)
        data["schema_version"] = "wrong_version"

        with self.assertRaises(ValueError):
            founder_preference_profile_from_dict(data)

    def test_validation_rejects_ml_training_claim(self):
        profile = build_founder_preference_profile([self._promote_cash()])
        data = founder_preference_profile_to_dict(profile)
        data["ml_training_claimed"] = True

        with self.assertRaises(ValueError):
            founder_preference_profile_from_dict(data)

    def test_validation_rejects_autonomous_decisions(self):
        profile = build_founder_preference_profile([self._promote_cash()])
        data = founder_preference_profile_to_dict(profile)
        data["autonomous_decisions_made"] = True

        with self.assertRaises(ValueError):
            founder_preference_profile_from_dict(data)

    def test_validation_rejects_invalid_pain_type(self):
        profile = build_founder_preference_profile([self._promote_cash()])
        data = founder_preference_profile_to_dict(profile)
        data["preferred_pain_types"] = ["invalid_pain_type"]

        with self.assertRaises(ValueError):
            founder_preference_profile_from_dict(data)

    def test_validation_rejects_negative_counts(self):
        profile = build_founder_preference_profile([self._promote_cash()])
        data = founder_preference_profile_to_dict(profile)
        data["promote_count"] = -1

        with self.assertRaises(ValueError):
            founder_preference_profile_from_dict(data)

    def test_scoring_adjustment_boost_preferred_pain(self):
        profile = build_founder_preference_profile([self._promote_cash()])

        hint = profile_scoring_adjustment(profile, pain_type="cash_collection")

        self.assertEqual("boost_preferred_pain", hint.kind)
        self.assertGreater(hint.adjustment, 0.0)

    def test_scoring_adjustment_suppress_kill_reason(self):
        profile = build_founder_preference_profile([self._kill_generic()])

        hint = profile_scoring_adjustment(
            profile,
            pain_type="other",
            matched_kill_reason="too_generic",
        )

        self.assertEqual("suppress_killed_pattern", hint.kind)
        self.assertLess(hint.adjustment, 0.0)

    def test_scoring_adjustment_suppress_rejected_pattern(self):
        profile = build_founder_preference_profile(
            [self._kill_vendor()],
            feedback_mappings=[self._mapping(self._kill_vendor())],
        )

        hint = profile_scoring_adjustment(
            profile,
            pain_type="other",
            matched_rejected_pattern="vendor_promo_false_positive",
        )

        self.assertEqual("suppress_rejected_pattern", hint.kind)
        self.assertLess(hint.adjustment, 0.0)

    def test_scoring_adjustment_require_price_evidence(self):
        profile = build_founder_preference_profile(
            [self._needs_evidence()],
            feedback_mappings=[self._mapping(self._needs_evidence())],
        )

        hint = profile_scoring_adjustment(
            profile,
            pain_type="other",
            has_price_evidence=False,
        )

        self.assertEqual("require_price_evidence", hint.kind)
        self.assertLess(hint.adjustment, 0.0)

    def test_scoring_adjustment_no_triggers_returns_neutral(self):
        profile = build_founder_preference_profile([self._promote_cash()])

        hint = profile_scoring_adjustment(
            profile,
            pain_type="bookkeeping",
        )

        self.assertEqual("no_advisory_change", hint.kind)
        self.assertEqual(0.0, hint.adjustment)

    def test_scoring_adjustment_adjustment_clamped(self):
        profile = build_founder_preference_profile(
            [self._kill_generic(), self._kill_vendor(), self._park_no_buyer()],
            feedback_mappings=[
                self._mapping(self._kill_generic()),
                self._mapping(self._kill_vendor()),
                self._mapping(self._park_no_buyer()),
            ],
        )

        hint = profile_scoring_adjustment(
            profile,
            pain_type="other",
            matched_kill_reason="too_generic",
            matched_rejected_pattern="vendor_promo_false_positive",
            has_price_evidence=False,
            has_buyer_clarity=False,
        )

        self.assertGreaterEqual(hint.adjustment, -0.20)
        self.assertLessEqual(hint.adjustment, 0.10)

    def test_package_warnings_no_promotes_generates_warning(self):
        profile = build_founder_preference_profile(
            [self._kill_generic(), self._kill_vendor(), self._park_no_buyer()],
            feedback_mappings=[
                self._mapping(self._kill_generic()),
                self._mapping(self._kill_vendor()),
                self._mapping(self._park_no_buyer()),
            ],
        )

        warnings = profile_founder_package_warnings(profile)

        self.assertTrue(any("many_kills_no_promote" in w.warning_id for w in warnings))
        self.assertTrue(any("no_promoted_opportunities" in w.warning_id for w in warnings))

    def test_package_warnings_no_preferred_pain_types(self):
        profile = build_founder_preference_profile(
            [self._kill_generic()],
            feedback_mappings=[self._mapping(self._kill_generic())],
        )

        warnings = profile_founder_package_warnings(profile)

        self.assertTrue(any("no_preferred_pain_types" in w.warning_id for w in warnings))

    def test_package_warnings_recurring_kill_patterns(self):
        profile = build_founder_preference_profile(
            [self._kill_generic(), self._kill_vendor()],
            feedback_mappings=[
                self._mapping(self._kill_generic()),
                self._mapping(self._kill_vendor()),
            ],
        )

        warnings = profile_founder_package_warnings(profile)

        self.assertTrue(any("recurring_kill_patterns" in w.warning_id for w in warnings))
        for w in warnings:
            if "recurring_kill_patterns" in w.warning_id:
                self.assertIn("too_generic", w.message)
                self.assertIn("vendor_promo_false_positive", w.message)

    def test_package_warnings_many_needs_evidence(self):
        decisions = [
            self._needs_evidence(),
            self._park_no_buyer(),
        ]
        decisions.append(
            create_founder_decision(
                opportunity_id="opp_other",
                evidence_pack_id="evidence_pack_other",
                decision=NEEDS_MORE_EVIDENCE,
                reasons=["need_buyer_clarity"],
                linked_evidence_ids=["ev_3"],
                linked_source_signal_ids=["sig_3"],
                linked_source_urls=["https://example.com/c"],
                confidence=0.5,
                decided_by="founder",
                decided_at="2026-05-06T00:00:00Z",
            )
        )
        mappings = [self._mapping(d) for d in decisions]
        profile = build_founder_preference_profile(decisions, mappings)

        self.assertEqual(2, profile.needs_more_evidence_count)
        self.assertEqual(1, profile.park_count)

        warnings = profile_founder_package_warnings(profile)

        self.assertTrue(any("many_needs_evidence" in w.warning_id for w in warnings))

    def test_warnings_serialize_correctly(self):
        profile = build_founder_preference_profile(
            [self._kill_generic()],
            feedback_mappings=[self._mapping(self._kill_generic())],
        )
        warnings = profile_founder_package_warnings(profile)

        for w in warnings:
            data = w.to_dict()
            json.dumps(data)

    def test_scoring_hint_serializes(self):
        profile = build_founder_preference_profile([self._promote_cash()])
        hint = profile_scoring_adjustment(profile, pain_type="cash_collection")

        data = hint.to_dict()
        json.dumps(data)

    def test_build_accepts_dict_inputs(self):
        promote_dict = self._promote_cash().to_dict()
        kill_dict = self._kill_generic().to_dict()

        profile = build_founder_preference_profile([promote_dict, kill_dict])

        self.assertEqual(2, profile.decision_count)

    def test_build_accepts_feedback_mapping_dicts(self):
        mapping = self._mapping(self._promote_cash())
        mapping_dict = founder_feedback_mapping_to_dict(mapping)

        profile = build_founder_preference_profile(
            [self._promote_cash()],
            feedback_mappings=[mapping_dict],
        )

        self.assertEqual(1, len(profile.source_feedback_mapping_ids))
        self.assertEqual(mapping.mapping_id, profile.source_feedback_mapping_ids[0])

    def test_deterministic_output(self):
        decisions = [
            self._promote_cash(),
            self._kill_generic(),
            self._park_no_buyer(),
        ]
        mappings = [self._mapping(d) for d in decisions]

        profile1 = build_founder_preference_profile(decisions, mappings)
        profile2 = build_founder_preference_profile(decisions, mappings)

        # All fields except generated_at must match
        self.assertEqual(profile1.profile_id, profile2.profile_id)
        self.assertEqual(profile1.preferred_pain_types, profile2.preferred_pain_types)
        self.assertEqual(profile1.rejected_patterns, profile2.rejected_patterns)
        self.assertEqual(profile1.promoted_patterns, profile2.promoted_patterns)
        self.assertEqual(profile1.recurring_kill_reasons, profile2.recurring_kill_reasons)
        self.assertEqual(profile1.areas_needing_more_evidence, profile2.areas_needing_more_evidence)
        self.assertEqual(profile1.source_decision_ids, profile2.source_decision_ids)
        self.assertEqual(profile1.decision_count, profile2.decision_count)

    def test_no_live_network_or_llm_calls_are_present(self):
        source = Path("src/oos/founder_preference_profile.py").read_text(encoding="utf-8")

        self.assertNotIn("provider.complete", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib.request", source)

    def test_rejected_patterns_include_direct_reasons_from_kill_decisions(self):
        profile = build_founder_preference_profile(
            [self._decision(KILL, ["no_buyer"]), self._decision(KILL, ["disguised_consulting"])],
        )

        self.assertIn("no_buyer", profile.rejected_patterns)
        self.assertIn("disguised_consulting", profile.rejected_patterns)

    def test_promoted_patterns_from_mappings(self):
        mapping = self._mapping(self._promote_cash())
        profile = build_founder_preference_profile(
            [self._promote_cash()],
            feedback_mappings=[mapping],
        )

        self.assertIn("promoted_pattern", profile.promoted_patterns)
        self.assertIn("strong_pain_confirmed", profile.promoted_patterns)


if __name__ == "__main__":
    unittest.main()
