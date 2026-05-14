from __future__ import annotations

"""Tests for deterministic noise classification hardening (v2.14 item 1).

Covers:
1. Clean pain evidence remains accepted.
2. low_text_context + empty/URL-only body becomes noise.
3. suspected_self_promo + product_launch becomes noise or weak, not accepted-clean.
4. requires_manual_review alone becomes weak, not accepted-clean.
5. stale_issue becomes weak unless paired with strong clear pain evidence.
6. maintainer_housekeeping becomes noise.
7. debugging_pain / integration_pain / workflow_pain do not by themselves make evidence noise.
8. Source Quality Report counts accepted/weak/noise correctly from mixed evidence.
9. Operational pilot output source quality report reflects noise/weak counts.
10. Serialization roundtrips preserve classification fields.
11. No traceability behavior is weakened.
12. No source scope behavior is weakened.
"""

import json
import unittest

from oos.noise_classifier import (
    ACCEPTED,
    NOISE,
    WEAK,
    classify_noise,
    classify_noise_for_evidence,
    classify_noise_for_signal,
)
from oos.source_quality_report import (
    build_source_quality_report,
)
from oos.operational_discovery_pilot import (
    OperationalDiscoveryPilotInput,
    _derive_minimal_candidate_signals,
    run_operational_discovery_pilot,
)


# =========================================================================
# Fixture helpers
# =========================================================================

def _make_evidence(**kwargs) -> dict:
    defaults = {
        "evidence_id": "ev_001",
        "source_id": "hacker_news",
        "source_type": "discussion",
        "source_url": "https://news.ycombinator.com/item?id=1",
        "title": "Debugging AI agents is impossible",
        "body": "Multi-step agent traces are non-reproducible and cost hours of developer time.",
        "evidence_kind": "pain_signal_candidate",
        "quality_flags": [],
        "excerpt": "",
    }
    defaults.update(kwargs)
    return defaults


def _make_signal(**kwargs) -> dict:
    defaults = {
        "signal_id": "sig_001",
        "evidence_id": "ev_001",
        "source_id": "hacker_news",
        "source_type": "discussion",
        "source_url": "https://news.ycombinator.com/item?id=1",
        "classification": "pain_signal_candidate",
        "signal_type": "pain_signal",
        "quality_flags": [],
        "pain_summary": "Debugging AI agents is impossible",
        "evidence_kind": "pain_signal_candidate",
        "title": "Debugging AI agents is impossible",
        "body": "Multi-step agent traces are non-reproducible and cost hours.",
        "excerpt": "",
    }
    defaults.update(kwargs)
    return defaults


def _make_pilot_evidence(
    evidence_id="ev_p",
    source_id="hacker_news",
    source_type="discussion",
    source_url="https://news.ycombinator.com/item?id=1",
    title="Clean pain",
    body="We struggle with a critical problem.",
    evidence_kind="pain_signal_candidate",
    quality_flags=None,
):
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "source_type": source_type,
        "source_url": source_url,
        "title": title,
        "body": body,
        "evidence_kind": evidence_kind,
        "created_at": "2026-01-01T00:00:00Z",
        "collected_at": "2026-01-01T00:00:00Z",
        "fetched_at": "2026-01-01T00:00:00Z",
        "topic_id": "agent_debugging",
        "query_kind": "pilot_fixture",
        "quality_flags": quality_flags or [],
        "excerpt": "",
        "raw_metadata": {"target_user": "developer"},
    }


# =========================================================================
# 1. Clean pain evidence remains accepted
# =========================================================================

class TestCleanPainAccepted(unittest.TestCase):
    def test_clean_pain_signal_accepted(self):
        result = classify_noise(
            quality_flags=[],
            evidence_kind="pain_signal_candidate",
            title="Debugging AI agents is impossible",
            body="Multi-step agent traces are non-reproducible. We spend hours every week.",
        )
        self.assertEqual(result, ACCEPTED)

    def test_pain_signal_with_workaround_flag_accepted(self):
        result = classify_noise(
            quality_flags=["workaround_signal"],
            evidence_kind="pain_signal_candidate",
            title="Manual spreadsheet reconciliation broken",
            body="We waste 5 hours per week manually matching Stripe payouts to bank records.",
        )
        self.assertEqual(result, ACCEPTED)

    def test_integration_pain_does_not_create_noise(self):
        result = classify_noise(
            quality_flags=["integration_pain"],
            evidence_kind="integration_pain",
            title="Cannot integrate Slack and Jira",
            body="Every time a ticket moves, we need to manually update Slack. This costs hours.",
        )
        self.assertEqual(result, ACCEPTED)

    def test_debugging_pain_does_not_create_noise(self):
        result = classify_noise(
            quality_flags=["debugging_pain"],
            evidence_kind="pain_signal_candidate",
            title="LLM agent trace debugging is broken",
            body="Cannot reproduce multi-step agent failures. Critical for our dev workflow.",
        )
        self.assertEqual(result, ACCEPTED)

    def test_workflow_pain_does_not_create_noise(self):
        result = classify_noise(
            quality_flags=["workflow_pain"],
            evidence_kind="pain_signal_candidate",
            title="CI/CD pipeline debugging wastes hours",
            body="Flaky tests cause entire team to wait. This problem is costing us real money.",
        )
        self.assertEqual(result, ACCEPTED)

    def test_business_cost_signal_does_not_create_noise(self):
        result = classify_noise(
            quality_flags=["business_cost_signal"],
            evidence_kind="pain_signal_candidate",
            title="Manual processes cost our startup $2000/month",
            body="We need to automate invoice reconciliation. Currently a manual process.",
        )
        self.assertEqual(result, ACCEPTED)


# =========================================================================
# 2. low_text_context + empty/URL-only body becomes noise
# =========================================================================

class TestLowTextContextNoise(unittest.TestCase):
    def test_low_text_context_empty_body_noise(self):
        result = classify_noise(
            quality_flags=["low_text_context"],
            evidence_kind="bug_report",
            title="",
            body="",
            excerpt="",
        )
        self.assertEqual(result, NOISE)

    def test_low_text_context_url_only_body_noise(self):
        result = classify_noise(
            quality_flags=["low_text_context"],
            evidence_kind="bug_report",
            title="Check this out",
            body="https://example.com",
            excerpt="",
        )
        self.assertEqual(result, NOISE)

    def test_low_text_context_no_pain_noise(self):
        result = classify_noise(
            quality_flags=["low_text_context"],
            evidence_kind="bug_report",
            title="it's broken",
            body="fix it please",
            excerpt="",
        )
        self.assertEqual(result, NOISE)

    def test_low_text_context_with_clear_pain_stays_accepted_if_overridden(self):
        result = classify_noise(
            quality_flags=["low_text_context"],
            evidence_kind="bug_report",
            title="Agent debugging broken - costs hours",
            body="The LLM agent debugging is broken. We cannot reproduce failures. Workaround is painfully manual. This problem frustrates our whole team.",
        )
        self.assertEqual(result, ACCEPTED)


# =========================================================================
# 3. suspected_self_promo + product_launch becomes noise or weak, not accepted
# =========================================================================

class TestSelfPromoWithProductLaunch(unittest.TestCase):
    def test_self_promo_product_launch_no_pain_noise(self):
        result = classify_noise(
            quality_flags=["suspected_self_promo", "launch_hype"],
            evidence_kind="product_launch",
            title="Check out our new AI debugging tool!",
            body="We just launched FooDebugger 2.0. It makes debugging fun and easy. Try it now!",
        )
        self.assertNotEqual(result, ACCEPTED)
        self.assertIn(result, (WEAK, NOISE))

    def test_self_promo_product_launch_no_pain_noise_single_flag(self):
        # suspected_self_promo + product_launch evidence_kind + no pain → noise
        # Use text that avoids pain-marker substrings (e.g., "debugging" contains "bug")
        result = classify_noise(
            quality_flags=["suspected_self_promo"],
            evidence_kind="product_launch",
            title="Introducing our new project management tool",
            body="Available for download now. Visit our homepage to sign up.",
        )
        # Rule 3 catches this: self_promo + product_launch + no pain → noise
        self.assertEqual(result, NOISE)

    def test_self_promo_product_launch_with_pain_weak(self):
        result = classify_noise(
            quality_flags=["suspected_self_promo"],
            evidence_kind="product_launch",
            title="Our debugging tool solves real pain",
            body="We struggled for months debugging multi-step agents. The workaround was manual and broken. Our tool solves this frustrating problem that costs developers hours every week.",
        )
        # Has clear pain, so NOT auto-noise. But suspected_self_promo is medium → weak
        self.assertEqual(result, WEAK)

    def test_self_promo_alone_without_product_launch_weak(self):
        result = classify_noise(
            quality_flags=["suspected_self_promo"],
            evidence_kind="pain_signal_candidate",
            title="Debugging tool comparison",
            body="We tried several debugging tools and found the current state frustrating. Manual workarounds cost hours.",
        )
        self.assertEqual(result, WEAK)


# =========================================================================
# 4. requires_manual_review alone becomes weak, not accepted-clean
# =========================================================================

class TestRequiresManualReviewWeak(unittest.TestCase):
    def test_requires_manual_review_alone_weak(self):
        result = classify_noise(
            quality_flags=["requires_manual_review"],
            evidence_kind="pain_signal_candidate",
            title="Possible pain signal",
            body="This might be about debugging issues but context is unclear.",
        )
        self.assertEqual(result, WEAK)

    def test_requires_manual_review_with_pain_weak(self):
        result = classify_noise(
            quality_flags=["requires_manual_review"],
            evidence_kind="pain_signal_candidate",
            title="Debugging agents is hard",
            body="We struggle with agent debugging every day. Our workaround is broken. This is a critical problem.",
        )
        self.assertEqual(result, WEAK)

    def test_requires_manual_review_not_accepted(self):
        result = classify_noise(
            quality_flags=["requires_manual_review"],
            evidence_kind="pain_signal_candidate",
            title="Standard clean issue",
            body="This is a well-described problem with clear actor, workflow, and object. It affects many users.",
        )
        self.assertNotEqual(result, ACCEPTED)


# =========================================================================
# 5. stale_issue becomes weak unless paired with strong clear pain evidence
# =========================================================================

class TestStaleIssueClassification(unittest.TestCase):
    def test_stale_issue_alone_weak(self):
        result = classify_noise(
            quality_flags=["stale_issue"],
            evidence_kind="bug_report",
            title="Old bug from 2019",
            body="This issue was reported years ago and hasn't been active.",
        )
        self.assertEqual(result, WEAK)

    def test_stale_issue_with_strong_pain_accepted(self):
        result = classify_noise(
            quality_flags=["stale_issue"],
            evidence_kind="bug_report",
            title="Critical: Agent debugging still broken after 2 years",
            body=(
                "This critical bug has been open for two years and affects every developer on our team. "
                "We cannot reproduce multi-step agent failures, the workaround is painfully manual, "
                "and we waste hours every single week. Our costs are skyrocketing. This is frustrating "
                "and broken. The problem has gotten worse with more complex agent workflows."
            ),
        )
        self.assertEqual(result, ACCEPTED)

    def test_stale_issue_with_marginal_pain_weak(self):
        result = classify_noise(
            quality_flags=["stale_issue"],
            evidence_kind="bug_report",
            title="Old issue",
            body="This problem was reported a while ago and no one has followed up. It affects some users sometimes.",
        )
        self.assertEqual(result, WEAK)


# =========================================================================
# 6. maintainer_housekeeping becomes noise
# =========================================================================

class TestMaintainerHousekeepingNoise(unittest.TestCase):
    def test_maintainer_housekeeping_noise(self):
        result = classify_noise(
            quality_flags=["maintainer_housekeeping"],
            evidence_kind="bug_report",
            title="Bump version to 2.0.1",
            body="Release checklist: update changelog, tag release, publish to npm.",
        )
        self.assertEqual(result, NOISE)

    def test_maintainer_housekeeping_with_pain_still_noise(self):
        result = classify_noise(
            quality_flags=["maintainer_housekeeping", "debugging_pain"],
            evidence_kind="bug_report",
            title="Update dependencies and fix broken debug tool",
            body="Several dependencies are outdated. Need to update npm packages.",
        )
        self.assertEqual(result, NOISE)


# =========================================================================
# 7. Positive flags do not by themselves make evidence noise
# =========================================================================

class TestPositiveFlagsNotNoise(unittest.TestCase):
    def test_debugging_pain_alone_accepted(self):
        result = classify_noise(
            quality_flags=["debugging_pain"],
            evidence_kind="pain_signal_candidate",
            title="Debugging is hard",
            body="We cannot debug our agent pipelines properly.",
        )
        self.assertEqual(result, ACCEPTED)

    def test_integration_pain_alone_accepted(self):
        result = classify_noise(
            quality_flags=["integration_pain"],
            evidence_kind="integration_pain",
            title="Cannot integrate two systems",
            body="Our CI/CD integration with monitoring tools is broken and frustrating.",
        )
        self.assertEqual(result, ACCEPTED)

    def test_workflow_pain_alone_accepted(self):
        result = classify_noise(
            quality_flags=["workflow_pain"],
            evidence_kind="pain_signal_candidate",
            title="Workflow is broken",
            body="Our deployment workflow wastes hours every week.",
        )
        self.assertEqual(result, ACCEPTED)

    def test_reliability_pain_alone_accepted(self):
        result = classify_noise(
            quality_flags=["reliability_pain"],
            evidence_kind="pain_signal_candidate",
            title="System is unreliable",
            body="Our monitoring system crashes frequently, causing data loss.",
        )
        self.assertEqual(result, ACCEPTED)

    def test_positive_flags_dont_override_negative(self):
        result = classify_noise(
            quality_flags=["debugging_pain", "bot_generated"],
            evidence_kind="pain_signal_candidate",
            title="Bot message",
            body="Automated update notification.",
        )
        self.assertEqual(result, NOISE)


# =========================================================================
# 8. Source Quality Report counts correctly from mixed evidence
# =========================================================================

class TestSourceQualityReportWithNoiseClassification(unittest.TestCase):
    def test_mixed_evidence_produces_correct_counts(self):
        evidence = [
            # Clean accepted
            _make_evidence(
                evidence_id="hn_clean",
                title="Debugging LLM agents is broken",
                body="Cannot reproduce multi-step agent traces. Wastes hours. Manual workaround is painful.",
                quality_flags=[],
            ),
            # Weak
            _make_evidence(
                evidence_id="hn_weak",
                title="Something might be wrong",
                body="Not sure if this is a pain point but seems relevant.",
                quality_flags=["requires_manual_review"],
            ),
            # Noise (maintainer_housekeeping)
            _make_evidence(
                evidence_id="hn_noise",
                title="Dependabot: bump express to 4.18.0",
                body="Automated dependency update. Changelog: minor fixes.",
                quality_flags=["maintainer_housekeeping"],
                evidence_kind="bot_generated",
            ),
            # Clean accepted #2
            _make_evidence(
                evidence_id="hn_clean2",
                title="Cannot integrate CI/CD tools properly",
                body="Our monitoring and deployment pipeline is broken. Costs hours per week.",
                quality_flags=["integration_pain", "workflow_pain"],
            ),
            # Noise (low_text_context)
            _make_evidence(
                evidence_id="hn_lowtext",
                title="it",
                body="",
                quality_flags=["low_text_context"],
            ),
            # Weak (stale_issue no strong pain)
            _make_evidence(
                evidence_id="hn_stale",
                title="Old issue from 2020",
                body="This was reported a long time ago.",
                quality_flags=["stale_issue"],
            ),
        ]
        # Build candidate-signal-like dicts with same quality_flags
        signals = []
        for ev in evidence:
            signals.append({
                "signal_id": f"sig_{ev['evidence_id']}",
                "evidence_id": ev["evidence_id"],
                "source_id": ev["source_id"],
                "source_type": ev["source_type"],
                "source_url": ev.get("source_url", ""),
                "classification": ev.get("classification", "pain_signal_candidate"),
                "signal_type": ev.get("signal_type", "pain_signal"),
                "quality_flags": ev.get("quality_flags", []),
                "evidence_kind": ev.get("evidence_kind", "pain_signal_candidate"),
                "title": ev.get("title", ""),
                "body": ev.get("body", ""),
                "excerpt": ev.get("excerpt", ""),
            })

        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_mixed",
            created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.source_id, "hacker_news")
        # hn_clean: no flags → accepted
        # hn_weak: requires_manual_review → weak
        # hn_noise: maintainer_housekeeping → noise
        # hn_clean2: positive flags only → accepted
        # hn_lowtext: low_text_context, no pain → noise
        # hn_stale: stale_issue, no strong pain → weak
        self.assertEqual(m.accepted_signal_count, 2)
        self.assertEqual(m.weak_signal_count, 2)
        self.assertEqual(m.noise_signal_count, 2)

    def test_all_clean_evidence_produces_full_accepted(self):
        evidence = [
            _make_evidence(evidence_id=f"hn_{i}", quality_flags=[])
            for i in range(5)
        ]
        signals = [
            {
                "signal_id": f"sig_hn_{i}",
                "evidence_id": f"hn_{i}",
                "source_id": "hacker_news",
                "source_type": "discussion",
                "source_url": "https://news.ycombinator.com/item?id=1",
                "classification": "pain_signal_candidate",
                "signal_type": "pain_signal",
                "quality_flags": [],
                "evidence_kind": "pain_signal_candidate",
                "title": f"Title {i}",
                "body": "Pain body text.",
                "excerpt": "",
            }
            for i in range(5)
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_clean",
            created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.accepted_signal_count, 5)
        self.assertEqual(m.weak_signal_count, 0)
        self.assertEqual(m.noise_signal_count, 0)
        self.assertGreater(m.accepted_rate, 0.99)

    def test_all_noise_evidence_produces_zero_accepted(self):
        evidence = [
            _make_evidence(
                evidence_id=f"hn_n{i}",
                quality_flags=["bot_generated"],
                title="Automated message",
                body="This is an automated notification.",
            )
            for i in range(3)
        ]
        signals = [
            {
                "signal_id": f"sig_hn_n{i}",
                "evidence_id": f"hn_n{i}",
                "source_id": "hacker_news",
                "source_type": "discussion",
                "source_url": "https://news.ycombinator.com/item?id=1",
                "classification": "pain_signal_candidate",
                "signal_type": "pain_signal",
                "quality_flags": ["bot_generated"],
                "evidence_kind": "pain_signal_candidate",
                "title": "Automated message",
                "body": "This is an automated notification.",
                "excerpt": "",
            }
            for i in range(3)
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_noise",
            created_at="2026-01-01T00:00:00Z",
        )
        m = report.source_metrics[0]
        self.assertEqual(m.accepted_signal_count, 0)
        self.assertEqual(m.noise_signal_count, 3)


# =========================================================================
# 9. Operational pilot output source quality report reflects noise/weak counts
# =========================================================================

class TestOperationalPilotNoisePropagation(unittest.TestCase):
    def test_pilot_with_mixed_quality_flags(self):
        evidence = [
            _make_pilot_evidence(
                evidence_id="hn_p1",
                title="Debugging is broken",
                body="Cannot debug agent traces. Hours wasted. Manual workaround required.",
                quality_flags=[],
            ),
            _make_pilot_evidence(
                evidence_id="hn_p2",
                title="Check out my tool",
                body="Launching FooBar. Sign up now.",
                evidence_kind="product_launch",
                quality_flags=["suspected_self_promo", "launch_hype"],
            ),
            _make_pilot_evidence(
                evidence_id="hn_p3",
                title="Automated dependency update",
                body="Bump express to next version.",
                evidence_kind="bug_report",
                quality_flags=["maintainer_housekeeping"],
            ),
        ]

        result = run_operational_discovery_pilot(
            OperationalDiscoveryPilotInput(
                raw_evidence=evidence,
                discovery_run_id="test_noise_pilot",
                created_at="2026-01-01T00:00:00Z",
            )
        )

        sqr = result.source_quality_report
        self.assertIsNotNone(sqr)
        m = sqr["source_metrics"][0]

        # hn_p1: clean → accepted
        # hn_p2: suspected_self_promo + launch_hype + product_launch, no pain → noise
        # hn_p3: maintainer_housekeeping → noise
        self.assertEqual(m["accepted_signal_count"], 1)
        self.assertEqual(m["noise_signal_count"], 2)
        self.assertEqual(m["weak_signal_count"], 0)

    def test_pilot_clean_traceability_preserved(self):
        evidence = [
            _make_pilot_evidence(
                evidence_id="hn_t1",
                source_url="https://news.ycombinator.com/item?id=42",
                title="Clean pain signal",
                body="We struggle with debugging agent workflows. It's a critical problem.",
                quality_flags=["debugging_pain"],
            ),
        ]
        result = run_operational_discovery_pilot(
            OperationalDiscoveryPilotInput(
                raw_evidence=evidence,
                discovery_run_id="test_traceability",
                created_at="2026-01-01T00:00:00Z",
            )
        )
        self.assertTrue(result.is_valid)
        ts = result.source_quality_report["traceability_summary"]
        self.assertTrue(ts["source_url_validation_passed"])


# =========================================================================
# 10. Serialization roundtrips preserve classification fields
# =========================================================================

class TestSerializationRoundtrips(unittest.TestCase):
    def test_classify_noise_for_evidence_dict_roundtrip(self):
        ev = _make_evidence(
            quality_flags=["requires_manual_review"],
            evidence_kind="pain_signal_candidate",
        )
        classification = classify_noise_for_evidence(ev)
        self.assertEqual(classification, WEAK)

        serialized = json.dumps(ev, sort_keys=True)
        restored = json.loads(serialized)
        classification2 = classify_noise_for_evidence(restored)
        self.assertEqual(classification, classification2)

    def test_classify_noise_for_signal_dict_roundtrip(self):
        sig = _make_signal(
            quality_flags=["maintainer_housekeeping"],
        )
        classification = classify_noise_for_signal(sig)
        self.assertEqual(classification, NOISE)

        serialized = json.dumps(sig, sort_keys=True)
        restored = json.loads(serialized)
        classification2 = classify_noise_for_signal(restored)
        self.assertEqual(classification, classification2)

    def test_source_quality_report_to_dict_has_counts(self):
        evidence = [
            _make_evidence(evidence_id="ev_1", quality_flags=[]),
            _make_evidence(evidence_id="ev_2", quality_flags=["bot_generated"]),
        ]
        signals = [
            {
                "signal_id": f"sig_{ev['evidence_id']}",
                "evidence_id": ev["evidence_id"],
                "source_id": ev["source_id"],
                "source_type": ev["source_type"],
                "source_url": ev.get("source_url", ""),
                "classification": "pain_signal_candidate",
                "signal_type": "pain_signal",
                "quality_flags": ev.get("quality_flags", []),
                "evidence_kind": ev.get("evidence_kind", "pain_signal_candidate"),
                "title": ev.get("title", ""),
                "body": ev.get("body", ""),
                "excerpt": ev.get("excerpt", ""),
            }
            for ev in evidence
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_roundtrip",
            created_at="2026-01-01T00:00:00Z",
        )
        d = report.to_dict()
        self.assertIn("accepted_signal_total", d)
        self.assertIn("weak_signal_total", d)
        self.assertIn("noise_signal_total", d)
        restored = report.from_dict(d)
        self.assertEqual(restored.accepted_signal_total, d["accepted_signal_total"])
        self.assertEqual(restored.weak_signal_total, d["weak_signal_total"])
        self.assertEqual(restored.noise_signal_total, d["noise_signal_total"])


# =========================================================================
# 11. No traceability behavior is weakened
# =========================================================================

class TestTraceabilityUnchanged(unittest.TestCase):
    def test_missing_source_url_errors_preserved(self):
        evidence = [
            _make_pilot_evidence(
                evidence_id="ev_bad",
                source_url="",
                quality_flags=[],
            ),
        ]
        result = run_operational_discovery_pilot(
            OperationalDiscoveryPilotInput(
                raw_evidence=evidence,
                discovery_run_id="test_trace",
                created_at="2026-01-01T00:00:00Z",
            )
        )
        self.assertFalse(result.is_valid)
        self.assertTrue(len(result.errors) > 0)
        self.assertTrue(any("source_url" in e.lower() for e in result.errors))

    def test_valid_source_url_still_passes(self):
        evidence = [
            _make_pilot_evidence(
                evidence_id="ev_good",
                source_url="https://news.ycombinator.com/item?id=1",
                quality_flags=[],
            ),
        ]
        result = run_operational_discovery_pilot(
            OperationalDiscoveryPilotInput(
                raw_evidence=evidence,
                discovery_run_id="test_trace_ok",
                created_at="2026-01-01T00:00:00Z",
            )
        )
        self.assertTrue(result.is_valid)

    def test_placeholder_url_still_caught(self):
        evidence = [
            {
                "evidence_id": "ev_placeholder",
                "source_id": "hacker_news",
                "source_type": "discussion",
                "source_url": "urn:oos:placeholder",
                "title": "Test",
                "body": "Content",
                "evidence_kind": "pain_signal_candidate",
                "created_at": "2026-01-01T00:00:00Z",
                "collected_at": "2026-01-01T00:00:00Z",
                "fetched_at": "2026-01-01T00:00:00Z",
                "topic_id": "test",
                "query_kind": "test",
                "quality_flags": [],
                "raw_metadata": {},
            },
        ]
        result = run_operational_discovery_pilot(
            OperationalDiscoveryPilotInput(
                raw_evidence=evidence,
                discovery_run_id="test_placeholder",
                created_at="2026-01-01T00:00:00Z",
            )
        )
        self.assertFalse(result.is_valid)


# =========================================================================
# 12. No source scope behavior is weakened
# =========================================================================

class TestSourceScopeUnchanged(unittest.TestCase):
    def test_deferred_source_still_rejected(self):
        evidence = [
            {
                "evidence_id": "ph_001",
                "source_id": "product_hunt",
                "source_type": "discussion",
                "source_url": "https://producthunt.com/posts/1",
                "title": "PH post",
                "body": "content",
                "evidence_kind": "pain_signal_candidate",
                "created_at": "2026-01-01T00:00:00Z",
                "collected_at": "2026-01-01T00:00:00Z",
                "fetched_at": "2026-01-01T00:00:00Z",
                "topic_id": "testing",
                "query_kind": "test",
                "quality_flags": [],
                "raw_metadata": {},
            },
        ]
        result = run_operational_discovery_pilot(
            OperationalDiscoveryPilotInput(
                raw_evidence=evidence,
                discovery_run_id="test_scope",
                created_at="2026-01-01T00:00:00Z",
            )
        )
        self.assertFalse(result.is_valid)
        self.assertTrue(any("product_hunt" in e.lower() for e in result.errors))

    def test_allowed_sources_still_pass(self):
        evidence = [
            _make_pilot_evidence(
                evidence_id="hn_ok",
                source_url="https://news.ycombinator.com/item?id=1",
                quality_flags=[],
            ),
        ]
        result = run_operational_discovery_pilot(
            OperationalDiscoveryPilotInput(
                raw_evidence=evidence,
                discovery_run_id="test_scope_ok",
                created_at="2026-01-01T00:00:00Z",
            )
        )
        self.assertTrue(result.is_valid)


# =========================================================================
# Additional edge cases
# =========================================================================

class TestEdgeCases(unittest.TestCase):
    def test_multiple_severe_flags_noise(self):
        result = classify_noise(
            quality_flags=["bot_generated", "flamewar_or_meta_discussion"],
            evidence_kind="pain_signal_candidate",
            title="Any title",
            body="Any body with pain and struggle and problems.",
        )
        self.assertEqual(result, NOISE)

    def test_multiple_medium_flags_weak(self):
        result = classify_noise(
            quality_flags=["unclear_actor", "unclear_workflow", "no_business_cost"],
            evidence_kind="pain_signal_candidate",
            title="Development is hard",
            body="People find software development difficult.",
        )
        self.assertEqual(result, WEAK)

    def test_no_flags_no_content_accepted(self):
        result = classify_noise(
            quality_flags=[],
            evidence_kind="",
            title="",
            body="",
            excerpt="",
        )
        self.assertEqual(result, ACCEPTED)

    def test_none_quality_flags_accepted(self):
        result = classify_noise(
            quality_flags=None,
            evidence_kind="pain_signal_candidate",
            title="Debugging is hard",
            body="We have real problems with agent debugging.",
        )
        self.assertEqual(result, ACCEPTED)

    def test_empty_string_quality_flags_list(self):
        result = classify_noise(
            quality_flags=[""],
            evidence_kind="pain_signal_candidate",
            title="Title",
            body="Pain evidence with struggle and problems.",
        )
        self.assertEqual(result, ACCEPTED)

    def test_derived_signals_propagate_quality_flags(self):
        evidence = [
            {
                "evidence_id": "ev_qf",
                "source_id": "hacker_news",
                "source_type": "discussion",
                "source_url": "https://news.ycombinator.com/item?id=1",
                "title": "Test",
                "body": "Content",
                "evidence_kind": "pain_signal_candidate",
                "quality_flags": ["requires_manual_review", "stale_issue"],
                "excerpt": "",
                "created_at": "2026-01-01T00:00:00Z",
                "collected_at": "2026-01-01T00:00:00Z",
                "fetched_at": "2026-01-01T00:00:00Z",
                "topic_id": "test",
                "query_kind": "test",
                "raw_metadata": {"target_user": "developer"},
            },
        ]
        signals = _derive_minimal_candidate_signals(evidence, "2026-01-01T00:00:00Z")
        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertIn("quality_flags", sig)
        self.assertEqual(sig["quality_flags"], ["requires_manual_review", "stale_issue"])
        self.assertIn("evidence_kind", sig)
        self.assertEqual(sig["evidence_kind"], "pain_signal_candidate")

    def test_flamewar_always_noise(self):
        result = classify_noise(
            quality_flags=["flamewar_or_meta_discussion"],
            evidence_kind="pain_signal_candidate",
            title="Rust vs Go debate",
            body="Rust is better than Go because of ownership. Also debugging agents is hard and broken and frustrating.",
        )
        self.assertEqual(result, NOISE)

    def test_wishlist_without_pain_weak(self):
        result = classify_noise(
            quality_flags=["wishlist_without_pain"],
            evidence_kind="feature_request",
            title="Add dark mode please",
            body="It would be nice to have a dark mode option in the settings.",
        )
        self.assertEqual(result, WEAK)

    def test_one_off_bug_weak(self):
        result = classify_noise(
            quality_flags=["one_off_bug"],
            evidence_kind="bug_report",
            title="Crashes on Python 3.7 on Windows XP",
            body="This only happens with a specific locale setting and an old OS.",
        )
        self.assertEqual(result, WEAK)


if __name__ == "__main__":
    unittest.main()
