import unittest
import json
from dataclasses import replace
from unittest.mock import patch

from oos.collection_scheduler import CollectionLimits, CollectionScheduler
from oos.github_issues_collector import (
    GitHubIssuesCollector,
    GitHubSourceQualitySummary,
    GH_CANONICAL_SOURCE_ID,
    GH_CANONICAL_SOURCE_TYPE,
    GH_LEGACY_SOURCE_TYPE,
    _classify_evidence_kind,
    _compute_quality_flags,
    _author_context_label,
    _derive_repo_full_name,
    github_issue_to_raw_evidence,
    parse_github_issues,
    build_github_source_quality_summary,
)
from oos.models import RawEvidence, compute_raw_evidence_content_hash
from oos.query_planner import QueryPlanner
from oos.source_registry import default_source_registry, default_topic_profiles


def github_scheduled_item(max_results: int = 25):
    plans = QueryPlanner().build_plans(
        registry=default_source_registry(),
        topic_profiles=default_topic_profiles(),
    )
    github_plan = [plan for plan in plans if plan.source_id == "github_issues"][0]
    queue = CollectionScheduler(
        limits=CollectionLimits(
            max_total_queries=1,
            max_results_per_query=max_results,
            allowed_source_ids={"github_issues"},
        )
    ).build_queue([github_plan])
    return queue[0]


def fixture_payload():
    return {
        "items": [
            {
                "id": 123456789,
                "node_id": "I_kwDOExample",
                "number": 42,
                "html_url": "https://github.com/example/finance-tool/issues/42",
                "url": "https://api.github.com/repos/example/finance-tool/issues/42",
                "repository_url": "https://api.github.com/repos/example/finance-tool",
                "comments_url": "https://api.github.com/repos/example/finance-tool/issues/42/comments",
                "title": "Cashflow report export is painful for SMB users",
                "body": "Our finance team keeps stitching monthly reports together by hand.",
                "state": "open",
                "created_at": "2024-02-03T04:05:06Z",
                "updated_at": "2024-02-04T04:05:06Z",
                "closed_at": None,
                "comments": 5,
                "labels": [{"name": "feature request"}, {"name": "reporting"}],
                "reactions": {"total_count": 3, "+1": 2, "eyes": 1, "url": "ignored"},
                "user": {"login": "raw_github_login"},
            },
            {
                "id": 123456790,
                "number": 43,
                "node_id": "I_kwDOExample2",
                "html_url": "https://github.com/example/finance-tool/issues/43",
                "title": "Need better management reporting workaround",
                "body": "We export CSVs and clean them manually.",
                "state": "open",
                "created_at": "2024-02-05T04:05:06Z",
                "comments": 1,
                "labels": ["workaround"],
                "user": {"login": "another_login"},
            },
        ]
    }


class TestGitHubSourceQualitySummary(unittest.TestCase):
    """Tests for GitHubSourceQualitySummary dataclass."""

    def test_defaults_are_canonical(self) -> None:
        summary = GitHubSourceQualitySummary()
        self.assertEqual(summary.source_id, "github_issues")
        self.assertEqual(summary.source_type, "issue_tracker")

    def test_validate_accepts_valid_summary(self) -> None:
        summary = GitHubSourceQualitySummary(
            records_seen=10, records_emitted=8, records_rejected=1,
            pr_filtered_count=1, warning_count=2, error_count=0,
            duplicate_count=0, missing_url_count=0, placeholder_url_count=0,
        )
        summary.validate()

    def test_validate_rejects_negative_counts(self) -> None:
        summary = GitHubSourceQualitySummary(records_seen=-1)
        with self.assertRaises(ValueError):
            summary.validate()

    def test_validate_rejects_empty_source_id(self) -> None:
        summary = GitHubSourceQualitySummary(source_id="")
        with self.assertRaises(ValueError):
            summary.validate()

    def test_counts_are_tracked_correctly(self) -> None:
        summary = GitHubSourceQualitySummary(
            records_seen=100, records_emitted=80, records_rejected=15,
            pr_filtered_count=5, duplicate_count=3, missing_url_count=2,
            rejection_reasons={"pull_request": 5, "missing_source_url": 2},
        )
        self.assertEqual(summary.records_seen, 100)
        self.assertEqual(summary.pr_filtered_count, 5)
        self.assertEqual(summary.missing_url_count, 2)


class TestCanonicalIdentity(unittest.TestCase):
    """Tests for canonical source_id and source_type."""

    def test_source_id_is_github_issues(self) -> None:
        item = github_scheduled_item()
        evidence = github_issue_to_raw_evidence(
            fixture_payload()["items"][0], scheduled_item=item
        )
        self.assertEqual(evidence.source_id, "github_issues")

    def test_source_type_is_issue_tracker(self) -> None:
        item = github_scheduled_item()
        evidence = github_issue_to_raw_evidence(
            fixture_payload()["items"][0], scheduled_item=item
        )
        self.assertEqual(evidence.source_type, "issue_tracker")

    def test_collector_default_source_id(self) -> None:
        collector = GitHubIssuesCollector()
        self.assertEqual(collector.source_id, "github_issues")

    def test_supports_canonical_source_type(self) -> None:
        item = github_scheduled_item()
        canonical_item = replace(item, source_type="issue_tracker")
        collector = GitHubIssuesCollector(fixture_payload=fixture_payload())
        self.assertTrue(collector.supports(canonical_item))

    def test_supports_legacy_source_type(self) -> None:
        item = github_scheduled_item()
        collector = GitHubIssuesCollector(fixture_payload=fixture_payload())
        self.assertTrue(collector.supports(item))

    def test_emits_canonical_even_with_legacy_scheduled_item(self) -> None:
        item = github_scheduled_item()
        # item has legacy source_type="github_issues"
        result = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)
        for ev in result.evidence:
            self.assertEqual(ev.source_type, "issue_tracker")
            self.assertEqual(ev.source_id, "github_issues")


class TestSourceURLHardening(unittest.TestCase):
    """Tests for source_url: no github:// fallback, http(s) only."""

    def test_source_url_uses_html_url(self) -> None:
        item = github_scheduled_item()
        evidence = github_issue_to_raw_evidence(
            fixture_payload()["items"][0], scheduled_item=item
        )
        self.assertEqual(
            evidence.source_url,
            "https://github.com/example/finance-tool/issues/42",
        )

    def test_missing_html_url_rejects_with_reason(self) -> None:
        item = github_scheduled_item()
        summary = GitHubSourceQualitySummary()
        issue = {
            "id": 999, "node_id": "I_kwDOTest",
            "number": 99, "title": "No URL",
            "body": "Some body",
        }
        evidence = github_issue_to_raw_evidence(
            issue, scheduled_item=item, quality_summary=summary
        )
        self.assertIsNone(evidence)
        self.assertEqual(summary.missing_url_count, 1)
        self.assertEqual(summary.records_rejected, 1)
        self.assertIn("missing_source_url", summary.rejection_reasons)

    def test_empty_html_url_rejects(self) -> None:
        item = github_scheduled_item()
        summary = GitHubSourceQualitySummary()
        issue = {
            "id": 999, "node_id": "I_kwDOTest",
            "number": 99, "title": "Empty URL",
            "body": "Some body", "html_url": "",
        }
        evidence = github_issue_to_raw_evidence(
            issue, scheduled_item=item, quality_summary=summary
        )
        self.assertIsNone(evidence)
        self.assertEqual(summary.missing_url_count, 1)

    def test_github_fallback_not_used(self) -> None:
        item = github_scheduled_item()
        summary = GitHubSourceQualitySummary()
        issue = {
            "id": 999, "node_id": "I_kwDOTest",
            "number": 99, "title": "API URL only",
            "body": "Some body",
            "url": "https://api.github.com/repos/example/repo/issues/99",
        }
        evidence = github_issue_to_raw_evidence(
            issue, scheduled_item=item, quality_summary=summary
        )
        # No html_url means rejected; url (API) is not accepted as source_url
        self.assertIsNone(evidence)
        self.assertEqual(summary.missing_url_count, 1)

    def test_all_emitted_urls_start_with_https(self) -> None:
        item = github_scheduled_item()
        result = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)
        for ev in result.evidence:
            self.assertTrue(
                ev.source_url.startswith("https://github.com/"),
                f"source_url {ev.source_url} does not start with https://github.com/",
            )

    def test_no_placeholder_urls_in_output(self) -> None:
        item = github_scheduled_item()
        result = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)
        for ev in result.evidence:
            self.assertNotIn("github://", ev.source_url)
            self.assertNotIn("urn:", ev.source_url)


class TestPullRequestFiltering(unittest.TestCase):
    """Tests for mandatory PR filtering."""

    def test_pr_issue_is_filtered(self) -> None:
        item = github_scheduled_item()
        summary = GitHubSourceQualitySummary()
        pr_issue = {
            "id": 555, "node_id": "I_kwDOPR",
            "number": 7, "html_url": "https://github.com/example/repo/pull/7",
            "title": "A pull request", "body": "PR body",
            "pull_request": {"url": "https://api.github.com/repos/example/repo/pulls/7"},
        }
        evidence = github_issue_to_raw_evidence(
            pr_issue, scheduled_item=item, quality_summary=summary
        )
        self.assertIsNone(evidence)
        self.assertEqual(summary.pr_filtered_count, 1)
        self.assertIn("pull_request", summary.rejection_reasons)

    def test_issue_without_pr_key_is_retained(self) -> None:
        item = github_scheduled_item()
        issue = {
            "id": 999, "node_id": "I_kwDOTest",
            "number": 99, "html_url": "https://github.com/example/repo/issues/99",
            "title": "Normal issue", "body": "Some body",
        }
        evidence = github_issue_to_raw_evidence(issue, scheduled_item=item)
        self.assertIsNotNone(evidence)
        self.assertEqual(evidence.evidence_id, "raw_github_issue_I_kwDOTest")

    def test_pr_filtered_in_batch(self) -> None:
        item = github_scheduled_item()
        summary = GitHubSourceQualitySummary()
        payload = {
            "items": [
                {
                    "id": 555, "node_id": "I_kwDOPR",
                    "number": 7, "html_url": "https://github.com/example/repo/pull/7",
                    "title": "PR", "body": "PR",
                    "pull_request": {},
                },
                fixture_payload()["items"][0],
            ]
        }
        evidence = parse_github_issues(payload, scheduled_item=item, quality_summary=summary)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].evidence_id, "raw_github_issue_I_kwDOExample")
        self.assertEqual(summary.pr_filtered_count, 1)

    def test_all_prs_dropped_emits_zero(self) -> None:
        item = github_scheduled_item()
        summary = GitHubSourceQualitySummary()
        payload = {
            "items": [
                {
                    "id": 555, "node_id": "I_kwDOPR1",
                    "number": 7, "html_url": "https://github.com/example/repo/pull/7",
                    "title": "PR 1", "body": "PR", "pull_request": {},
                },
                {
                    "id": 556, "node_id": "I_kwDOPR2",
                    "number": 8, "html_url": "https://github.com/example/repo/pull/8",
                    "title": "PR 2", "body": "PR", "pull_request": {},
                },
            ]
        }
        evidence = parse_github_issues(payload, scheduled_item=item, quality_summary=summary)
        self.assertEqual(len(evidence), 0)
        self.assertEqual(summary.pr_filtered_count, 2)
        self.assertEqual(summary.records_emitted, 0)


class TestEvidenceKindClassification(unittest.TestCase):
    """Tests for deterministic evidence_kind classification."""

    def test_bug_label_yields_bug_report(self) -> None:
        issue = {
            "title": "Export fails",
            "body": "When I click export, it crashes.",
            "labels": [{"name": "bug"}],
        }
        self.assertEqual(_classify_evidence_kind(issue), "bug_report")

    def test_bug_label_with_pain_yields_pain_signal_candidate(self) -> None:
        issue = {
            "title": "Export is completely broken",
            "body": "This is a blocker. I can't proceed without fixing this.",
            "labels": [{"name": "bug"}],
        }
        self.assertEqual(_classify_evidence_kind(issue), "pain_signal_candidate")

    def test_enhancement_label_yields_feature_request(self) -> None:
        issue = {
            "title": "Add CSV export",
            "body": "Would be nice to export to CSV.",
            "labels": [{"name": "enhancement"}],
        }
        self.assertEqual(_classify_evidence_kind(issue), "feature_request")

    def test_workaround_yields_workaround(self) -> None:
        issue = {
            "title": "Need a workaround for reporting",
            "body": "We use a spreadsheet as a temporary solution.",
            "labels": [],
        }
        self.assertEqual(_classify_evidence_kind(issue), "workaround")

    def test_pain_keyword_yields_pain_signal_candidate(self) -> None:
        issue = {
            "title": "Cashflow reporting is a nightmare",
            "body": "It's impossible to get accurate reports.",
            "labels": [],
        }
        self.assertEqual(_classify_evidence_kind(issue), "pain_signal_candidate")

    def test_complaint_yields_complaint(self) -> None:
        issue = {
            "title": "This needs to be better",
            "body": "Why is this so frustrating? It should be easier.",
            "labels": [],
        }
        self.assertEqual(_classify_evidence_kind(issue), "complaint")

    def test_feature_request_yields_feature_request(self) -> None:
        issue = {
            "title": "Missing feature",
            "body": "I wish it had batch export. Please add this.",
            "labels": [],
        }
        self.assertEqual(_classify_evidence_kind(issue), "feature_request")

    def test_duplicate_label_yields_unknown(self) -> None:
        issue = {
            "title": "Duplicate of #42",
            "body": "Same as that one.",
            "labels": [{"name": "duplicate"}],
        }
        self.assertEqual(_classify_evidence_kind(issue), "unknown")

    def test_invalid_label_yields_unknown(self) -> None:
        issue = {
            "title": "Not an issue",
            "body": "Never mind.",
            "labels": [{"name": "invalid"}],
        }
        self.assertEqual(_classify_evidence_kind(issue), "unknown")

    def test_wontfix_label_yields_unknown(self) -> None:
        issue = {
            "title": "Won't fix",
            "body": "We decided not to do this.",
            "labels": [{"name": "wontfix"}],
        }
        self.assertEqual(_classify_evidence_kind(issue), "unknown")

    def test_default_yields_unknown(self) -> None:
        issue = {
            "title": "General question",
            "body": "Can someone help me with this?",
            "labels": [],
        }
        self.assertEqual(_classify_evidence_kind(issue), "unknown")

    def test_documentation_label_yields_unknown(self) -> None:
        issue = {
            "title": "Update docs for API",
            "body": "The docs are out of date.",
            "labels": [{"name": "documentation"}],
        }
        self.assertEqual(_classify_evidence_kind(issue), "unknown")

    def test_question_label_yields_unknown(self) -> None:
        issue = {
            "title": "How do I...",
            "body": "Question about usage.",
            "labels": [{"name": "question"}],
        }
        self.assertEqual(_classify_evidence_kind(issue), "unknown")

    def test_short_body_no_labels_yields_unknown(self) -> None:
        issue = {
            "title": "Help",
            "body": "quick",
            "labels": [],
        }
        self.assertEqual(_classify_evidence_kind(issue), "unknown")

    def test_fixture_issue_kind_is_set(self) -> None:
        item = github_scheduled_item()
        result = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)
        for ev in result.evidence:
            kind = ev.raw_metadata.get("evidence_kind")
            self.assertIsNotNone(kind)
            self.assertIn(kind, {
                "bug_report", "feature_request", "complaint",
                "workaround", "pain_signal_candidate", "unknown",
            })


class TestQualityFlags(unittest.TestCase):
    """Tests for deterministic noise/quality flags."""

    def test_bot_generated_detects_bot_type(self) -> None:
        issue = {
            "title": "Bump version", "body": "Auto-bump.",
            "labels": [], "user": {"login": "dependabot[bot]", "type": "Bot"},
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("bot_generated", flags)

    def test_bot_generated_detects_github_actions(self) -> None:
        issue = {
            "title": "Update CI", "body": "Changes.",
            "labels": [], "user": {"login": "github-actions[bot]"},
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("bot_generated", flags)

    def test_stale_issue_no_updated_at(self) -> None:
        issue = {
            "title": "Old issue", "body": "No updated_at.",
            "labels": [],
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("stale_issue", flags)

    def test_short_body_yields_low_text_context(self) -> None:
        issue = {
            "title": "Short", "body": "tiny",
            "labels": [],
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("low_text_context", flags)

    def test_duplicate_label_yields_duplicate_or_invalid(self) -> None:
        issue = {
            "title": "Duplicate", "body": "This is a duplicate of #1.",
            "labels": [{"name": "duplicate"}],
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("duplicate_or_invalid", flags)

    def test_invalid_label_yields_duplicate_or_invalid(self) -> None:
        issue = {
            "title": "Bad report", "body": "nonsense",
            "labels": [{"name": "invalid"}],
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("duplicate_or_invalid", flags)

    def test_wontfix_label_yields_wontfix_or_not_planned(self) -> None:
        issue = {
            "title": "Won't fix", "body": "Not doing this.",
            "labels": [{"name": "wontfix"}],
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("wontfix_or_not_planned", flags)

    def test_state_reason_not_planned_yields_wontfix(self) -> None:
        issue = {
            "title": "Closed as not planned", "body": "Closed.",
            "labels": [], "state_reason": "not_planned",
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("wontfix_or_not_planned", flags)

    def test_maintainer_housekeeping_chore_prefix(self) -> None:
        issue = {
            "title": "chore: update deps", "body": "Regular maintenance.",
            "labels": [],
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("maintainer_housekeeping", flags)

    def test_maintainer_housekeeping_ci_prefix(self) -> None:
        issue = {
            "title": "ci: fix pipeline", "body": "Pipeline fix.",
            "labels": [],
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("maintainer_housekeeping", flags)

    def test_maintainer_housekeeping_bump_version(self) -> None:
        issue = {
            "title": "bump version to 2.0", "body": "Version bump.",
            "labels": [],
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("maintainer_housekeeping", flags)

    def test_locked_issue_yields_source_access_limited(self) -> None:
        issue = {
            "title": "Locked thread", "body": "Content.",
            "labels": [], "locked": True,
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("source_access_limited", flags)

    def test_requires_manual_review_set_when_flags_present(self) -> None:
        issue = {
            "title": "Short", "body": "tiny",
            "labels": [],
        }
        flags = _compute_quality_flags(issue)
        self.assertIn("low_text_context", flags)
        self.assertIn("requires_manual_review", flags)

    def test_no_flags_for_clean_issue(self) -> None:
        from datetime import datetime, timezone, timedelta
        recent = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        issue = {
            "title": "Normal feature request",
            "body": "I would like to request a feature that helps with reporting. "
                     "The current workflow requires going through five different screens "
                     "and manually exporting each report individually.",
            "labels": [{"name": "enhancement"}],
            "updated_at": recent,
            "user": {"login": "normal_user"},
        }
        flags = _compute_quality_flags(issue)
        self.assertEqual(flags, [])

    def test_quality_flags_in_metadata(self) -> None:
        item = github_scheduled_item()
        result = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)
        for ev in result.evidence:
            qf = ev.raw_metadata.get("quality_flags")
            self.assertIsInstance(qf, list)


class TestAuthorContextLabels(unittest.TestCase):
    """Tests for privacy-safe author_or_context labels."""

    def test_default_reporter_label(self) -> None:
        label = _author_context_label({
            "title": "Issue", "user": {"login": "normal_user"},
        })
        self.assertEqual(label, "issue reporter")

    def test_bug_label_yields_bug_reporter(self) -> None:
        label = _author_context_label({
            "title": "Bug", "user": {"login": "user1"},
            "labels": [{"name": "bug"}],
        })
        self.assertEqual(label, "bug reporter")

    def test_enhancement_yields_feature_requester(self) -> None:
        label = _author_context_label({
            "title": "Feature", "user": {"login": "user2"},
            "labels": [{"name": "enhancement"}],
        })
        self.assertEqual(label, "feature requester")

    def test_bot_detected_as_automated_system(self) -> None:
        label = _author_context_label({
            "title": "Bump", "user": {"login": "dependabot[bot]", "type": "Bot"},
        })
        self.assertEqual(label, "automated system (bot)")

    def test_maintainer_detected_via_author_association(self) -> None:
        label = _author_context_label({
            "title": "Issue", "user": {"login": "owner"},
            "author_association": "OWNER",
        })
        self.assertEqual(label, "project maintainer")

    def test_author_or_context_does_not_store_raw_login(self) -> None:
        item = github_scheduled_item()
        evidence = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item).evidence[0]
        self.assertNotIn("raw_github_login", evidence.author_or_context)
        self.assertNotIn("raw_github_login", str(evidence.raw_metadata))
        self.assertNotIn("user", evidence.raw_metadata, "user object must not be stored")


class TestRepoFullNameDerivation(unittest.TestCase):
    """Tests for repo_full_name derivation."""

    def test_from_repository_url(self) -> None:
        issue = {"repository_url": "https://api.github.com/repos/owner/repo"}
        self.assertEqual(_derive_repo_full_name(issue), "owner/repo")

    def test_from_html_url(self) -> None:
        issue = {"html_url": "https://github.com/owner/repo/issues/1"}
        self.assertEqual(_derive_repo_full_name(issue), "owner/repo")

    def test_empty_when_no_urls(self) -> None:
        issue = {}
        self.assertEqual(_derive_repo_full_name(issue), "")


class TestGitHubIssuesCollector(unittest.TestCase):
    """Core collector integration tests."""

    def test_fixture_issue_converts_to_raw_evidence(self) -> None:
        item = github_scheduled_item()
        evidence = github_issue_to_raw_evidence(
            fixture_payload()["items"][0], scheduled_item=item
        )
        self.assertIsInstance(evidence, RawEvidence)
        self.assertEqual(evidence.evidence_id, "raw_github_issue_I_kwDOExample")
        self.assertEqual(evidence.source_name, "GitHub Issues")
        self.assertEqual(evidence.source_type, "issue_tracker")
        self.assertEqual(evidence.collection_method, "fixture")

    def test_source_topic_query_kind_are_preserved(self) -> None:
        item = github_scheduled_item()
        result = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)
        evidence = result.evidence[0]
        self.assertEqual(evidence.source_id, GH_CANONICAL_SOURCE_ID)
        self.assertEqual(evidence.topic_id, item.topic_id)
        self.assertEqual(evidence.query_kind, item.query_kind)

    def test_raw_metadata_preserves_safe_fields(self) -> None:
        item = github_scheduled_item()
        evidence = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item).evidence[0]
        meta = evidence.raw_metadata
        self.assertEqual(meta["issue_id"], 123456789)
        self.assertEqual(meta["node_id"], "I_kwDOExample")
        self.assertEqual(meta["number"], 42)
        self.assertEqual(meta["labels"], ["feature request", "reporting"])
        self.assertEqual(meta["state"], "open")
        self.assertEqual(meta["comments_count"], 5)
        self.assertEqual(meta["reactions"], {"total_count": 3, "+1": 2, "eyes": 1})
        self.assertFalse(meta["pull_request_present"])
        self.assertTrue(meta["user_present"])
        self.assertIn("repository_url", meta)
        self.assertIn("comments_url", meta)
        self.assertIn("repo_full_name", meta)
        self.assertIn("evidence_kind", meta)
        self.assertIn("quality_flags", meta)
        self.assertIn("engagement_metrics", meta)
        self.assertIn("categories", meta)
        self.assertIn("source_specific_id", meta)

    def test_content_hash_is_deterministic(self) -> None:
        item = github_scheduled_item()
        first = github_issue_to_raw_evidence(
            fixture_payload()["items"][0], scheduled_item=item
        )
        second = github_issue_to_raw_evidence(
            fixture_payload()["items"][0], scheduled_item=item
        )
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(
            first.content_hash,
            compute_raw_evidence_content_hash(title=first.title, body=first.body),
        )

    def test_collector_respects_max_results(self) -> None:
        item = github_scheduled_item(max_results=1)
        result = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)
        self.assertEqual(len(result.evidence), 1)

    def test_no_network_call_when_live_network_is_disabled(self) -> None:
        item = github_scheduled_item()
        collector = GitHubIssuesCollector()
        with patch.object(collector, "_fetch_live_payload", side_effect=AssertionError("network called")):
            result = collector.collect(item)
        self.assertEqual(result.evidence, [])
        self.assertFalse(result.live_network_used)

    def test_rejects_unsupported_source_type(self) -> None:
        item = replace(github_scheduled_item(), source_type="hacker_news_algolia")
        with self.assertRaisesRegex(ValueError, "does not support"):
            GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)

    def test_empty_fixture_returns_empty_safely(self) -> None:
        item = github_scheduled_item()
        result = GitHubIssuesCollector(fixture_payload={"items": []}).collect(item)
        self.assertEqual(result.evidence, [])

    def test_malformed_issues_do_not_crash(self) -> None:
        item = github_scheduled_item()
        payload = {
            "items": [
                {"title": "missing id"},
                "not a dict",
                {
                    "id": 987654321, "node_id": "I_kwDOTest",
                    "title": "", "body": "",
                    "html_url": "https://github.com/example/repo/issues/99",
                },
            ]
        }
        evidence = parse_github_issues(payload, scheduled_item=item)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].evidence_id, "raw_github_issue_I_kwDOTest")

    def test_no_secrets_or_api_keys_required(self) -> None:
        item = github_scheduled_item()
        evidence = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item).evidence
        self.assertTrue(evidence)
        self.assertTrue(all("api_key" not in item.raw_metadata for item in evidence))
        self.assertTrue(all("token" not in item.raw_metadata for item in evidence))

    def test_no_live_internet_api_or_llm_calls(self) -> None:
        item = github_scheduled_item()
        result = GitHubIssuesCollector(fixture_payload=fixture_payload()).collect(item)
        self.assertTrue(result.evidence)
        self.assertFalse(result.live_network_used)

    def test_live_fetch_decodes_utf8_without_mojibake(self) -> None:
        item = replace(github_scheduled_item(max_results=1), live_network_enabled=True)
        payload = {
            "items": [
                {
                    "id": 999, "node_id": "I_kwDOTest",
                    "number": 9,
                    "html_url": "https://github.com/example/repo/issues/9",
                    "title": "Cash flow planning 🚀",
                    "body": "Invoice tracker — manual checklist 📋 for bills.",
                    "state": "open",
                }
            ]
        }

        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def read(self):
                return json.dumps(payload, ensure_ascii=False).encode("utf-8")

        collector = GitHubIssuesCollector(allow_live_network=True)
        with patch("oos.github_issues_collector.urlopen", return_value=Response()):
            result = collector.collect(item)

        text = f"{result.evidence[0].title} {result.evidence[0].body}"
        self.assertIn("🚀", text)
        self.assertIn("—", text)
        self.assertIn("📋", text)
        self.assertNotIn("рџ", text.lower())

    def test_registry_planner_scheduler_flow(self) -> None:
        plans = QueryPlanner().build_plans(
            registry=default_source_registry(),
            topic_profiles=default_topic_profiles(),
        )
        queue = CollectionScheduler(
            limits=CollectionLimits(max_total_queries=2, allowed_source_ids={"github_issues"})
        ).build_queue(plans)
        collector = GitHubIssuesCollector(fixture_payload=fixture_payload())
        evidence = []
        for item in queue:
            evidence.extend(collector.collect(item).evidence)
        self.assertTrue(evidence)
        self.assertTrue(all(item.source_id == "github_issues" for item in evidence))
        self.assertTrue(all(item.source_type == "issue_tracker" for item in evidence))
        self.assertTrue(
            all(item.source_url.startswith("https://github.com/") for item in evidence)
        )


class TestRepoAllowlist(unittest.TestCase):
    """Tests for repo allowlist filtering."""

    def test_null_allowlist_allows_all(self) -> None:
        item = github_scheduled_item()
        issue = fixture_payload()["items"][0]
        evidence = github_issue_to_raw_evidence(issue, scheduled_item=item, repo_allowlist=None)
        self.assertIsNotNone(evidence)

    def test_matching_repo_is_allowed(self) -> None:
        item = github_scheduled_item()
        issue = fixture_payload()["items"][0]
        evidence = github_issue_to_raw_evidence(
            issue, scheduled_item=item,
            repo_allowlist=["example/finance-tool"],
        )
        self.assertIsNotNone(evidence)

    def test_non_matching_repo_is_rejected(self) -> None:
        item = github_scheduled_item()
        summary = GitHubSourceQualitySummary()
        issue = fixture_payload()["items"][0]
        evidence = github_issue_to_raw_evidence(
            issue, scheduled_item=item,
            repo_allowlist=["other/repo", "another/repo"],
            quality_summary=summary,
        )
        self.assertIsNone(evidence)
        self.assertEqual(summary.records_rejected, 1)
        self.assertIn("not_in_allowlist", summary.rejection_reasons)

    def test_case_insensitive_matching(self) -> None:
        item = github_scheduled_item()
        issue = fixture_payload()["items"][0]
        evidence = github_issue_to_raw_evidence(
            issue, scheduled_item=item,
            repo_allowlist=["EXAMPLE/FINANCE-TOOL"],
        )
        self.assertIsNotNone(evidence)

    def test_collector_passes_allowlist(self) -> None:
        item = github_scheduled_item()
        collector = GitHubIssuesCollector(
            fixture_payload=fixture_payload(),
            repo_allowlist=["example/finance-tool"],
        )
        result = collector.collect(item)
        self.assertTrue(len(result.evidence) > 0)

    def test_empty_allowlist_blocks_all(self) -> None:
        item = github_scheduled_item()
        collector = GitHubIssuesCollector(
            fixture_payload=fixture_payload(),
            repo_allowlist=[],
        )
        result = collector.collect(item)
        self.assertEqual(len(result.evidence), 0)


class TestSourceQualitySummaryIntegration(unittest.TestCase):
    """Tests for source quality summary production."""

    def test_summary_counts_records(self) -> None:
        item = github_scheduled_item()
        summary = GitHubSourceQualitySummary()
        payload = fixture_payload()
        evidence = parse_github_issues(payload, scheduled_item=item, quality_summary=summary)
        self.assertEqual(summary.records_seen, 2)
        self.assertEqual(summary.records_emitted, len(evidence))
        self.assertEqual(summary.records_emitted, 2)

    def test_summary_tracks_pr_filtered(self) -> None:
        item = github_scheduled_item()
        summary = GitHubSourceQualitySummary()
        payload = {
            "items": [
                {
                    "id": 555, "node_id": "I_kwDOPR",
                    "number": 7, "html_url": "https://github.com/example/repo/pull/7",
                    "title": "PR", "body": "PR", "pull_request": {},
                },
                fixture_payload()["items"][0],
            ]
        }
        parse_github_issues(payload, scheduled_item=item, quality_summary=summary)
        self.assertEqual(summary.pr_filtered_count, 1)

    def test_summary_tracks_missing_url(self) -> None:
        item = github_scheduled_item()
        summary = GitHubSourceQualitySummary()
        payload = {
            "items": [
                {"id": 999, "node_id": "I_kwDOTest", "title": "No URL", "body": "Body"},
            ]
        }
        parse_github_issues(payload, scheduled_item=item, quality_summary=summary)
        self.assertEqual(summary.missing_url_count, 1)

    def test_summary_tracks_duplicates(self) -> None:
        item = github_scheduled_item()
        summary = GitHubSourceQualitySummary()
        issue = fixture_payload()["items"][0]
        payload = {"items": [issue, issue]}
        evidence = parse_github_issues(payload, scheduled_item=item, quality_summary=summary)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(summary.duplicate_count, 1)

    def test_build_summary_from_payload(self) -> None:
        item = github_scheduled_item()
        payload = fixture_payload()
        evidence = parse_github_issues(payload, scheduled_item=item)
        summary = build_github_source_quality_summary(payload, evidence)
        summary.validate()
        self.assertEqual(summary.source_id, "github_issues")
        self.assertEqual(summary.source_type, "issue_tracker")
        self.assertEqual(summary.records_seen, 2)
        self.assertEqual(summary.records_emitted, 2)

    def test_summary_tracks_rejection_reasons(self) -> None:
        item = github_scheduled_item()
        summary = GitHubSourceQualitySummary()
        payload = {
            "items": [
                {
                    "id": 555, "node_id": "I_kwDOPR",
                    "number": 7, "html_url": "https://github.com/example/repo/pull/7",
                    "title": "PR", "body": "PR", "pull_request": {},
                },
                {"id": 999, "title": "No URL", "body": "Body"},
            ]
        }
        parse_github_issues(payload, scheduled_item=item, quality_summary=summary)
        self.assertIn("pull_request", summary.rejection_reasons)
        self.assertIn("missing_source_url", summary.rejection_reasons)
        # The {"id": 999} issue has id=999 so passes node_id check,
        # but hits missing_source_url (no html_url). Non-dict "not a dict"
        # items are also skipped without being counted in this path.

    def test_quality_flag_counts_populated(self) -> None:
        item = github_scheduled_item()
        payload = {
            "items": [
                {
                    "id": 777, "node_id": "I_kwDOBot",
                    "number": 77,
                    "html_url": "https://github.com/example/repo/issues/77",
                    "title": "Bump deps",
                    "body": "short",
                    "labels": [{"name": "duplicate"}],
                    "user": {"login": "dependabot[bot]", "type": "Bot"},
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ]
        }
        summary = GitHubSourceQualitySummary()
        parse_github_issues(payload, scheduled_item=item, quality_summary=summary)
        self.assertIn("bot_generated", summary.quality_flag_counts)
        self.assertIn("duplicate_or_invalid", summary.quality_flag_counts)
        self.assertIn("low_text_context", summary.quality_flag_counts)

    def test_quality_summary_source_type_is_issue_tracker(self) -> None:
        summary = GitHubSourceQualitySummary()
        self.assertEqual(summary.source_type, "issue_tracker")


if __name__ == "__main__":
    unittest.main()
