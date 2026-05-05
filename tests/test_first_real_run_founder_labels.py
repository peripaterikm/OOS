import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LABEL_DIR = PROJECT_ROOT / "examples" / "first_real_open_source_signal_run_v1"
LABEL_JSON = LABEL_DIR / "founder_manual_labels.json"
LABEL_MD = LABEL_DIR / "founder_manual_labels.md"

ALLOWED_FOUNDER_LABELS = {
    "useful",
    "weak",
    "noise",
    "duplicate",
    "vendor_promo",
    "price_false_positive",
    "needs_more_evidence",
}

ALLOWED_RECOMMENDED_ACTIONS = {
    "promote_to_opportunity_seed",
    "keep_as_context",
    "park_for_more_evidence",
    "suppress_in_future",
    "mark_duplicate",
    "use_for_price_hardening",
    "use_for_mojibake_regression",
}

REQUIRED_EVIDENCE_IDS = {
    "raw_github_issue_3565323722",
    "raw_github_issue_1182773055",
    "raw_github_issue_4369704245",
    "raw_github_issue_385700413",
    "raw_github_issue_4072093883",
    "raw_github_issue_194268452",
    "raw_github_issue_4058309053",
    "raw_github_issue_4103786450",
    "raw_hn_47844178",
    "raw_hn_47401563",
    "raw_hn_47082761",
    "raw_hn_46725518",
    "raw_hn_44581530",
    "raw_hn_47009152",
    "raw_hn_46864767",
    "raw_hn_46430957",
}


class TestFirstRealRunFounderLabels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(LABEL_JSON.read_text(encoding="utf-8"))
        cls.reviews = cls.payload["reviews"]

    def test_label_artifacts_exist(self):
        self.assertTrue(LABEL_JSON.exists())
        self.assertTrue(LABEL_MD.exists())

    def test_all_18_review_entries_exist_with_unique_ids(self):
        self.assertEqual(18, len(self.reviews))
        review_ids = [review["review_id"] for review in self.reviews]
        self.assertEqual(len(review_ids), len(set(review_ids)))

    def test_only_allowed_labels_and_actions_are_used(self):
        for review in self.reviews:
            self.assertIn(review["founder_label"], ALLOWED_FOUNDER_LABELS)
            self.assertIn(review["recommended_action"], ALLOWED_RECOMMENDED_ACTIONS)

    def test_required_evidence_ids_are_present(self):
        evidence_ids = {review["evidence_id"] for review in self.reviews}
        self.assertTrue(REQUIRED_EVIDENCE_IDS.issubset(evidence_ids))

    def test_useful_labels_include_known_real_pains(self):
        useful_ids = {
            review["evidence_id"]
            for review in self.reviews
            if review["founder_label"] == "useful"
        }
        self.assertIn("raw_hn_47082761", useful_ids)
        self.assertIn("raw_github_issue_1182773055", useful_ids)
        self.assertIn("raw_hn_47009152", useful_ids)

    def test_vendor_promo_labels_include_known_source_quality_failures(self):
        vendor_ids = {
            review["evidence_id"]
            for review in self.reviews
            if review["founder_label"] == "vendor_promo"
        }
        self.assertIn("raw_github_issue_3565323722", vendor_ids)
        self.assertIn("raw_github_issue_4369704245", vendor_ids)
        self.assertIn("raw_github_issue_385700413", vendor_ids)
        self.assertIn("raw_github_issue_4103786450", vendor_ids)

    def test_price_false_positive_labels_include_known_price_failures(self):
        price_false_positive_ids = {
            review["evidence_id"]
            for review in self.reviews
            if review["founder_label"] == "price_false_positive"
        }
        self.assertIn("raw_github_issue_194268452", price_false_positive_ids)
        self.assertIn("raw_hn_46725518", price_false_positive_ids)

    def test_duplicate_labels_include_duplicate_occurrences(self):
        duplicate_reviews = [
            review for review in self.reviews if review["founder_label"] == "duplicate"
        ]
        self.assertEqual(
            ["raw_hn_47844178", "raw_hn_47401563"],
            [review["evidence_id"] for review in duplicate_reviews],
        )
        self.assertEqual(
            ["dup_raw_hn_47844178", "dup_raw_hn_47401563"],
            [review["duplicate_group_id"] for review in duplicate_reviews],
        )

    def test_issue_tags_include_mojibake_and_source_quality_examples(self):
        all_tags = {
            tag for review in self.reviews for tag in review.get("issue_tags", [])
        }
        self.assertIn("mojibake", all_tags)
        self.assertIn("source_quality_issue", all_tags)

    def test_no_live_network_or_llm_calls_are_needed(self):
        self.assertEqual(
            "artifacts/discovery_runs/first_real_open_source_signal_run_v1/candidate_signals.json",
            self.payload["source_candidate_artifact"],
        )
        self.assertEqual(
            "initial_founder_ground_truth_for_v2_5_block_1",
            self.payload["reviewer_context"],
        )


if __name__ == "__main__":
    unittest.main()
