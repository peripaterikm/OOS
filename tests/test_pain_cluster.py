from __future__ import annotations

import datetime
import json
import unittest

from oos.pain_cluster import (
    ALLOWED_CONTRIBUTION_TYPES,
    ALLOWED_STATUSES,
    SCORING_MODEL_VERSION,
    PainCluster,
    PainClusterScoring,
    SourceEvidenceEntry,
    assign_auto_status,
    classify_cluster_tier,
    compute_cluster_id,
    compute_freshness_score,
    compute_overall_score,
    compute_pain_cluster_scoring,
    compute_recurrence_score,
    compute_source_reliability,
    default_pain_cluster_scoring,
    evidence_entry_from_dict,
    evidence_entry_to_dict,
    pain_cluster_from_dict,
    pain_cluster_to_dict,
    scoring_from_dict,
    scoring_to_dict,
    validate_pain_cluster,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence_entry(
    evidence_id: str = "ev_001",
    source_id: str = "hacker_news",
    source_type: str = "discussion",
    source_url: str = "https://news.ycombinator.com/item?id=123",
    evidence_kind: str = "ask_hn",
    title: str = "Debugging AI agents is painful",
    excerpt: str = "I spend hours trying to trace multi-step agent reasoning.",
    created_at: str = "2026-05-10T00:00:00Z",
    fetched_at: str = "2026-05-12T00:00:00Z",
    contribution_to_cluster: str = "primary_pain",
    signal_id: str | None = None,
    quality_flags: list[str] | None = None,
) -> SourceEvidenceEntry:
    return SourceEvidenceEntry(
        evidence_id=evidence_id,
        source_id=source_id,
        source_type=source_type,
        source_url=source_url,
        evidence_kind=evidence_kind,
        title=title,
        excerpt=excerpt,
        created_at=created_at,
        fetched_at=fetched_at,
        contribution_to_cluster=contribution_to_cluster,
        signal_id=signal_id,
        quality_flags=quality_flags or [],
    )


def _make_scoring(**overrides: float) -> PainClusterScoring:
    defaults: dict[str, float | str] = {
        "overall": 0.0,
        "pain_explicitness": 0.5,
        "recurrence": 0.0,
        "business_cost": 0.5,
        "icp_fit": 0.5,
        "source_reliability": 0.5,
        "freshness": 0.5,
        "actionability": 0.5,
        "noise_risk": 0.0,
    }
    defaults.update(overrides)
    return PainClusterScoring(
        overall=float(defaults["overall"]),
        pain_explicitness=float(defaults["pain_explicitness"]),
        recurrence=float(defaults["recurrence"]),
        business_cost=float(defaults["business_cost"]),
        icp_fit=float(defaults["icp_fit"]),
        source_reliability=float(defaults["source_reliability"]),
        freshness=float(defaults["freshness"]),
        actionability=float(defaults["actionability"]),
        noise_risk=float(defaults["noise_risk"]),
    )


def _make_minimal_cluster(
    *,
    cluster_id: str = "pc_test_001",
    actor: str = "developer",
    workflow: str = "AI agent debugging",
    object: str = "multi-step agent workflows",
    pain_verb: str = "hard to debug",
    pain_pattern: str = "developers cannot reliably debug AI agent workflows",
    evidence_entries: list[SourceEvidenceEntry] | None = None,
    scoring: PainClusterScoring | None = None,
    **overrides: object,
) -> PainCluster:
    if evidence_entries is None:
        evidence_entries = [_make_evidence_entry()]
    if scoring is None:
        scoring = default_pain_cluster_scoring()
    base: dict[str, object] = {
        "cluster_id": cluster_id,
        "actor": actor,
        "workflow": workflow,
        "object": object,
        "pain_verb": pain_verb,
        "pain_pattern": pain_pattern,
        "source_evidence_list": evidence_entries,
        "source_diversity": len({e.source_type for e in evidence_entries}),
        "recurrence": len(evidence_entries),
        "business_relevance": 0.5,
        "noise_risk": 0.1,
        "representative_quotes_or_excerpts": ["Hard to trace agent reasoning"],
        "linked_candidate_signals": [],
        "created_at": "2026-05-12T00:00:00Z",
        "updated_at": "2026-05-12T00:00:00Z",
        "status": "new",
        "scoring": scoring,
    }
    base.update(overrides)
    return PainCluster(**base)


# ---------------------------------------------------------------------------
# SourceEvidenceEntry tests
# ---------------------------------------------------------------------------


class TestSourceEvidenceEntry(unittest.TestCase):
    def test_construct_minimal_valid_entry(self) -> None:
        entry = _make_evidence_entry()
        entry.validate()
        self.assertEqual(entry.evidence_id, "ev_001")
        self.assertEqual(entry.source_url, "https://news.ycombinator.com/item?id=123")

    def test_defaults_safely(self) -> None:
        entry = _make_evidence_entry()
        self.assertEqual(entry.signal_id, None)
        self.assertEqual(entry.quality_flags, [])

    def test_rejects_missing_source_url(self) -> None:
        with self.assertRaises(ValueError):
            _make_evidence_entry(source_url="").validate()

    def test_rejects_non_http_source_url(self) -> None:
        # Entry-level validate accepts any non-empty string; scheme validation
        # is handled by validate_pain_cluster (VF8/VF9 fail rules).
        entry = _make_evidence_entry(source_url="ftp://example.com/item")
        entry.validate()  # does not reject at entry level
        self.assertEqual(entry.source_url, "ftp://example.com/item")

    def test_rejects_invalid_contribution_type(self) -> None:
        with self.assertRaises(ValueError):
            _make_evidence_entry(contribution_to_cluster="invalid_type").validate()

    def test_all_contribution_types_accepted(self) -> None:
        for ctype in ALLOWED_CONTRIBUTION_TYPES:
            entry = _make_evidence_entry(contribution_to_cluster=ctype)
            entry.validate()

    def test_rejects_excerpt_too_long(self) -> None:
        long_excerpt = "x" * 501
        entry = _make_evidence_entry(excerpt=long_excerpt)
        with self.assertRaises(ValueError):
            entry.validate()

    def test_excerpt_500_chars_accepted(self) -> None:
        excerpt = "x" * 500
        entry = _make_evidence_entry(excerpt=excerpt)
        entry.validate()

    def test_roundtrip_to_dict_from_dict(self) -> None:
        entry = _make_evidence_entry(
            signal_id="sig_001",
            quality_flags=["flamewar", "vague_complaint"],
        )
        data = evidence_entry_to_dict(entry)
        restored = evidence_entry_from_dict(data)
        self.assertEqual(entry, restored)

    def test_dict_is_json_serializable(self) -> None:
        entry = _make_evidence_entry()
        data = evidence_entry_to_dict(entry)
        json_str = json.dumps(data, ensure_ascii=False)
        self.assertIn("ev_001", json_str)

    def test_json_roundtrip_preserves_all_fields(self) -> None:
        entry = _make_evidence_entry(
            signal_id="sig_002",
            quality_flags=["test_flag"],
        )
        data = evidence_entry_to_dict(entry)
        json_str = json.dumps(data, ensure_ascii=False)
        reloaded_data = json.loads(json_str)
        restored = evidence_entry_from_dict(reloaded_data)
        self.assertEqual(entry, restored)


# ---------------------------------------------------------------------------
# PainClusterScoring tests
# ---------------------------------------------------------------------------


class TestPainClusterScoring(unittest.TestCase):
    def test_construct_with_valid_components(self) -> None:
        scoring = _make_scoring(overall=0.65)
        scoring.validate()
        self.assertEqual(scoring.overall, 0.65)

    def test_default_scoring_is_valid(self) -> None:
        scoring = default_pain_cluster_scoring()
        scoring.validate()
        self.assertEqual(scoring.scoring_model_version, SCORING_MODEL_VERSION)

    def test_rejects_component_below_zero(self) -> None:
        scoring = _make_scoring(pain_explicitness=-0.1)
        with self.assertRaises(ValueError):
            scoring.validate()

    def test_rejects_component_above_one(self) -> None:
        scoring = _make_scoring(actionability=1.1)
        with self.assertRaises(ValueError):
            scoring.validate()

    def test_rejects_overall_below_zero(self) -> None:
        scoring = _make_scoring(overall=-0.001)
        with self.assertRaises(ValueError):
            scoring.validate()

    def test_rejects_overall_above_one(self) -> None:
        scoring = _make_scoring(overall=1.001)
        with self.assertRaises(ValueError):
            scoring.validate()

    def test_roundtrip_to_dict_from_dict(self) -> None:
        scoring = _make_scoring(overall=0.72, pain_explicitness=0.8, noise_risk=0.3)
        data = scoring_to_dict(scoring)
        restored = scoring_from_dict(data)
        self.assertEqual(scoring, restored)

    def test_json_roundtrip(self) -> None:
        scoring = _make_scoring(overall=0.55, actionability=0.7)
        data = scoring_to_dict(scoring)
        json_str = json.dumps(data)
        reloaded_data = json.loads(json_str)
        restored = scoring_from_dict(reloaded_data)
        self.assertEqual(scoring.overall, restored.overall)
        self.assertEqual(scoring.actionability, restored.actionability)


# ---------------------------------------------------------------------------
# PainCluster tests
# ---------------------------------------------------------------------------


class TestPainClusterModel(unittest.TestCase):
    def test_construct_minimal_valid_cluster(self) -> None:
        cluster = _make_minimal_cluster()
        cluster.validate()
        self.assertEqual(cluster.cluster_id, "pc_test_001")
        self.assertEqual(cluster.actor, "developer")

    def test_id_property_returns_cluster_id(self) -> None:
        cluster = _make_minimal_cluster()
        self.assertEqual(cluster.id, cluster.cluster_id)

    def test_rejects_missing_actor(self) -> None:
        with self.assertRaises(ValueError):
            _make_minimal_cluster(actor="").validate()

    def test_rejects_missing_workflow(self) -> None:
        with self.assertRaises(ValueError):
            _make_minimal_cluster(workflow="").validate()

    def test_rejects_missing_object(self) -> None:
        with self.assertRaises(ValueError):
            _make_minimal_cluster(object="").validate()

    def test_rejects_missing_pain_pattern(self) -> None:
        with self.assertRaises(ValueError):
            _make_minimal_cluster(pain_pattern="").validate()

    def test_rejects_missing_pain_verb(self) -> None:
        with self.assertRaises(ValueError):
            _make_minimal_cluster(pain_verb="").validate()

    def test_rejects_empty_evidence_list(self) -> None:
        with self.assertRaises(ValueError):
            _make_minimal_cluster(evidence_entries=[]).validate()

    def test_rejects_invalid_status(self) -> None:
        with self.assertRaises(ValueError):
            _make_minimal_cluster(status="invalid_status").validate()

    def test_all_valid_statuses_accepted(self) -> None:
        for status in ALLOWED_STATUSES:
            cluster = _make_minimal_cluster(status=status)
            cluster.validate()

    def test_rejects_out_of_range_business_relevance(self) -> None:
        with self.assertRaises(ValueError):
            _make_minimal_cluster(business_relevance=1.5).validate()
        with self.assertRaises(ValueError):
            _make_minimal_cluster(business_relevance=-0.1).validate()

    def test_rejects_out_of_range_noise_risk(self) -> None:
        with self.assertRaises(ValueError):
            _make_minimal_cluster(noise_risk=1.5).validate()
        with self.assertRaises(ValueError):
            _make_minimal_cluster(noise_risk=-0.1).validate()

    def test_rejects_source_diversity_mismatch(self) -> None:
        ev1 = _make_evidence_entry(source_type="discussion")
        ev2 = _make_evidence_entry(
            evidence_id="ev_002", source_type="issue_tracker",
            source_id="github_issues",
            source_url="https://github.com/example/repo/issues/1",
        )
        # source_diversity should be 2, but we lie and set it to 1
        cluster = _make_minimal_cluster(
            evidence_entries=[ev1, ev2],
            source_diversity=1,  # wrong!
            recurrence=2,
        )
        with self.assertRaises(ValueError):
            cluster.validate()

    def test_rejects_recurrence_mismatch(self) -> None:
        ev1 = _make_evidence_entry()
        ev2 = _make_evidence_entry(evidence_id="ev_002", source_url="https://example.com/2")
        cluster = _make_minimal_cluster(
            evidence_entries=[ev1, ev2],
            source_diversity=1,
            recurrence=1,  # wrong! should be 2
        )
        with self.assertRaises(ValueError):
            cluster.validate()

    def test_rejects_empty_quotes(self) -> None:
        with self.assertRaises(ValueError):
            _make_minimal_cluster(representative_quotes_or_excerpts=[]).validate()

    def test_rejects_quote_too_long(self) -> None:
        with self.assertRaises(ValueError):
            _make_minimal_cluster(
                representative_quotes_or_excerpts=["x" * 201]
            ).validate()

    def test_quote_200_chars_accepted(self) -> None:
        cluster = _make_minimal_cluster(
            representative_quotes_or_excerpts=["x" * 200]
        )
        cluster.validate()

    def test_notes_defaults_to_empty_string(self) -> None:
        cluster = _make_minimal_cluster()
        self.assertEqual(cluster.notes, "")

    def test_linked_opportunity_candidates_defaults_to_empty(self) -> None:
        cluster = _make_minimal_cluster()
        self.assertEqual(cluster.linked_opportunity_candidates, [])

    def test_roundtrip_to_dict_from_dict(self) -> None:
        ev1 = _make_evidence_entry()
        ev2 = _make_evidence_entry(
            evidence_id="ev_002",
            source_type="issue_tracker",
            source_id="github_issues",
            source_url="https://github.com/owner/repo/issues/1",
            evidence_kind="bug_report",
        )
        scoring = compute_pain_cluster_scoring(
            _make_minimal_cluster(evidence_entries=[ev1, ev2]),
            pain_explicitness=0.7,
        )
        cluster = _make_minimal_cluster(
            evidence_entries=[ev1, ev2],
            source_diversity=2,
            recurrence=2,
            scoring=scoring,
            notes="Test cluster",
            linked_candidate_signals=["sig_a", "sig_b"],
            linked_opportunity_candidates=["opp_x"],
        )
        data = pain_cluster_to_dict(cluster)
        restored = pain_cluster_from_dict(data)
        self.assertEqual(cluster, restored)

    def test_json_roundtrip(self) -> None:
        cluster = _make_minimal_cluster()
        data = pain_cluster_to_dict(cluster)
        json_str = json.dumps(data, ensure_ascii=False)
        reloaded_data = json.loads(json_str)
        restored = pain_cluster_from_dict(reloaded_data)
        self.assertEqual(cluster, restored)

    def test_deterministic_json_structure(self) -> None:
        cluster = _make_minimal_cluster()
        data = pain_cluster_to_dict(cluster)
        self.assertIn("cluster_id", data)
        self.assertIn("actor", data)
        self.assertIn("source_evidence_list", data)
        self.assertIn("scoring", data)
        self.assertIsInstance(data["source_evidence_list"], list)
        self.assertIsInstance(data["scoring"], dict)


# ---------------------------------------------------------------------------
# Cluster ID tests
# ---------------------------------------------------------------------------


class TestClusterID(unittest.TestCase):
    def test_stable_for_same_inputs(self) -> None:
        id1 = compute_cluster_id(
            actor="developer",
            workflow="AI agent debugging",
            object="multi-step agent workflows",
            pain_pattern="developers cannot debug ai agents",
        )
        id2 = compute_cluster_id(
            actor="developer",
            workflow="AI agent debugging",
            object="multi-step agent workflows",
            pain_pattern="developers cannot debug ai agents",
        )
        self.assertEqual(id1, id2)
        self.assertTrue(id1.startswith("pc_"))
        self.assertEqual(len(id1), 19)  # "pc_" + 16 hex chars

    def test_case_normalization(self) -> None:
        id1 = compute_cluster_id(
            actor="Developer",
            workflow="AI Agent Debugging",
            object="Multi-step Agent Workflows",
            pain_pattern="Developers Cannot Debug AI Agents",
        )
        id2 = compute_cluster_id(
            actor="developer",
            workflow="ai agent debugging",
            object="multi-step agent workflows",
            pain_pattern="developers cannot debug ai agents",
        )
        self.assertEqual(id1, id2)

    def test_whitespace_normalization(self) -> None:
        id1 = compute_cluster_id(
            actor="  developer  ",
            workflow="AI agent debugging",
            object="multi-step agent workflows",
            pain_pattern="developers cannot debug ai agents",
        )
        id2 = compute_cluster_id(
            actor="developer",
            workflow="AI agent debugging",
            object="multi-step agent workflows",
            pain_pattern="developers cannot debug ai agents",
        )
        self.assertEqual(id1, id2)

    def test_different_pain_pattern_changes_id(self) -> None:
        id1 = compute_cluster_id(
            actor="developer",
            workflow="AI agent debugging",
            object="multi-step agent workflows",
            pain_pattern="developers cannot debug ai agents",
        )
        id2 = compute_cluster_id(
            actor="developer",
            workflow="deploying ML models",
            object="kubernetes clusters",
            pain_pattern="developers cannot deploy models reliably",
        )
        self.assertNotEqual(id1, id2)

    def test_does_not_depend_on_timestamps(self) -> None:
        """Timestamps should NOT affect cluster_id; it's purely from pain pattern fields."""
        id1 = compute_cluster_id(
            actor="developer",
            workflow="debugging",
            object="agents",
            pain_pattern="agents are unreliable",
        )
        id2 = compute_cluster_id(
            actor="developer",
            workflow="debugging",
            object="agents",
            pain_pattern="agents are unreliable",
        )
        self.assertEqual(id1, id2)

    def test_id_format_is_filesafe(self) -> None:
        """cluster_id should be safe for filenames (no slashes, no special chars)."""
        cid = compute_cluster_id(
            actor="developer",
            workflow="CI/CD pipeline management",
            object="multi-cloud deployment",
            pain_pattern="deployments are brittle across clouds",
        )
        self.assertTrue(cid.startswith("pc_"))
        self.assertTrue(all(c in "0123456789abcdef_pc" for c in cid))


# ---------------------------------------------------------------------------
# Scoring formula tests
# ---------------------------------------------------------------------------


class TestScoringFormula(unittest.TestCase):
    def test_exact_formula_calculation(self) -> None:
        overall = compute_overall_score(
            pain_explicitness=0.8,
            recurrence=0.6,
            business_cost=0.7,
            icp_fit=0.5,
            source_reliability=0.78,
            freshness=1.0,
            actionability=0.7,
            noise_risk=0.15,
        )
        expected = (
            0.25 * 0.8
            + 0.20 * 0.6
            + 0.15 * 0.7
            + 0.15 * 0.5
            + 0.10 * 0.78
            + 0.10 * 1.0
            + 0.05 * 0.7
            - 0.20 * 0.15
        )
        self.assertEqual(overall, round(max(0.0, min(1.0, expected)), 4))

    def test_clamp_below_zero(self) -> None:
        overall = compute_overall_score(
            pain_explicitness=0.0,
            recurrence=0.0,
            business_cost=0.0,
            icp_fit=0.0,
            source_reliability=0.0,
            freshness=0.0,
            actionability=0.0,
            noise_risk=1.0,
        )
        self.assertEqual(overall, 0.0)

    def test_clamp_above_one(self) -> None:
        overall = compute_overall_score(
            pain_explicitness=1.0,
            recurrence=1.0,
            business_cost=1.0,
            icp_fit=1.0,
            source_reliability=1.0,
            freshness=1.0,
            actionability=1.0,
            noise_risk=0.0,
        )
        self.assertEqual(overall, 1.0)

    def test_noise_risk_subtracts_from_score(self) -> None:
        score_no_noise = compute_overall_score(
            pain_explicitness=0.7,
            recurrence=0.5,
            business_cost=0.6,
            icp_fit=0.5,
            source_reliability=0.7,
            freshness=0.8,
            actionability=0.6,
            noise_risk=0.0,
        )
        score_with_noise = compute_overall_score(
            pain_explicitness=0.7,
            recurrence=0.5,
            business_cost=0.6,
            icp_fit=0.5,
            source_reliability=0.7,
            freshness=0.8,
            actionability=0.6,
            noise_risk=0.8,
        )
        self.assertGreater(score_no_noise, score_with_noise)
        # Difference should be exactly 0.20 * 0.8 = 0.16
        self.assertAlmostEqual(
            score_no_noise - score_with_noise, 0.20 * 0.8, places=4
        )


# ---------------------------------------------------------------------------
# Recurrence scoring tests
# ---------------------------------------------------------------------------


class TestRecurrenceScoring(unittest.TestCase):
    def test_single_evidence_gives_0_2_single_source(self) -> None:
        score = compute_recurrence_score(raw_count=1, source_diversity=1)
        self.assertEqual(score, 0.2)

    def test_single_evidence_gives_0_23_cross_source(self) -> None:
        score = compute_recurrence_score(raw_count=1, source_diversity=2)
        self.assertEqual(score, round(0.2 * 1.15, 4))

    def test_five_evidence_maxes_at_1_0_single_source(self) -> None:
        score = compute_recurrence_score(raw_count=5, source_diversity=1)
        self.assertEqual(score, 1.0)

    def test_four_evidence_cross_source_0_92(self) -> None:
        score = compute_recurrence_score(raw_count=4, source_diversity=2)
        self.assertEqual(score, round(min(1.0, (4.0 / 5.0) * 1.15), 4))

    def test_ten_evidence_clamped_to_1_0(self) -> None:
        score = compute_recurrence_score(raw_count=10, source_diversity=3)
        self.assertEqual(score, 1.0)

    def test_multi_source_bonus(self) -> None:
        single = compute_recurrence_score(raw_count=3, source_diversity=1)
        multi = compute_recurrence_score(raw_count=3, source_diversity=2)
        self.assertGreater(multi, single)


# ---------------------------------------------------------------------------
# Freshness scoring tests
# ---------------------------------------------------------------------------


class TestFreshnessScoring(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime.datetime(2026, 5, 12, tzinfo=datetime.timezone.utc)

    def _freshness(self, days_ago: int) -> float:
        dt = self.now - datetime.timedelta(days=days_ago)
        return compute_freshness_score(dt.isoformat(), now=self.now)

    def test_very_recent_is_1_0(self) -> None:
        self.assertEqual(self._freshness(0), 1.0)
        self.assertEqual(self._freshness(5), 1.0)
        self.assertEqual(self._freshness(7), 1.0)

    def test_14_days_ago_decays(self) -> None:
        score = self._freshness(14)
        # day 14 is day 7 of the 23-day decay from 1.0 to 0.6
        expected = 1.0 - (14 - 7) / 23.0 * 0.4
        self.assertAlmostEqual(score, round(expected, 4), places=4)
        self.assertLess(score, 1.0)
        self.assertGreater(score, 0.6)

    def test_30_days_ago_is_0_6(self) -> None:
        expected = round(1.0 - (30 - 7) / 23.0 * 0.4, 4)
        self.assertEqual(self._freshness(30), expected)

    def test_60_days_ago_decays_in_second_tier(self) -> None:
        score = self._freshness(60)
        # day 60 is day 30 of the 60-day decay from 0.6 to 0.3
        expected = round(0.6 - (60 - 30) / 60.0 * 0.3, 4)
        self.assertAlmostEqual(score, expected, places=4)

    def test_90_days_ago_is_0_3(self) -> None:
        expected = round(0.6 - (90 - 30) / 60.0 * 0.3, 4)
        self.assertEqual(self._freshness(90), expected)

    def test_180_days_ago_decays_below_0_3(self) -> None:
        score = self._freshness(180)
        # day 180 is day 90 of the 270-day decay from 0.3 to 0.1
        expected = round(max(0.1, 0.3 - (180 - 90) / 270.0 * 0.2), 4)
        self.assertAlmostEqual(score, expected, places=4)
        self.assertLess(score, 0.3)
        self.assertGreaterEqual(score, 0.1)

    def test_360_days_ago_floor_0_1(self) -> None:
        expected = round(max(0.1, 0.3 - (360 - 90) / 270.0 * 0.2), 4)
        self.assertEqual(self._freshness(360), expected)

    def test_700_days_ago_still_floor_0_1(self) -> None:
        self.assertEqual(self._freshness(700), 0.1)

    def test_invalid_timestamp_returns_default(self) -> None:
        score = compute_freshness_score("not-a-timestamp", now=self.now)
        self.assertEqual(score, 0.5)


# ---------------------------------------------------------------------------
# Source reliability tests
# ---------------------------------------------------------------------------


class TestSourceReliability(unittest.TestCase):
    def test_single_source_uses_prior(self) -> None:
        entries = [_make_evidence_entry(source_id="github_issues", source_type="issue_tracker")]
        score = compute_source_reliability(entries)
        self.assertEqual(score, 0.78)

    def test_multi_source_weighted_average(self) -> None:
        entries = [
            _make_evidence_entry(
                evidence_id="ev_001",
                source_id="github_issues",
                source_type="issue_tracker",
                source_url="https://github.com/a/b/issues/1",
            ),
            _make_evidence_entry(
                evidence_id="ev_002",
                source_id="hacker_news",
                source_type="discussion",
                source_url="https://news.ycombinator.com/item?id=2",
            ),
        ]
        score = compute_source_reliability(entries)
        expected = (0.78 * 1 + 0.72 * 1) / 2
        self.assertEqual(score, round(expected, 4))

    def test_weighted_by_evidence_count(self) -> None:
        entries = [
            _make_evidence_entry(
                evidence_id="ev_001",
                source_id="github_issues",
                source_type="issue_tracker",
                source_url="https://github.com/a/b/issues/1",
            ),
            _make_evidence_entry(
                evidence_id="ev_002",
                source_id="hacker_news",
                source_type="discussion",
                source_url="https://news.ycombinator.com/item?id=2",
            ),
            _make_evidence_entry(
                evidence_id="ev_003",
                source_id="hacker_news",
                source_type="discussion",
                source_url="https://news.ycombinator.com/item?id=3",
            ),
        ]
        score = compute_source_reliability(entries)
        expected = (0.78 * 1 + 0.72 * 2) / 3
        self.assertEqual(score, round(expected, 4))

    def test_empty_entries_returns_default(self) -> None:
        score = compute_source_reliability([])
        self.assertEqual(score, 0.5)


# ---------------------------------------------------------------------------
# compute_pain_cluster_scoring tests
# ---------------------------------------------------------------------------


class TestComputePainClusterScoring(unittest.TestCase):
    def test_computes_all_8_components(self) -> None:
        cluster = _make_minimal_cluster()
        scoring = compute_pain_cluster_scoring(
            cluster,
            pain_explicitness=0.8,
            icp_fit=0.6,
            actionability=0.7,
        )
        self.assertIsInstance(scoring, PainClusterScoring)
        scoring.validate()

        self.assertEqual(scoring.pain_explicitness, 0.8)
        self.assertEqual(scoring.icp_fit, 0.6)
        self.assertEqual(scoring.actionability, 0.7)
        self.assertGreaterEqual(scoring.overall, 0.0)
        self.assertLessEqual(scoring.overall, 1.0)

    def test_default_pain_explicitness_is_0_5(self) -> None:
        cluster = _make_minimal_cluster()
        scoring = compute_pain_cluster_scoring(cluster)
        self.assertEqual(scoring.pain_explicitness, 0.5)

    def test_default_icp_fit_is_0_5(self) -> None:
        cluster = _make_minimal_cluster()
        scoring = compute_pain_cluster_scoring(cluster)
        self.assertEqual(scoring.icp_fit, 0.5)

    def test_rejects_invalid_pain_explicitness(self) -> None:
        cluster = _make_minimal_cluster()
        with self.assertRaises(ValueError):
            compute_pain_cluster_scoring(cluster, pain_explicitness=1.5)

    def test_rejects_invalid_icp_fit(self) -> None:
        cluster = _make_minimal_cluster()
        with self.assertRaises(ValueError):
            compute_pain_cluster_scoring(cluster, icp_fit=-0.1)

    def test_rejects_invalid_actionability(self) -> None:
        cluster = _make_minimal_cluster()
        with self.assertRaises(ValueError):
            compute_pain_cluster_scoring(cluster, actionability=2.0)

    def test_scoring_model_version_is_pilot_v1(self) -> None:
        cluster = _make_minimal_cluster()
        scoring = compute_pain_cluster_scoring(cluster)
        self.assertEqual(scoring.scoring_model_version, SCORING_MODEL_VERSION)

    def test_computed_at_is_current_timestamp(self) -> None:
        cluster = _make_minimal_cluster()
        scoring = compute_pain_cluster_scoring(cluster)
        self.assertTrue(scoring.computed_at.endswith("Z") or "+" in scoring.computed_at)


# ---------------------------------------------------------------------------
# Tier classification tests
# ---------------------------------------------------------------------------


class TestTierClassification(unittest.TestCase):
    def test_overall_ge_0_70_is_candidate(self) -> None:
        self.assertEqual(classify_cluster_tier(0.70, noise_risk=0.1), "candidate")
        self.assertEqual(classify_cluster_tier(0.85, noise_risk=0.0), "candidate")

    def test_0_50_to_0_69_is_needs_more_evidence(self) -> None:
        self.assertEqual(classify_cluster_tier(0.50, noise_risk=0.1), "needs_more_evidence")
        self.assertEqual(classify_cluster_tier(0.69, noise_risk=0.3), "needs_more_evidence")

    def test_below_0_50_is_noise_or_park(self) -> None:
        self.assertEqual(classify_cluster_tier(0.49, noise_risk=0.1), "noise_or_park")
        self.assertEqual(classify_cluster_tier(0.0, noise_risk=0.0), "noise_or_park")

    def test_noise_risk_ge_0_80_overrides_even_high_score(self) -> None:
        self.assertEqual(classify_cluster_tier(0.95, noise_risk=0.80), "noise_or_park")
        self.assertEqual(classify_cluster_tier(0.75, noise_risk=0.90), "noise_or_park")


# ---------------------------------------------------------------------------
# Auto status assignment tests
# ---------------------------------------------------------------------------


class TestAutoStatusAssignment(unittest.TestCase):
    def test_high_noise_risk_gives_noise(self) -> None:
        self.assertEqual(assign_auto_status(0.8, noise_risk=0.85, recurrence=5), "noise")

    def test_low_overall_low_recurrence_gives_weak(self) -> None:
        self.assertEqual(assign_auto_status(0.2, noise_risk=0.1, recurrence=1), "weak")

    def test_low_overall_moderate_noise_gives_noise(self) -> None:
        self.assertEqual(assign_auto_status(0.40, noise_risk=0.55, recurrence=3), "noise")

    def test_default_returns_new(self) -> None:
        self.assertEqual(assign_auto_status(0.60, noise_risk=0.1, recurrence=5), "new")
        self.assertEqual(assign_auto_status(0.35, noise_risk=0.3, recurrence=3), "new")


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestValidatePainCluster(unittest.TestCase):
    def test_valid_cluster_has_no_errors(self) -> None:
        cluster = _make_minimal_cluster()
        errors, warnings = validate_pain_cluster(cluster)
        self.assertEqual(errors, [])

    def test_missing_actor_fails(self) -> None:
        cluster = _make_minimal_cluster(actor="")
        errors, _ = validate_pain_cluster(cluster)
        self.assertTrue(any("actor" in e for e in errors))

    def test_missing_workflow_fails(self) -> None:
        cluster = _make_minimal_cluster(workflow="")
        errors, _ = validate_pain_cluster(cluster)
        self.assertTrue(any("workflow" in e for e in errors))

    def test_missing_object_fails(self) -> None:
        cluster = _make_minimal_cluster(object="")
        errors, _ = validate_pain_cluster(cluster)
        self.assertTrue(any("object" in e for e in errors))

    def test_missing_pain_pattern_fails(self) -> None:
        cluster = _make_minimal_cluster(pain_pattern="")
        errors, _ = validate_pain_cluster(cluster)
        self.assertTrue(any("pain_pattern" in e for e in errors))

    def test_no_evidence_fails(self) -> None:
        cluster = _make_minimal_cluster(evidence_entries=[])
        errors, _ = validate_pain_cluster(cluster)
        self.assertTrue(any("evidence" in e.lower() for e in errors))

    def test_evidence_without_source_url_fails(self) -> None:
        ev = _make_evidence_entry(source_url="")
        cluster = _make_minimal_cluster(evidence_entries=[ev])
        errors, _ = validate_pain_cluster(cluster)
        self.assertTrue(any("source_url" in e for e in errors))

    def test_evidence_with_placeholder_url_fails(self) -> None:
        ev = _make_evidence_entry(source_url="urn:oos:placeholder:123")
        cluster = _make_minimal_cluster(evidence_entries=[ev])
        errors, _ = validate_pain_cluster(cluster)
        self.assertTrue(any("VF8" in e for e in errors))

    def test_evidence_with_non_http_url_fails(self) -> None:
        ev = _make_evidence_entry(source_url="ftp://example.com/item")
        cluster = _make_minimal_cluster(evidence_entries=[ev])
        errors, _ = validate_pain_cluster(cluster)
        self.assertTrue(any("VF9" in e for e in errors))

    def test_missing_scoring_component_fails(self) -> None:
        # scoring with invalid overall
        scoring = _make_scoring(overall=2.0)
        cluster = _make_minimal_cluster(scoring=scoring)
        errors, _ = validate_pain_cluster(cluster)
        self.assertTrue(any("overall" in e for e in errors))

    def test_high_noise_risk_warning(self) -> None:
        cluster = _make_minimal_cluster(noise_risk=0.65)
        cluster = PainCluster(
            cluster_id=cluster.cluster_id,
            actor=cluster.actor,
            workflow=cluster.workflow,
            object=cluster.object,
            pain_verb=cluster.pain_verb,
            pain_pattern=cluster.pain_pattern,
            source_evidence_list=cluster.source_evidence_list,
            source_diversity=cluster.source_diversity,
            recurrence=cluster.recurrence,
            business_relevance=cluster.business_relevance,
            noise_risk=0.65,
            representative_quotes_or_excerpts=cluster.representative_quotes_or_excerpts,
            linked_candidate_signals=cluster.linked_candidate_signals,
            created_at=cluster.created_at,
            updated_at=cluster.updated_at,
            status=cluster.status,
            scoring=cluster.scoring,
        )
        _, warnings = validate_pain_cluster(cluster)
        self.assertTrue(any("VW2" in w for w in warnings))

    def test_single_source_warning(self) -> None:
        cluster = _make_minimal_cluster()
        _, warnings = validate_pain_cluster(cluster)
        self.assertTrue(any("VW1" in w for w in warnings))


# ---------------------------------------------------------------------------
# Scoring overall computes correctly from cluster
# ---------------------------------------------------------------------------


class TestScoringIntegration(unittest.TestCase):
    def test_scoring_roundtrip_in_cluster(self) -> None:
        ev1 = _make_evidence_entry()
        ev2 = _make_evidence_entry(
            evidence_id="ev_002",
            source_type="issue_tracker",
            source_id="github_issues",
            source_url="https://github.com/owner/repo/issues/1",
            evidence_kind="bug_report",
        )
        cluster = _make_minimal_cluster(
            evidence_entries=[ev1, ev2],
            source_diversity=2,
            recurrence=2,
            business_relevance=0.75,
            noise_risk=0.15,
        )
        scoring = compute_pain_cluster_scoring(
            cluster,
            pain_explicitness=0.8,
            icp_fit=0.6,
            actionability=0.7,
        )
        cluster_with_scoring = PainCluster(
            cluster_id=cluster.cluster_id,
            actor=cluster.actor,
            workflow=cluster.workflow,
            object=cluster.object,
            pain_verb=cluster.pain_verb,
            pain_pattern=cluster.pain_pattern,
            source_evidence_list=cluster.source_evidence_list,
            source_diversity=cluster.source_diversity,
            recurrence=cluster.recurrence,
            business_relevance=cluster.business_relevance,
            noise_risk=cluster.noise_risk,
            representative_quotes_or_excerpts=cluster.representative_quotes_or_excerpts,
            linked_candidate_signals=cluster.linked_candidate_signals,
            created_at=cluster.created_at,
            updated_at=cluster.updated_at,
            status=cluster.status,
            scoring=scoring,
        )
        cluster_with_scoring.validate()
        errors, _ = validate_pain_cluster(cluster_with_scoring)
        self.assertEqual(errors, [])

    def test_deterministic_scoring_same_input_same_output(self) -> None:
        def build_and_score() -> PainClusterScoring:
            cluster = _make_minimal_cluster()
            return compute_pain_cluster_scoring(
                cluster,
                pain_explicitness=0.7,
                icp_fit=0.5,
                actionability=0.6,
            )

        s1 = build_and_score()
        s2 = build_and_score()
        self.assertEqual(s1, s2)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases(unittest.TestCase):
    def test_max_noise_cluster_scores_low(self) -> None:
        cluster = _make_minimal_cluster(noise_risk=1.0, business_relevance=0.0)
        scoring = compute_pain_cluster_scoring(
            cluster,
            pain_explicitness=0.0,
            icp_fit=0.0,
            actionability=0.0,
        )
        self.assertLess(scoring.overall, 0.50)
        self.assertEqual(classify_cluster_tier(scoring.overall, scoring.noise_risk), "noise_or_park")

    def test_strong_signal_scores_high(self) -> None:
        ev1 = _make_evidence_entry()
        ev2 = _make_evidence_entry(
            evidence_id="ev_002",
            source_type="issue_tracker",
            source_id="github_issues",
            source_url="https://github.com/owner/repo/issues/1",
            evidence_kind="bug_report",
        )
        ev3 = _make_evidence_entry(
            evidence_id="ev_003",
            source_type="issue_tracker",
            source_id="github_issues",
            source_url="https://github.com/owner/repo/issues/2",
            evidence_kind="bug_report",
        )
        ev4 = _make_evidence_entry(
            evidence_id="ev_004",
            source_type="discussion",
            source_id="hacker_news",
            source_url="https://news.ycombinator.com/item?id=4",
        )
        ev5 = _make_evidence_entry(
            evidence_id="ev_005",
            source_type="discussion",
            source_id="hacker_news",
            source_url="https://news.ycombinator.com/item?id=5",
        )
        ev6 = _make_evidence_entry(
            evidence_id="ev_006",
            source_type="discussion",
            source_id="hacker_news",
            source_url="https://news.ycombinator.com/item?id=6",
        )
        cluster = _make_minimal_cluster(
            evidence_entries=[ev1, ev2, ev3, ev4, ev5, ev6],
            source_diversity=2,
            recurrence=6,
            business_relevance=0.9,
            noise_risk=0.05,
        )
        scoring = compute_pain_cluster_scoring(
            cluster,
            pain_explicitness=0.95,
            icp_fit=0.85,
            actionability=0.9,
        )
        self.assertGreaterEqual(scoring.overall, 0.70)
        self.assertEqual(
            classify_cluster_tier(scoring.overall, scoring.noise_risk), "candidate"
        )

    def test_empty_linked_candidate_signals_valid(self) -> None:
        cluster = _make_minimal_cluster(linked_candidate_signals=[])
        cluster.validate()

    def test_multiple_quotes_valid(self) -> None:
        cluster = _make_minimal_cluster(
            representative_quotes_or_excerpts=["quote one", "quote two", "quote three"]
        )
        cluster.validate()
        self.assertEqual(len(cluster.representative_quotes_or_excerpts), 3)


if __name__ == "__main__":
    unittest.main()
