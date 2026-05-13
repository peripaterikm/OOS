from __future__ import annotations

import unittest

from oos.pain_cluster_dedupe import (
    CANONICAL_SOURCE_IDS,
    CANONICAL_SOURCE_TYPES,
    SOURCE_ID_NORMALIZATION,
    SOURCE_TYPE_NORMALIZATION,
    compute_source_diversity,
    dedupe_by_canonical_url,
    dedupe_by_evidence_id,
    dedupe_by_source_url,
    dedupe_full,
    is_canonical_source_id,
    is_canonical_source_type,
    normalize_evidence_source,
    normalize_source_id,
    normalize_source_type,
    should_preserve_as_separate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ev(
    evidence_id: str = "ev_001",
    source_id: str = "hacker_news",
    source_type: str = "discussion",
    source_url: str = "https://news.ycombinator.com/item?id=123",
    title: str = "Test title",
    body: str = "Test body",
    canonical_url: str | None = None,
) -> dict:
    d: dict = {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "source_type": source_type,
        "source_url": source_url,
        "title": title,
        "body": body,
    }
    if canonical_url:
        d["canonical_url"] = canonical_url
    return d


# ---------------------------------------------------------------------------
# Source normalization tests
# ---------------------------------------------------------------------------


class TestSourceNormalization(unittest.TestCase):
    def test_normalize_source_id_legacy_hacker_news(self) -> None:
        self.assertEqual(normalize_source_id("hacker_news_algolia"), "hacker_news")

    def test_normalize_source_id_canonical_unchanged(self) -> None:
        self.assertEqual(normalize_source_id("hacker_news"), "hacker_news")
        self.assertEqual(normalize_source_id("github_issues"), "github_issues")

    def test_normalize_source_id_unknown_passthrough(self) -> None:
        self.assertEqual(normalize_source_id("stack_exchange"), "stack_exchange")

    def test_normalize_source_type_legacy_github_issues(self) -> None:
        self.assertEqual(normalize_source_type("github_issues"), "issue_tracker")

    def test_normalize_source_type_legacy_hacker_news_algolia(self) -> None:
        self.assertEqual(normalize_source_type("hacker_news_algolia"), "discussion")

    def test_normalize_source_type_canonical_unchanged(self) -> None:
        self.assertEqual(normalize_source_type("discussion"), "discussion")
        self.assertEqual(normalize_source_type("issue_tracker"), "issue_tracker")

    def test_normalize_source_type_hacker_news_source_id(self) -> None:
        self.assertEqual(normalize_source_type("hacker_news"), "discussion")

    def test_normalize_source_type_unknown_passthrough(self) -> None:
        self.assertEqual(normalize_source_type("qa"), "qa")

    def test_is_canonical_source_id(self) -> None:
        self.assertTrue(is_canonical_source_id("hacker_news"))
        self.assertTrue(is_canonical_source_id("github_issues"))
        self.assertFalse(is_canonical_source_id("hacker_news_algolia"))
        self.assertFalse(is_canonical_source_id("stack_exchange"))

    def test_is_canonical_source_type(self) -> None:
        self.assertTrue(is_canonical_source_type("discussion"))
        self.assertTrue(is_canonical_source_type("issue_tracker"))
        self.assertFalse(is_canonical_source_type("github_issues"))
        self.assertFalse(is_canonical_source_type("hacker_news_algolia"))

    def test_normalize_evidence_source_returns_new_dict(self) -> None:
        ev = _make_ev(source_id="hacker_news_algolia", source_type="github_issues")
        result = normalize_evidence_source(ev)
        self.assertEqual(result["source_id"], "hacker_news")
        self.assertEqual(result["source_type"], "issue_tracker")
        # Original unchanged
        self.assertEqual(ev["source_id"], "hacker_news_algolia")

    def test_normalize_evidence_source_canonical_unchanged(self) -> None:
        ev = _make_ev(source_id="hacker_news", source_type="discussion")
        result = normalize_evidence_source(ev)
        self.assertEqual(result["source_id"], "hacker_news")
        self.assertEqual(result["source_type"], "discussion")


# ---------------------------------------------------------------------------
# Dedupe by evidence_id tests
# ---------------------------------------------------------------------------


class TestDedupeByEvidenceId(unittest.TestCase):
    def test_no_duplicates(self) -> None:
        evs = [
            _make_ev(evidence_id="ev_001"),
            _make_ev(evidence_id="ev_002", source_url="https://example.com/2"),
        ]
        unique, dups = dedupe_by_evidence_id(evs)
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(dups), 0)

    def test_exact_evidence_id_duplicate(self) -> None:
        evs = [
            _make_ev(evidence_id="ev_001"),
            _make_ev(evidence_id="ev_001", source_url="https://example.com/dup"),
        ]
        unique, dups = dedupe_by_evidence_id(evs)
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0]["duplicate_of"], "ev_001")
        self.assertEqual(dups[0]["source_url"], "https://example.com/dup")

    def test_multiple_duplicates_traceable(self) -> None:
        evs = [
            _make_ev(evidence_id="ev_001"),
            _make_ev(evidence_id="ev_001", source_url="https://example.com/d1"),
            _make_ev(evidence_id="ev_001", source_url="https://example.com/d2"),
            _make_ev(evidence_id="ev_002", source_url="https://example.com/u2"),
        ]
        unique, dups = dedupe_by_evidence_id(evs)
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(dups), 2)
        for d in dups:
            self.assertEqual(d["duplicate_of"], "ev_001")

    def test_empty_evidence_id_treated_as_unique(self) -> None:
        evs = [
            _make_ev(evidence_id=""),
            _make_ev(evidence_id=""),
        ]
        unique, dups = dedupe_by_evidence_id(evs)
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(dups), 0)


# ---------------------------------------------------------------------------
# Dedupe by canonical_url tests
# ---------------------------------------------------------------------------


class TestDedupeByCanonicalUrl(unittest.TestCase):
    def test_same_canonical_url_dedupe(self) -> None:
        evs = [
            _make_ev(evidence_id="ev_001", canonical_url="https://example.com/item"),
            _make_ev(evidence_id="ev_002", canonical_url="https://example.com/item"),
        ]
        unique, dups = dedupe_by_canonical_url(evs)
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0]["duplicate_of"], "ev_001")

    def test_different_canonical_url_kept(self) -> None:
        evs = [
            _make_ev(evidence_id="ev_001", canonical_url="https://a.com/1"),
            _make_ev(evidence_id="ev_002", canonical_url="https://b.com/2"),
        ]
        unique, dups = dedupe_by_canonical_url(evs)
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(dups), 0)

    def test_no_canonical_url_always_unique(self) -> None:
        evs = [
            _make_ev(evidence_id="ev_001"),
            _make_ev(evidence_id="ev_002"),
        ]
        unique, dups = dedupe_by_canonical_url(evs)
        self.assertEqual(len(unique), 2)


# ---------------------------------------------------------------------------
# Dedupe by source_url tests
# ---------------------------------------------------------------------------


class TestDedupeBySourceUrl(unittest.TestCase):
    def test_same_source_url_dedupe(self) -> None:
        evs = [
            _make_ev(evidence_id="ev_001", source_url="https://example.com/item"),
            _make_ev(evidence_id="ev_002", source_url="https://example.com/item"),
        ]
        unique, dups = dedupe_by_source_url(evs)
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0]["duplicate_of"], "ev_001")

    def test_different_source_url_kept(self) -> None:
        evs = [
            _make_ev(evidence_id="ev_001", source_url="https://a.com/1"),
            _make_ev(evidence_id="ev_002", source_url="https://b.com/2"),
        ]
        unique, dups = dedupe_by_source_url(evs)
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(dups), 0)

    def test_empty_source_url_not_deduped(self) -> None:
        evs = [
            _make_ev(evidence_id="ev_001", source_url=""),
            _make_ev(evidence_id="ev_002", source_url=""),
        ]
        unique, dups = dedupe_by_source_url(evs)
        self.assertEqual(len(unique), 2)


# ---------------------------------------------------------------------------
# Full dedupe tests
# ---------------------------------------------------------------------------


class TestDedupeFull(unittest.TestCase):
    def test_no_duplicates(self) -> None:
        evs = [
            _make_ev(evidence_id="ev_001", source_url="https://a.com/1"),
            _make_ev(evidence_id="ev_002", source_url="https://b.com/2"),
            _make_ev(evidence_id="ev_003", source_url="https://c.com/3"),
        ]
        unique, dups = dedupe_full(evs)
        self.assertEqual(len(unique), 3)
        self.assertEqual(len(dups), 0)

    def test_multi_pass_dedupe(self) -> None:
        evs = [
            _make_ev(evidence_id="ev_001", source_url="https://a.com/1"),
            _make_ev(evidence_id="ev_001", source_url="https://a.com/1"),  # evidence_id dup
            _make_ev(evidence_id="ev_002", source_url="https://a.com/1"),  # source_url dup after first pass
            _make_ev(evidence_id="ev_003", source_url="https://b.com/2"),
        ]
        unique, dups = dedupe_full(evs)
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(dups), 2)

    def test_provenance_preserved(self) -> None:
        evs = [
            _make_ev(evidence_id="ev_001", source_url="https://a.com/orig"),
            _make_ev(evidence_id="ev_001", source_url="https://a.com/dup"),
        ]
        unique, dups = dedupe_full(evs)
        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0]["evidence_id"], "ev_001")
        self.assertEqual(unique[0]["source_url"], "https://a.com/orig")
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0]["duplicate_of"], "ev_001")
        self.assertIn("source_url", dups[0])


# ---------------------------------------------------------------------------
# Cross-source preservation tests
# ---------------------------------------------------------------------------


class TestCrossSourcePreservation(unittest.TestCase):
    def test_cross_source_not_silently_dropped(self) -> None:
        """Even if they share a URL, different sources should be preserved."""
        # This is tested at the assembly layer, but the helper should return True
        ev1 = _make_ev(source_id="hacker_news", source_type="discussion")
        ev2 = _make_ev(source_id="github_issues", source_type="issue_tracker")
        self.assertTrue(should_preserve_as_separate(ev1, ev2))

    def test_same_source_can_be_merged(self) -> None:
        ev1 = _make_ev(source_id="hacker_news", source_type="discussion")
        ev2 = _make_ev(source_id="hacker_news", source_type="discussion", evidence_id="ev_002")
        self.assertFalse(should_preserve_as_separate(ev1, ev2))

    def test_legacy_source_ids_normalized_before_comparison(self) -> None:
        ev1 = _make_ev(source_id="hacker_news_algolia", source_type="discussion")
        ev2 = _make_ev(source_id="github_issues", source_type="issue_tracker")
        self.assertTrue(should_preserve_as_separate(ev1, ev2))

    def test_both_legacy_diff_sources_preserved(self) -> None:
        ev1 = _make_ev(source_id="hacker_news_algolia", source_type="hacker_news_algolia")
        ev2 = _make_ev(source_id="github_issues", source_type="github_issues")
        self.assertTrue(should_preserve_as_separate(ev1, ev2))


# ---------------------------------------------------------------------------
# Source diversity tests
# ---------------------------------------------------------------------------


class TestSourceDiversity(unittest.TestCase):
    def test_empty_returns_zero(self) -> None:
        self.assertEqual(compute_source_diversity([]), 0)

    def test_single_source(self) -> None:
        evs = [
            _make_ev(source_id="hacker_news", source_type="discussion"),
            _make_ev(source_id="hacker_news", source_type="discussion", evidence_id="ev_002"),
        ]
        self.assertEqual(compute_source_diversity(evs), 1)

    def test_two_canonical_sources(self) -> None:
        evs = [
            _make_ev(source_id="hacker_news", source_type="discussion"),
            _make_ev(source_id="github_issues", source_type="issue_tracker", evidence_id="ev_002"),
        ]
        self.assertEqual(compute_source_diversity(evs), 2)

    def test_legacy_source_ids_normalized(self) -> None:
        evs = [
            _make_ev(source_id="hacker_news_algolia", source_type="hacker_news_algolia"),
            _make_ev(source_id="github_issues", source_type="github_issues", evidence_id="ev_002"),
        ]
        self.assertEqual(compute_source_diversity(evs), 2)

    def test_legacy_and_canonical_same_source_count_as_one(self) -> None:
        evs = [
            _make_ev(source_id="hacker_news_algolia"),  # normalizes to hacker_news
            _make_ev(source_id="hacker_news", evidence_id="ev_002"),  # already hacker_news
        ]
        self.assertEqual(compute_source_diversity(evs), 1)


if __name__ == "__main__":
    unittest.main()
