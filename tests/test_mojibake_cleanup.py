import json
import shutil
import unittest
from pathlib import Path

from oos.candidate_signal_extractor import extract_candidate_signal
from oos.discovery_weekly import run_discovery_weekly
from oos.evidence_classifier import classify_evidence, clean_evidence, normalize_signal_text, repair_mojibake
from oos.models import RawEvidence, compute_raw_evidence_content_hash


TMP_ROOT = Path("codex_tmp_mojibake_cleanup")


def raw_evidence(
    body: str,
    *,
    evidence_id: str = "raw_mojibake",
    title: str = "Finance reporting",
    source_url: str = "https://github.com/example/repo/issues/194268452",
) -> RawEvidence:
    return RawEvidence(
        evidence_id=evidence_id,
        source_id="github_issues",
        source_type="github_issues",
        source_name="GitHub Issues",
        source_url=source_url,
        collected_at="2026-05-06T00:00:00+00:00",
        title=title,
        body=body,
        language="en",
        topic_id="ai_cfo_smb",
        query_kind="pain_query",
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context="public_issue_context",
        raw_metadata={"fixture": True},
        access_policy="fixture",
        collection_method="fixture",
    )


class TestMojibakeCleanup(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def test_today_apostrophe_mojibake_is_cleaned(self) -> None:
        cleaned = clean_evidence(raw_evidence("In todayвЂ™s accounting flow, invoice reporting is hard."))

        self.assertIn("today's", cleaned.normalized_body)
        self.assertNotIn("вЂ", cleaned.normalized_body)
        self.assertIn("mojibake_repaired", cleaned.cleaning_notes)

    def test_bullet_mojibake_is_cleaned(self) -> None:
        cleaned = clean_evidence(raw_evidence("вЂў Small Businesses use manual spreadsheets for bookkeeping."))

        self.assertIn("- Small Businesses", cleaned.normalized_body)
        self.assertNotIn("вЂ", cleaned.normalized_body)

    def test_cleaned_candidate_signal_summary_contains_no_mojibake(self) -> None:
        evidence = raw_evidence(
            "In todayвЂ™s accounting flow, invoice reporting is hard. вЂў Small Businesses use manual spreadsheets.",
            evidence_id="raw_hn_mojibake_candidate",
            source_url="https://news.ycombinator.com/item?id=47009152",
        )
        cleaned = clean_evidence(evidence)
        classification = classify_evidence(cleaned)
        signal = extract_candidate_signal(cleaned, classification)

        self.assertIsNotNone(signal)
        self.assertNotIn("вЂ", signal.pain_summary)
        self.assertNotIn("вЂ", signal.current_workaround)
        self.assertEqual(signal.evidence_id, "raw_hn_mojibake_candidate")
        self.assertEqual(signal.source_url, "https://news.ycombinator.com/item?id=47009152")

    def test_founder_package_contains_no_mojibake_and_preserves_traceability(self) -> None:
        project_root = TMP_ROOT / "project"
        project_root.mkdir(parents=True)
        source_url = "https://github.com/example/repo/issues/mojibake"
        evidence_path = project_root / "raw_evidence.json"
        evidence_path.write_text(
            json.dumps(
                {
                    "raw_evidence": [
                        raw_evidence(
                            "In todayвЂ™s accounting flow, invoice reporting is hard. вЂў Small Businesses use manual spreadsheets.",
                            evidence_id="raw_github_issue_mojibake",
                            source_url=source_url,
                        ).__dict__
                    ]
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        result = run_discovery_weekly(
            project_root=project_root,
            topic_id="ai_cfo_smb",
            run_id="mojibake_cleanup",
            input_raw_evidence=evidence_path.resolve(),
        )
        package_md = result.artifact_paths["founder_discovery_package_md"].read_text(encoding="utf-8")
        package_json = json.loads(result.artifact_paths["founder_discovery_package_json"].read_text(encoding="utf-8"))

        self.assertNotIn("вЂ", package_md)
        self.assertEqual(package_json["top_candidate_signals"][0]["evidence_id"], "raw_github_issue_mojibake")
        self.assertEqual(package_json["top_candidate_signals"][0]["source_url"], source_url)

    def test_cleanup_is_deterministic_and_idempotent(self) -> None:
        text = "In todayвЂ™s accounting flow вЂў invoices are hard"

        first = repair_mojibake(text)
        second = repair_mojibake(first)

        self.assertEqual(first, second)
        self.assertEqual(normalize_signal_text(text), normalize_signal_text(first))

    def test_valid_unicode_text_is_not_damaged(self) -> None:
        text = "Owner says “cash flow” isn’t optional — invoices matter • keep notes."

        self.assertEqual(repair_mojibake(text), text)
        self.assertIn("“cash flow”", normalize_signal_text(text))
        self.assertIn("—", normalize_signal_text(text))
        self.assertIn("•", normalize_signal_text(text))

    def test_non_breaking_space_mojibake_is_normalized(self) -> None:
        cleaned = clean_evidence(raw_evidence("Accounting В records use non-breaking spaces."))

        self.assertEqual(cleaned.normalized_body, "Accounting records use non-breaking spaces.")

    def test_no_live_network_or_llm_calls_are_made(self) -> None:
        source = Path("src/oos/evidence_classifier.py").read_text(encoding="utf-8")

        self.assertNotIn("requests.", source)
        self.assertNotIn("provider.complete", source)


if __name__ == "__main__":
    unittest.main()
