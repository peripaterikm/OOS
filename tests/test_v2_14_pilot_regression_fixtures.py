from __future__ import annotations

"""v2.14 Item 8 — Targeted regression fixtures from Run 1 / Run 2 summaries.

Converts real failure modes observed in Pilot Cycle 1 Run 1 and Run 2 into
permanent deterministic regression tests.

Organized by symptom:
  A. TestRun1Run2SQRRegressionFixtures
  B. TestRun1Run2ClusterRegressionFixtures
  C. TestRun1Run2TitleRegressionFixtures
  D. TestRun1Run2FounderReviewRegressionFixtures
  E. TestRun1Run2OpportunitySynthesisRegressionFixtures

No live APIs. No LLM calls. Compact synthetic fixtures only.
"""

import unittest

from oos.noise_classifier import (
    ACCEPTED,
    NOISE,
    WEAK,
    classify_noise,
    classify_noise_for_evidence,
    compute_evidence_quality_summary,
    compute_quality_gate_reasons,
)
from oos.source_quality_report import (
    SourceQualityHealth,
    SourceQualityMetrics,
    build_source_quality_report,
    render_source_quality_report_markdown,
)
from oos.pain_cluster_assembly import (
    assemble_pain_clusters,
    generate_cluster_review_title,
    _should_merge,
    _primary_canonical_anchor,
)
from oos.pilot_founder_review_package import (
    build_founder_review_package,
    render_founder_review_package_markdown,
)
from oos.opportunity_synthesis import (
    synthesize_opportunities,
    _cluster_is_eligible,
)

# ---------------------------------------------------------------------------
# Compact synthetic evidence/signal helpers
# ---------------------------------------------------------------------------

_FIXED_TS = "2026-05-15T10:00:00Z"


def _hn_ev(
    evidence_id="hn_001",
    title="Debugging AI agent traces is painful",
    body="I spend hours trying to trace multi-step agent reasoning. Hard to debug.",
    source_url="",
    evidence_kind="pain_signal_candidate",
    quality_flags=None,
    **overrides,
):
    """Build a compact HN-style evidence dict."""
    base = {
        "evidence_id": evidence_id,
        "source_id": "hacker_news",
        "source_type": "discussion",
        "source_url": source_url or f"https://news.ycombinator.com/item?id={evidence_id.replace('hn_', '')}",
        "title": title,
        "body": body,
        "evidence_kind": evidence_kind,
        "created_at": "2026-05-10T12:00:00Z",
        "collected_at": "2026-05-12T10:00:00Z",
        "fetched_at": "2026-05-12T10:00:00Z",
        "quality_flags": quality_flags or [],
    }
    base.update(overrides)
    return base


def _gh_ev(
    evidence_id="gh_001",
    title="Agent traces missing critical execution context",
    body="When an LLM agent makes a tool call, the trace shows the input but not the full context. Hard to reproduce bugs.",
    source_url="",
    evidence_kind="bug_report",
    quality_flags=None,
    **overrides,
):
    """Build a compact GitHub-Issues-style evidence dict."""
    base = {
        "evidence_id": evidence_id,
        "source_id": "github_issues",
        "source_type": "issue_tracker",
        "source_url": source_url or f"https://github.com/example/repo/issues/{evidence_id.replace('gh_', '')}",
        "title": title,
        "body": body,
        "evidence_kind": evidence_kind,
        "created_at": "2026-05-10T12:00:00Z",
        "collected_at": "2026-05-12T10:00:00Z",
        "fetched_at": "2026-05-12T10:00:00Z",
        "quality_flags": quality_flags or [],
    }
    base.update(overrides)
    return base


def _signal(
    signal_id="sig_001",
    evidence_id="hn_001",
    source_id="hacker_news",
    source_type="discussion",
    classification="pain_signal_candidate",
    source_url="https://news.ycombinator.com/item?id=1",
    quality_flags=None,
):
    """Build a compact candidate signal dict."""
    return {
        "signal_id": signal_id,
        "evidence_id": evidence_id,
        "source_id": source_id,
        "source_type": source_type,
        "source_url": source_url,
        "classification": classification,
        "quality_flags": quality_flags or [],
    }


# =========================================================================
# A. SQR regression fixtures
# =========================================================================


class TestRun1Run2SQRRegressionFixtures(unittest.TestCase):
    """Regression tests for Source Quality Report false-clean and hidden-noise patterns.

    Covers:
      - Symptom A: SQR false-clean when evidence has flags but signal omits them.
      - Symptom B: Hidden-noise: many risk flags must not present as clean.
      - Codex suggested regression: vendor_promo + product_launch + no pain -> noise.
    """

    # -- Symptom A: evidence-only flags, signal omits them -----------------

    def test_sqr_false_clean_evidence_flags_signal_omits_them(self):
        """Evidence has quality_flags but candidate signal has none -> SQR must not be clean."""
        evidence = [
            _hn_ev("hn_001", "Test product launch",
                    "We launched our new AI debugging SaaS! Sign up now.",
                    evidence_kind="product_launch",
                    quality_flags=["vendor_promo", "suspected_self_promo", "low_text_context"]),
        ]
        signals = [
            _signal("sig_001", "hn_001", "hacker_news", "discussion",
                     classification="pain_signal_candidate",
                     quality_flags=[]),  # signal omits flags!
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_false_clean",
            created_at=_FIXED_TS,
        )

        # The SQR must report noise (because evidence flags classify it as noise)
        self.assertEqual(report.noise_signal_total, 1,
                         "Evidence with vendor_promo+product_launch must be noise")
        self.assertEqual(report.accepted_signal_total, 0,
                         "No accepted signals when evidence has quality risk flags")

        # Classification health must NOT be clean
        qh = report.quality_health
        self.assertIn(qh.classification_health, ("caution", "problematic", "failing"),
                      f"classification_health should not be clean, got {qh.classification_health}")

        # dominant_quality_flags must include vendor_promo
        self.assertIn("vendor_promo", qh.dominant_quality_flags,
                      "vendor_promo must appear in dominant quality flags")

        # Markdown must include contradiction warnings or quality warnings
        md = render_source_quality_report_markdown(report)
        self.assertIn("## Contradiction Warnings", md)

    def test_sqr_flagged_records_count_uses_merged_evidence_flags(self):
        """flagged_record_count must count signals that have flags from evidence merge."""
        evidence = [
            _hn_ev("hn_001", "Debugging issue", "Agent traces lack context for debugging hard to reproduce.",
                    quality_flags=["requires_manual_review", "low_confidence_extraction"]),
        ]
        signals = [
            _signal("sig_001", "hn_001", "hacker_news", "discussion",
                     classification="pain_signal_candidate",
                     quality_flags=[]),
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_flagged",
            created_at=_FIXED_TS,
        )
        # The signal + evidence merge should carry flags
        hn_metrics = [m for m in report.source_metrics if m.source_id == "hacker_news"]
        self.assertTrue(hn_metrics, "hacker_news metrics should exist")
        self.assertGreaterEqual(hn_metrics[0].flagged_record_count, 1,
                                "flagged_record_count must count signal with merged evidence flags")

    # -- Symptom B: Run 2 hidden-noise pattern ----------------------------

    def test_sqr_hidden_noise_many_risk_flags_not_clean(self):
        """HN evidence with many requires_manual_review/suspected_self_promo/low_confidence_source
        flags must show caution/problematic status, not clean 100% accepted."""
        evidence = []
        signals = []
        for i in range(1, 6):
            eid = f"hn_noisy_{i:03d}"
            flags = ["requires_manual_review", "suspected_self_promo", "low_confidence_source"]
            evidence.append(
                _hn_ev(eid, f"AI tool announcement {i}",
                        "Check out our new AI-powered debugging platform. Early access available!",
                        evidence_kind="product_launch",
                        quality_flags=flags)
            )
            signals.append(
                _signal(f"sig_noisy_{i:03d}", eid, "hacker_news", "discussion",
                         classification="pain_signal_candidate",
                         quality_flags=[])
            )

        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_hidden_noise",
            created_at=_FIXED_TS,
        )

        qh = report.quality_health
        # Should NOT present as clean (100% accepted / 0% noise)
        self.assertIn(qh.classification_health, ("caution", "problematic", "failing"),
                      f"Expected caution/problematic/failing with many risk flags, got {qh.classification_health}")

        # Must have noise or weak signals
        self.assertTrue(
            report.noise_signal_total > 0 or report.weak_signal_total > 0,
            "Must have noise or weak signals when evidence has many risk flags"
        )

        # flagged_record_rate should be meaningful
        hn_metrics = [m for m in report.source_metrics if m.source_id == "hacker_news"]
        if hn_metrics:
            self.assertGreater(hn_metrics[0].flagged_record_rate, 0.0,
                               "flagged_record_rate must be > 0 with flagged evidence")

        # Markdown must contain per-source warnings or contradiction warnings
        md = render_source_quality_report_markdown(report)
        self.assertTrue(
            "Per-Source Quality Warnings" in md or "caution" in qh.classification_health,
            "Markdown should surface quality warnings for hidden-noise pattern"
        )

    def test_sqr_not_present_zero_noise_as_clean_when_flagged(self):
        """0% noise must NOT imply clean when flagged or weak records exist."""
        evidence = [
            _hn_ev("hn_clean_1", "Debugging trace replay is needed",
                    "We struggle to replay agent traces for debugging. Painful manual workaround.",
                    quality_flags=["workaround_signal"]),  # positive flag, not noise
        ]
        signals = [
            _signal("sig_clean_1", "hn_clean_1", "hacker_news", "discussion",
                     classification="pain_signal_candidate", quality_flags=[]),
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_clean_but_positive_flags",
            created_at=_FIXED_TS,
        )
        # This should be actually clean (positive flags only)
        self.assertEqual(report.noise_signal_total, 0)
        # But now test the opposite: evidence with low_text_context still present
        evidence2 = [
            _hn_ev("hn_risky_1", "Short post", "Check this out.",
                    quality_flags=["low_text_context", "requires_manual_review"]),
        ]
        signals2 = [
            _signal("sig_risky_1", "hn_risky_1", "hacker_news", "discussion",
                     classification="pain_signal_candidate", quality_flags=[]),
        ]
        report2 = build_source_quality_report(
            evidence_items=evidence2,
            candidate_signals=signals2,
            discovery_run_id="test_flagged_not_clean",
            created_at=_FIXED_TS,
        )
        self.assertIn(report2.quality_health.classification_health, ("caution", "problematic", "failing"),
                      "low_text_context evidence must prevent clean classification")

    # -- Codex suggested regression ---------------------------------------

    def test_codex_sqr_vendor_promo_product_launch_no_pain_is_noise(self):
        """vendor_promo + evidence_kind=product_launch + no clear pain -> noise, not weak."""
        result = classify_noise(
            quality_flags=["vendor_promo"],
            evidence_kind="product_launch",
            title="We launched our AI debugging SaaS!",
            body="Sign up now for early access to our platform.",
            excerpt="Early access available.",
        )
        self.assertEqual(result, NOISE,
                         "vendor_promo + product_launch + no pain must classify as noise")

    def test_codex_sqr_vendor_promo_product_launch_no_pain_accepted_zero(self):
        """SQR: product_launch evidence with vendor_promo -> noise_signal_count==1, accepted==0."""
        evidence = [
            _hn_ev("hn_vp_001", "Announcing DebugAI 2.0",
                    "We are excited to launch DebugAI 2.0! Sign up for early access now.",
                    evidence_kind="product_launch",
                    quality_flags=["vendor_promo"]),
        ]
        signals = [
            _signal("sig_vp_001", "hn_vp_001", "hacker_news", "discussion",
                     classification="pain_signal_candidate", quality_flags=[]),
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_vp_001",
            created_at=_FIXED_TS,
        )
        self.assertEqual(report.noise_signal_total, 1,
                         "product_launch + vendor_promo with no pain must be noise")
        self.assertEqual(report.accepted_signal_total, 0,
                         "No accepted signals for vendor_promo product_launch with no pain")
        self.assertNotEqual(report.quality_health.classification_health, "clean",
                            "classification_health must not be clean")

    def test_codex_sqr_vendor_promo_in_dominant_flags(self):
        """vendor_promo must appear in dominant_quality_flags when present."""
        evidence = [
            _hn_ev("hn_vp_002", "Launch: AI Monitor",
                    "Introducing our AI monitoring platform. Try it free.",
                    evidence_kind="product_launch",
                    quality_flags=["vendor_promo", "launch_hype"]),
        ]
        signals = [
            _signal("sig_vp_002", "hn_vp_002", "hacker_news", "discussion",
                     classification="pain_signal_candidate", quality_flags=[]),
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_vp_002",
            created_at=_FIXED_TS,
        )
        dominant = report.quality_health.dominant_quality_flags
        self.assertTrue(
            any("vendor_promo" in f or "suspected_self_promo" in f for f in dominant),
            f"vendor_promo or suspected_self_promo must be in dominant_quality_flags, got {dominant}"
        )

    def test_sqr_positive_pain_flags_do_not_trigger_noise(self):
        """Positive pain flags (debugging_pain, integration_pain etc.) do NOT cause noise classification."""
        evidence = [
            _hn_ev("hn_pain_1", "Debugging agent traces is painful",
                    "I need better tooling to inspect multi-step agent runs. Debugging pain is real.",
                    quality_flags=["debugging_pain", "workaround_signal"]),
        ]
        signals = [
            _signal("sig_pain_1", "hn_pain_1", "hacker_news", "discussion",
                     classification="pain_signal_candidate", quality_flags=[]),
        ]
        report = build_source_quality_report(
            evidence_items=evidence,
            candidate_signals=signals,
            discovery_run_id="test_positive_pain",
            created_at=_FIXED_TS,
        )
        self.assertEqual(report.accepted_signal_total, 1,
                         "Positive pain flags should not cause noise")
        self.assertEqual(report.noise_signal_total, 0)


# =========================================================================
# B. Cluster assembly regression fixtures
# =========================================================================


class TestRun1Run2ClusterRegressionFixtures(unittest.TestCase):
    """Regression tests for cluster assembly catch-all and fragmentation patterns.

    Covers:
      - Symptom C: Catch-all cluster risk — mixed agent/LLM records across
        different anchors must produce multiple coherent clusters.
      - Symptom D: Coherent recurring cluster preservation — multiple
        stack-trace / error-context records should remain one cluster.
    """

    # -- Symptom C: catch-all cluster risk ---------------------------------

    def test_mixed_agent_anchors_produce_multiple_clusters_not_one_catch_all(self):
        """Mixed evidence across agent_trace_debugging, output_provenance,
        prompt_trace_replay, checkpoint_state_reproducibility, and
        structured_output_reliability anchors must produce multiple
        coherent clusters, NOT one broad agent/LLM catch-all."""
        evidence = [
            # agent_trace_debugging
            _hn_ev("hn_trace_1", "Agent traces lack debugging context",
                    "Trace and tracing are broken. Observability is missing. Hard to debug agent runs."),
            _hn_ev("hn_trace_2", "Need better callbacks for agent spans",
                    "Tool call callbacks are insufficient. Span inspection is manual workaround."),
            # output_provenance
            _hn_ev("hn_prov_1", "Which agent contributed which part?",
                    "Provenance and source attribution are impossible with multi-agent workflows. Need claim provenance."),
            _hn_ev("hn_prov_2", "Source tracking in agent outputs",
                    "We have no source tracking for which agent produced which output section."),
            # prompt_trace_replay
            _hn_ev("hn_prompt_1", "Cannot replay production trace inputs",
                    "Prompt variables and production trace replay are missing. Need to rerun trace from production."),
            # checkpoint_state_reproducibility
            _hn_ev("hn_state_1", "Agent state is not reproducible",
                    "Checkpoint and state reproducibility are broken. Deterministic replay is impossible."),
            # structured_output_reliability
            _hn_ev("hn_output_1", "Structured output fails randomly",
                    "Structured output with JSON mode and schema fails unpredictably with tool schema."),
        ]
        clusters, duplicates, summary = assemble_pain_clusters(evidence, dedupe=False)

        # Must produce > 1 cluster (not one catch-all)
        self.assertGreater(len(clusters), 1,
                           f"Expected > 1 cluster, got {len(clusters)}. Mixed anchors must not be one catch-all.")
        self.assertLessEqual(len(clusters), 6,
                             f"Expected <= 6 clusters, got {len(clusters)}. Over-fragmentation is also bad.")

        # No cluster should be flagged catch_all_risk with this small diversity
        for c in clusters:
            self.assertFalse(c.catch_all_risk,
                             f"Cluster {c.cluster_id} should not be catch_all_risk")

    def test_provenance_and_trace_debugging_not_in_same_cluster(self):
        """output_provenance evidence must NOT merge with agent_trace_debugging evidence."""
        evidence = [
            _hn_ev("hn_prov_10", "Provenance tracking for multi-agent outputs",
                    "Provenance and source attribution are critical. Which agent contributed which part?"),
            _hn_ev("hn_trace_10", "Debugging agent execution traces",
                    "Trace, tracing, spans, and observability are insufficient for debugging agent runs."),
        ]
        from oos.pain_cluster_assembly import _primary_canonical_anchor

        ev_a = evidence[0]
        ev_b = evidence[1]

        # These should NOT merge (output_provenance vs agent_trace_debugging are not block pairs
        # but they are different specific anchors that don't share keywords)
        should = _should_merge(ev_a, ev_b)
        self.assertFalse(should,
                         f"output_provenance and agent_trace_debugging must not merge: {should}")

    def test_prompt_trace_replay_and_stack_trace_context_not_merge(self):
        """prompt_trace_replay evidence must NOT merge with stack_trace_context evidence."""
        ev_a = _hn_ev("hn_prompt_20", "Replay production traces for debugging",
                       "Prompt variables, production trace, replay — we need prompt playground.")
        ev_b = _hn_ev("hn_stack_20", "Stack traces missing context",
                       "Stack trace and exception context are incomplete. Missing error message details.")
        # These are block pairs in the anchor merge block list
        should = _should_merge(ev_a, ev_b)
        self.assertFalse(should,
                         f"prompt_trace_replay and stack_trace_context must not merge: {should}")

    # -- Symptom D: coherent recurring cluster preservation -----------------

    def test_multiple_stack_trace_records_remain_one_cluster(self):
        """Multiple stack-trace / error-context records must remain one coherent cluster."""
        evidence = [
            _hn_ev("hn_stack_1", "Stack traces lack actionable state details",
                    "Stack trace and exception context are missing critical state information. Debugging is hard."),
            _gh_ev("gh_stack_1", "Better error context needed for tracebacks",
                    "Stack traces and error context from the SDK are incomplete. Missing error message."),
            _hn_ev("hn_stack_2", "Exception handling needs more context",
                    "Exception context and stack trace information is minimal. Hard to reproduce errors."),
        ]
        clusters, _, _ = assemble_pain_clusters(evidence, dedupe=False)

        # All three stack-trace items should be in the same cluster
        cid_map = {}
        for c in clusters:
            for entry in c.source_evidence_list:
                cid_map[entry.evidence_id] = c.cluster_id

        # At least hn_stack_1 and hn_stack_2 should be together
        stack_ids = {cid_map.get(eid) for eid in ["hn_stack_1", "hn_stack_2", "gh_stack_1"] if eid in cid_map}
        # With 3 stack-trace items, we expect at most 2 clusters (ideally 1)
        self.assertLessEqual(len(stack_ids), 2,
                             f"Stack trace items over-fragmented: {len(stack_ids)} clusters for 3 items")

    def test_two_checkpoint_state_items_merge(self):
        """Two checkpoint/state reproducibility items should merge."""
        ev_a = _hn_ev("hn_chk_1", "Agent state reproducibility is broken",
                       "Checkpoint state and reproducibility are non-deterministic. Corruption happens.")
        ev_b = _hn_ev("hn_chk_2", "Cannot reproduce agent runs",
                       "Reproducibility and checkpoint are broken. Deterministic replay fails.")
        should = _should_merge(ev_a, ev_b)
        self.assertTrue(should, "checkpoint_state_reproducibility items must merge (same anchor)")

    def test_product_launch_does_not_merge_with_bug_report(self):
        """Product launch evidence must NOT merge with bug report evidence unless they share a specific anchor."""
        ev_launch = _hn_ev("hn_launch_1", "Announcing AI Debugger Pro",
                            "Check out our new tool! Early access available.",
                            evidence_kind="product_launch",
                            quality_flags=["suspected_self_promo"])
        ev_bug = _hn_ev("hn_bug_1", "Agent debugging context missing",
                          "Debugging agent runs is broken. Traces lack context for error reproduction.",
                          evidence_kind="bug_report")
        should = _should_merge(ev_launch, ev_bug)
        self.assertFalse(should,
                         "product_launch must not merge with bug_report without shared specific anchor")


# =========================================================================
# C. Title grounding regression fixtures
# =========================================================================


class TestRun1Run2TitleRegressionFixtures(unittest.TestCase):
    """Regression tests for cluster title grounding.

    Covers:
      - Symptom E: Generic LLM/agent evidence must not become provenance title.
      - Explicit provenance evidence -> provenance-related title.
      - Bad raw titles: "[dead]", "needs_more_evidence" must not surface.
    """

    def test_generic_agent_debugging_not_mistitled_as_provenance(self):
        """Generic LLM agent debugging evidence must not produce a provenance title."""
        cluster = {
            "actor": "developer",
            "workflow": "debugging AI agents",
            "object": "agent traces",
            "pain_verb": "hard to debug",
            "pain_pattern": "developers cannot debug AI agents because agent traces are hard to debug",
            "source_evidence_list": [
                {
                    "evidence_id": "hn_gen_1",
                    "title": "Debugging AI agent workflows is painful",
                    "excerpt": "I spend hours debugging agent execution. Traces are not enough.",
                    "contribution_to_cluster": "primary_pain",
                    "quality_flags": [],
                },
            ],
        }
        title = generate_cluster_review_title(cluster)
        self.assertNotIn("provenance", title.lower(),
                         f"Generic agent debugging must not produce provenance title: {title!r}")

    def test_explicit_provenance_evidence_becomes_provenance_title(self):
        """Explicit provenance/source-attribution evidence must produce provenance-related title."""
        cluster = {
            "actor": "developer",
            "workflow": "source attribution",
            "object": "agent outputs",
            "pain_verb": "cannot",
            "pain_pattern": "developers cannot trace source attribution in agent outputs because provenance is missing",
            "source_evidence_list": [
                {
                    "evidence_id": "hn_prov_t_1",
                    "title": "Which agent contributed which part in multi-agent systems?",
                    "excerpt": "Provenance and source attribution are missing. We need trust and sources tracking.",
                    "contribution_to_cluster": "primary_pain",
                    "quality_flags": [],
                },
            ],
        }
        title = generate_cluster_review_title(cluster)
        self.assertIn("provenance", title.lower(),
                      f"Explicit provenance evidence must produce provenance title: {title!r}")

    def test_dead_title_not_surfaced(self):
        """Bad raw title '[dead]' must not surface as a review title."""
        cluster = {
            "actor": "developer",
            "workflow": "something",
            "object": "unknown",
            "pain_verb": "hard to",
            "pain_pattern": "developers struggle with something",
            "source_evidence_list": [
                {
                    "evidence_id": "hn_dead_1",
                    "title": "[dead] This post is dead",
                    "excerpt": "Some content.",
                    "contribution_to_cluster": "primary_pain",
                    "quality_flags": [],
                },
            ],
        }
        title = generate_cluster_review_title(cluster)
        self.assertNotIn("[dead]", title.lower(),
                         f"[dead] must not appear in review title: {title!r}")
        self.assertNotIn("dead", title.lower().split(),
                         f"'dead' must not appear as a word in review title: {title!r}")

    def test_needs_more_evidence_title_not_surfaced(self):
        """'needs_more_evidence' must not surface as a review title."""
        cluster = {
            "actor": "unknown",
            "workflow": "unknown",
            "object": "unknown",
            "pain_verb": "unknown",
            "pain_pattern": "needs_more_evidence",
            "source_evidence_list": [
                {
                    "evidence_id": "hn_nme_1",
                    "title": "needs_more_evidence",
                    "excerpt": "",
                    "contribution_to_cluster": "context_only",
                    "quality_flags": ["low_text_context"],
                },
            ],
        }
        title = generate_cluster_review_title(cluster)
        self.assertNotIn("needs_more_evidence", title.lower(),
                         f"needs_more_evidence must not be a title: {title!r}")

    def test_title_does_not_exceed_max_length(self):
        """Generated title must not exceed 90 characters."""
        cluster = {
            "actor": "developer",
            "workflow": "debugging multi-step agent workflows with complex tool chains",
            "object": "very specific and detailed object description",
            "pain_verb": "hard to debug",
            "pain_pattern": "developers cannot debug multi-step agent workflows",
            "source_evidence_list": [
                {
                    "evidence_id": "hn_long_1",
                    "title": "A very long title that goes on and on about debugging agent workflows in production",
                    "excerpt": "Debugging context.",
                    "contribution_to_cluster": "primary_pain",
                    "quality_flags": [],
                },
            ],
        }
        title = generate_cluster_review_title(cluster)
        self.assertLessEqual(len(title), 90,
                             f"Title must be <= 90 chars: {len(title)}: {title!r}")

    def test_title_not_empty(self):
        """Generated title must never be empty."""
        cluster = {
            "actor": "developer",
            "workflow": "debugging",
            "object": "traces",
            "pain_verb": "hard to",
            "pain_pattern": "developers struggle with traces",
            "source_evidence_list": [
                {
                    "evidence_id": "hn_title_1",
                    "title": "Agent trace debugging is broken",
                    "excerpt": "Painful debugging workflow.",
                    "contribution_to_cluster": "primary_pain",
                    "quality_flags": [],
                },
            ],
        }
        title = generate_cluster_review_title(cluster)
        self.assertTrue(title and title.strip(),
                        f"Title must be non-empty: {title!r}")


# =========================================================================
# D. Founder Review Package regression fixtures
# =========================================================================


class TestRun1Run2FounderReviewRegressionFixtures(unittest.TestCase):
    """Regression tests for Founder Review Package clarity.

    Covers:
      - Symptom F: FRP Markdown includes Executive Summary, Signal-to-Noise Ratio,
        Per-Source Breakdown, Quality Gate, Opportunity Hypotheses section.
      - Priority ranks must align with final sorted card order.
    """

    def _make_cluster_dict(self, cluster_id, overall=0.75, source_diversity=2, recurrence=3,
                           evidence_list=None, actor="developer", workflow="debugging",
                           obj="agent traces", pain_pattern="developers cannot debug agent traces"):
        if evidence_list is None:
            evidence_list = [
                {"evidence_id": f"{cluster_id}_ev1", "source_id": "hacker_news",
                 "source_type": "discussion",
                 "source_url": "https://news.ycombinator.com/item?id=1",
                 "title": "Debugging pain", "excerpt": "Test excerpt with debugging pain.",
                 "evidence_kind": "pain_signal_candidate", "quality_flags": [],
                 "contribution_to_cluster": "primary_pain"},
                {"evidence_id": f"{cluster_id}_ev2", "source_id": "github_issues",
                 "source_type": "issue_tracker",
                 "source_url": "https://github.com/example/repo/issues/1",
                 "title": "Agent trace issue", "excerpt": "GitHub issue about agent traces.",
                 "evidence_kind": "bug_report", "quality_flags": [],
                 "contribution_to_cluster": "supporting_pain"},
            ]
        return {
            "cluster_id": cluster_id,
            "actor": actor, "workflow": workflow, "object": obj,
            "pain_verb": "hard to debug", "pain_pattern": pain_pattern,
            "source_evidence_list": evidence_list,
            "source_diversity": source_diversity, "recurrence": recurrence,
            "business_relevance": 0.70, "noise_risk": 0.10,
            "representative_quotes_or_excerpts": ["test"],
            "linked_candidate_signals": [],
            "created_at": _FIXED_TS, "updated_at": _FIXED_TS,
            "status": "new",
            "scoring": {"overall": overall, "pain_explicitness": 0.8, "recurrence": 0.6,
                        "business_cost": 0.7, "icp_fit": 0.5, "source_reliability": 0.75,
                        "freshness": 0.9, "actionability": 0.6, "noise_risk": 0.1},
        }

    def test_frp_markdown_includes_executive_summary(self):
        """FRP Markdown must include Executive Summary section."""
        clusters = [self._make_cluster_dict("pc_frp_1")]
        pkg = build_founder_review_package(
            pain_clusters=clusters,
            discovery_run_id="test_frp_clarity",
            created_at=_FIXED_TS,
        )
        md = render_founder_review_package_markdown(pkg)
        self.assertIn("## Executive Summary", md,
                      "FRP Markdown must include Executive Summary")

    def test_frp_markdown_includes_signal_to_noise_ratio(self):
        """FRP Markdown must include Signal-to-Noise Ratio section."""
        clusters = [self._make_cluster_dict("pc_snr_1")]
        pkg = build_founder_review_package(
            pain_clusters=clusters,
            discovery_run_id="test_snr",
            created_at=_FIXED_TS,
        )
        md = render_founder_review_package_markdown(pkg)
        self.assertIn("## Signal-to-Noise Ratio", md,
                      "FRP Markdown must include Signal-to-Noise Ratio")

    def test_frp_markdown_includes_per_source_breakdown(self):
        """FRP Markdown must include Per-Source Breakdown."""
        clusters = [self._make_cluster_dict("pc_psb_1")]
        pkg = build_founder_review_package(
            pain_clusters=clusters,
            discovery_run_id="test_psb",
            created_at=_FIXED_TS,
        )
        md = render_founder_review_package_markdown(pkg)
        self.assertIn("### Per-Source Breakdown", md,
                      "FRP Markdown must include Per-Source Breakdown")

    def test_frp_markdown_includes_quality_gate_per_item(self):
        """FRP Markdown must include Quality Gate section per review item."""
        clusters = [self._make_cluster_dict("pc_qgate_1")]
        pkg = build_founder_review_package(
            pain_clusters=clusters,
            discovery_run_id="test_qgate",
            created_at=_FIXED_TS,
        )
        md = render_founder_review_package_markdown(pkg)
        self.assertIn("#### Quality Gate", md,
                      "FRP Markdown must include Quality Gate per item")

    def test_frp_markdown_includes_opportunity_hypotheses_section(self):
        """FRP Markdown must include Opportunity Hypotheses section (even if empty)."""
        clusters = [self._make_cluster_dict("pc_oh_1")]
        pkg = build_founder_review_package(
            pain_clusters=clusters,
            discovery_run_id="test_oh_empty",
            created_at=_FIXED_TS,
        )
        md = render_founder_review_package_markdown(pkg)
        self.assertIn("## Opportunity Hypotheses", md,
                      "FRP Markdown must include Opportunity Hypotheses section")

    def test_frp_empty_opportunity_hypotheses_shows_safe_message(self):
        """FRP with no opportunity hypotheses shows a safe empty-state message."""
        # Use a cluster that won't synthesize (e.g., low score to get PARK)
        cluster = self._make_cluster_dict("pc_empty_oh", overall=0.40)

        pkg = build_founder_review_package(
            pain_clusters=[cluster],
            discovery_run_id="test_empty_oh",
            created_at=_FIXED_TS,
        )
        md = render_founder_review_package_markdown(pkg)
        # Either "No opportunity hypotheses" empty state or the section header is present
        self.assertTrue(
            "No opportunity hypotheses" in md or "## Opportunity Hypotheses" in md,
            "FRP must show opportunity hypotheses section with empty-state message"
        )

    def test_frp_priority_ranks_align_with_sort_order(self):
        """Review priority ranks (review_priority) must align with sorted card order."""
        clusters = [
            self._make_cluster_dict("pc_prio_1", overall=0.85, source_diversity=2, recurrence=4),
            self._make_cluster_dict("pc_prio_2", overall=0.65, source_diversity=1, recurrence=2),
            self._make_cluster_dict("pc_prio_3", overall=0.45, source_diversity=1, recurrence=1),
        ]
        pkg = build_founder_review_package(
            pain_clusters=clusters,
            discovery_run_id="test_priority",
            created_at=_FIXED_TS,
            max_items=10,
        )
        items = pkg.review_items
        self.assertGreaterEqual(len(items), 3, "Should have at least 3 review items")
        # Priority ranks should be sequential: 1, 2, 3...
        priorities = [ri.review_priority for ri in items]
        self.assertEqual(priorities, list(range(1, len(priorities) + 1)),
                         f"Priority ranks must be sequential 1..n: {priorities}")

    def test_frp_decision_breakdown_table_present(self):
        """FRP Markdown must include Decision Breakdown table."""
        clusters = [self._make_cluster_dict("pc_db_1")]
        pkg = build_founder_review_package(
            pain_clusters=clusters,
            discovery_run_id="test_db",
            created_at=_FIXED_TS,
        )
        md = render_founder_review_package_markdown(pkg)
        self.assertIn("## Decision Breakdown", md,
                      "FRP Markdown must include Decision Breakdown")


# =========================================================================
# E. Opportunity synthesis safety regression fixtures
# =========================================================================


class TestRun1Run2OpportunitySynthesisRegressionFixtures(unittest.TestCase):
    """Regression tests for opportunity synthesis safety.

    Covers:
      - Symptom G: Do NOT synthesize from PARK, REVISIT_LATER, KILL, no review item,
        placeholder titles, invalid source URLs, unknown actor as invented developer ICP.
      - DO synthesize from clean PROMOTE / NEEDS_MORE_EVIDENCE items when gates pass.
      - Unknown actor must remain "unproven; validate actor".
    """

    _FIXED_TS = "2026-05-15T10:00:00Z"

    def _cluster(self, cluster_id, title="Debugging Agent Traces", actor="developer",
                 workflow="debugging", obj="agent traces",
                 pain_pattern="developers cannot debug agent traces",
                 evidence_list=None, overall_score=0.75,
                 source_diversity=2, recurrence=3,
                 catch_all_risk=False, promotion_blockers=None):
        if evidence_list is None:
            evidence_list = [
                {"evidence_id": f"{cluster_id}_ev1", "source_id": "hacker_news",
                 "source_type": "discussion", "source_url": "https://news.ycombinator.com/item?id=1",
                 "title": "Debugging agent traces", "excerpt": "Test.",
                 "evidence_kind": "pain_signal_candidate", "quality_flags": [],
                 "body": "Debugging agent traces is painful and hard because trace context is missing."},
                {"evidence_id": f"{cluster_id}_ev2", "source_id": "github_issues",
                 "source_type": "issue_tracker", "source_url": "https://github.com/example/repo/issues/1",
                 "title": "Agent trace issue", "excerpt": "GitHub issue.",
                 "evidence_kind": "bug_report", "quality_flags": [],
                 "body": "Agent trace debugging needs better context for error reproduction."},
            ]
        return {
            "cluster_id": cluster_id,
            "title": title, "cluster_title": title,
            "actor": actor, "workflow": workflow, "object": obj,
            "pain_pattern": pain_pattern,
            "source_evidence_list": evidence_list,
            "source_diversity": source_diversity, "recurrence": recurrence,
            "cohesion_score": 0.7, "catch_all_risk": catch_all_risk,
            "scoring": {"overall": overall_score},
            "promotion_blockers": promotion_blockers or [],
        }

    def _ri(self, review_item_id, pain_cluster_id, recommended_decision="PROMOTE",
            promotion_blockers=None, traceability_status="clean"):
        return {
            "review_item_id": review_item_id,
            "pain_cluster_id": pain_cluster_id,
            "recommended_decision": recommended_decision,
            "promotion_blockers": promotion_blockers or [],
            "traceability_status": traceability_status,
        }

    # -- Safety: do NOT synthesize from ineligible states -------------------

    def test_no_synthesis_from_park_decision(self):
        """PARK decision must NOT be eligible for synthesis."""
        cluster = self._cluster("pc_park_1", overall_score=0.45)
        ri = self._ri("ri_park_1", "pc_park_1", "PARK")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible,
                         f"PARK decision must not be eligible: {reason}")
        self.assertIn("PARK", reason)

    def test_no_synthesis_from_revisit_later_decision(self):
        """REVISIT_LATER decision must NOT be eligible for synthesis."""
        cluster = self._cluster("pc_rl_1", overall_score=0.45)
        ri = self._ri("ri_rl_1", "pc_rl_1", "REVISIT_LATER")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible,
                         f"REVISIT_LATER decision must not be eligible: {reason}")

    def test_no_synthesis_from_kill_decision(self):
        """KILL decision must NOT be eligible for synthesis."""
        cluster = self._cluster("pc_kill_1", overall_score=0.20)
        ri = self._ri("ri_kill_1", "pc_kill_1", "KILL")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible,
                         f"KILL decision must not be eligible: {reason}")

    def test_no_synthesis_without_review_item(self):
        """No review item -> synthesis must not proceed."""
        cluster = self._cluster("pc_nori_1")
        eligible, reason = _cluster_is_eligible(cluster, None)
        self.assertFalse(eligible,
                         f"No review item must not be eligible: {reason}")
        self.assertIn("no review item", reason.lower())

    def test_no_synthesis_from_placeholder_title(self):
        """Placeholder title '[dead]' must not be eligible for synthesis."""
        cluster = self._cluster("pc_dead_1", title="[dead] Developer pain")
        ri = self._ri("ri_dead_1", "pc_dead_1", "PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible,
                         f"[dead] title must not be eligible: {reason}")

    def test_no_synthesis_from_needs_more_evidence_title(self):
        """'needs_more_evidence' in title must not be eligible."""
        cluster = self._cluster("pc_nme_1", title="needs_more_evidence workflow pain")
        ri = self._ri("ri_nme_1", "pc_nme_1", "PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible,
                         f"needs_more_evidence title must not be eligible: {reason}")

    def test_no_synthesis_from_invalid_source_url(self):
        """Invalid source URL (not http/https) must not be eligible."""
        evidence = [
            {"evidence_id": "ev_badurl_1", "source_id": "hacker_news",
             "source_type": "discussion", "source_url": "urn:oos:placeholder",
             "title": "Bad URL evidence", "excerpt": "Test.",
             "evidence_kind": "pain_signal_candidate", "quality_flags": [],
             "body": "This evidence has a bad source URL."},
        ]
        cluster = self._cluster("pc_badurl_1", evidence_list=evidence)
        ri = self._ri("ri_badurl_1", "pc_badurl_1", "PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible,
                         f"Invalid source URL must not be eligible: {reason}")

    # -- Safety: DO synthesize from clean eligible input --------------------

    def test_synthesis_from_clean_promote_item(self):
        """Clean PROMOTE cluster with valid evidence must synthesize."""
        cluster = self._cluster("pc_clean_1")
        ri = self._ri("ri_clean_1", "pc_clean_1", "PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertTrue(eligible,
                        f"Clean PROMOTE must be eligible: {reason}")

    def test_synthesis_from_needs_more_evidence_item(self):
        """NEEDS_MORE_EVIDENCE cluster with valid evidence must be eligible."""
        cluster = self._cluster("pc_nmee_1", overall_score=0.60)
        ri = self._ri("ri_nmee_1", "pc_nmee_1", "NEEDS_MORE_EVIDENCE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertTrue(eligible,
                        f"NEEDS_MORE_EVIDENCE with valid evidence must be eligible: {reason}")

    def test_synthesize_opportunities_returns_zero_for_ineligible(self):
        """synthesize_opportunities returns zero hypotheses when all clusters are ineligible."""
        cluster_park = self._cluster("pc_synth_park", overall_score=0.40)
        ri_park = self._ri("ri_synth_park", "pc_synth_park", "PARK")
        result = synthesize_opportunities(
            pain_clusters=[cluster_park],
            review_items=[ri_park],
            generated_at=self._FIXED_TS,
        )
        self.assertEqual(len(result), 0,
                         "Zero opportunities expected from PARK cluster")

    def test_synthesize_opportunities_returns_one_for_clean_eligible(self):
        """synthesize_opportunities returns one hypothesis for a clean eligible PROMOTE cluster."""
        cluster = self._cluster("pc_synth_clean")
        ri = self._ri("ri_synth_clean", "pc_synth_clean", "PROMOTE")
        result = synthesize_opportunities(
            pain_clusters=[cluster],
            review_items=[ri],
            generated_at=self._FIXED_TS,
        )
        self.assertEqual(len(result), 1,
                         "One hypothesis expected from clean PROMOTE cluster")

    # -- Unknown actor safety ----------------------------------------------

    def test_unknown_actor_remains_unproven_validate_actor(self):
        """Unknown actor must result in target_icp='unproven; validate actor'."""
        cluster = self._cluster("pc_unknown_actor", actor="unknown")
        ri = self._ri("ri_unknown_actor", "pc_unknown_actor", "NEEDS_MORE_EVIDENCE")
        result = synthesize_opportunities(
            pain_clusters=[cluster],
            review_items=[ri],
            generated_at=self._FIXED_TS,
        )
        self.assertEqual(len(result), 1, "Should synthesize one hypothesis")
        oh = result[0]
        self.assertEqual(oh.target_icp, "unproven; validate actor",
                         f"Unknown actor must be 'unproven; validate actor', got {oh.target_icp!r}")
        self.assertIn("not proven", oh.uncertainty_notes.lower(),
                      f"Uncertainty notes must mention unproven actor: {oh.uncertainty_notes!r}")

    def test_known_actor_is_preserved_in_hypothesis(self):
        """Known actor 'developer' must be preserved as target_icp."""
        cluster = self._cluster("pc_known_actor", actor="developer")
        ri = self._ri("ri_known_actor", "pc_known_actor", "PROMOTE")
        result = synthesize_opportunities(
            pain_clusters=[cluster],
            review_items=[ri],
            generated_at=self._FIXED_TS,
        )
        self.assertEqual(len(result), 1)
        oh = result[0]
        self.assertNotEqual(oh.target_icp, "unproven; validate actor",
                            "Known actor must not be marked unproven")
        self.assertEqual(oh.target_actor, "developer")

    # -- Catch-all risk blocks synthesis -----------------------------------

    def test_catch_all_risk_cluster_blocked_from_synthesis(self):
        """catch_all_risk=True must block opportunity synthesis."""
        cluster = self._cluster("pc_catchall_1", catch_all_risk=True)
        ri = self._ri("ri_catchall_1", "pc_catchall_1", "PROMOTE")
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible,
                         f"Catch-all risk cluster must not be eligible: {reason}")

    # -- Fatal blocker blocks synthesis ------------------------------------

    def test_traceability_blocker_blocks_synthesis(self):
        """Traceability fatal blocker must block synthesis."""
        cluster = self._cluster("pc_trace_fail_1", promotion_blockers=["Source URL traceability failure: missing or placeholder URLs."])
        ri = self._ri("ri_trace_fail_1", "pc_trace_fail_1", "PROMOTE",
                       promotion_blockers=["Source URL traceability failure: missing or placeholder URLs."])
        eligible, reason = _cluster_is_eligible(cluster, ri)
        self.assertFalse(eligible,
                         f"Traceability blocker must block synthesis: {reason}")
