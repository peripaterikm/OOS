import json
import shutil
import unittest
from pathlib import Path

from oos.artifact_store import ArtifactStore
from oos.discovery_weekly import run_discovery_weekly
from oos.evidence_classifier import clean_evidence
from oos.models import PriceSignal, RawEvidence, compute_raw_evidence_content_hash
from oos.price_signal_extractor import (
    PriceSignalExtractionInput,
    build_price_signal_extraction_messages,
    extract_price_signal,
    price_signal_scoring_boost,
)
from oos.signal_scoring import SignalScoringInput, build_signal_score_breakdown


def raw_evidence(
    body: str,
    *,
    evidence_id: str = "raw_price_1",
    title: str = "Finance cost issue",
    query_kind: str = "pain_query",
) -> RawEvidence:
    return RawEvidence(
        evidence_id=evidence_id,
        source_id="github_issues",
        source_type="github_issues",
        source_name="github_issues",
        source_url=f"https://example.com/{evidence_id}",
        collected_at="2026-05-03T00:00:00+00:00",
        title=title,
        body=body,
        language="en",
        topic_id="ai_cfo_smb",
        query_kind=query_kind,
        content_hash=compute_raw_evidence_content_hash(title=title, body=body),
        author_or_context="developer",
        raw_metadata={"fixture": True},
        access_policy="fixture",
        collection_method="fixture",
    )


class TestPriceSignalExtractor(unittest.TestCase):
    def test_explicit_dollar_month_extraction(self) -> None:
        signal = extract_price_signal(clean_evidence(raw_evidence("We are paying $1,200 per month for invoice cleanup.")))

        self.assertIsNotNone(signal)
        self.assertEqual(signal.current_spend_hint, "$1,200 per month")
        self.assertIn("$1,200 per month", signal.evidence_cited)
        self.assertGreaterEqual(signal.confidence, 0.35)

    def test_explicit_hour_month_effort_extraction(self) -> None:
        signal = extract_price_signal(clean_evidence(raw_evidence("Month-end close takes 20 hours/month in spreadsheets.")))

        self.assertIsNotNone(signal)
        self.assertEqual(signal.effort_cost_hint, "20 hours/month")
        self.assertIn("20 hours/month", signal.evidence_cited)

    def test_price_complaint_extraction(self) -> None:
        signal = extract_price_signal(clean_evidence(raw_evidence("The accounting tool is too expensive for this workflow.")))

        self.assertIsNotNone(signal)
        self.assertEqual(signal.price_complaint, "too expensive")
        self.assertIn("too expensive", signal.evidence_cited.lower())

    def test_willingness_to_pay_extraction(self) -> None:
        signal = extract_price_signal(clean_evidence(raw_evidence("We would pay for a tool that reconciles invoices.")))

        self.assertIsNotNone(signal)
        self.assertEqual(signal.willingness_to_pay_indicator, "present")
        self.assertIn("would pay", signal.evidence_cited.lower())

    def test_no_extraction_for_vague_unsupported_text(self) -> None:
        signal = extract_price_signal(clean_evidence(raw_evidence("Cash flow reporting is frustrating and confusing.")))

        self.assertIsNone(signal)

    def test_no_invented_budget_from_budget_word_alone(self) -> None:
        signal = extract_price_signal(clean_evidence(raw_evidence("We need better budget visibility for the team.")))

        self.assertIsNone(signal)

    def test_artifact_roundtrip_for_price_signal_model(self) -> None:
        signal = extract_price_signal(clean_evidence(raw_evidence("USD 500/mo for exports is overpriced.")))
        self.assertIsNotNone(signal)

        tmp = Path("codex_tmp_price_signal_roundtrip")
        if tmp.exists():
            shutil.rmtree(tmp)
        try:
            store = ArtifactStore(root_dir=tmp / "artifacts")
            ref = store.write_model(signal)
            loaded = store.read_model(PriceSignal, signal.price_signal_id)
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)

        self.assertEqual(ref.kind, "price_signals")
        self.assertEqual(loaded, signal)

    def test_llm_prompt_contract_is_future_only_and_evidence_bound(self) -> None:
        messages = build_price_signal_extraction_messages(
            PriceSignalExtractionInput(
                evidence_id="ev_1",
                source_type="github_issues",
                source_url="https://example.com/ev_1",
                title="Pricing",
                body="Tool costs $99/month and is too expensive.",
            )
        )
        prompt_text = "\n".join(message.content for message in messages)

        self.assertIn("price_signal_extraction.v1", prompt_text)
        self.assertIn("do not invent budgets", prompt_text.lower())
        self.assertIn("Cite the exact evidence text", prompt_text)
        self.assertIn("$99/month", prompt_text)

    def test_scoring_boost_applies_only_with_explicit_evidence(self) -> None:
        baseline = build_signal_score_breakdown(
            SignalScoringInput(
                topic_id="ai_cfo_smb",
                source_type="github_issues",
                query_kind="pain_query",
                classification_label="pain_signal_candidate",
                signal_type="pain_signal",
                body="Cash flow reporting is hard.",
                classification_confidence=0.8,
            )
        )
        boosted = build_signal_score_breakdown(
            SignalScoringInput(
                topic_id="ai_cfo_smb",
                source_type="github_issues",
                query_kind="pain_query",
                classification_label="pain_signal_candidate",
                signal_type="pain_signal",
                body="Cash flow reporting is hard.",
                classification_confidence=0.8,
                price_signal_explicit=True,
                price_signal_confidence=0.7,
            )
        )
        unsupported = build_signal_score_breakdown(
            SignalScoringInput(
                topic_id="ai_cfo_smb",
                source_type="github_issues",
                query_kind="pain_query",
                classification_label="pain_signal_candidate",
                signal_type="pain_signal",
                body="Cash flow reporting is hard.",
                classification_confidence=0.8,
                price_signal_explicit=False,
                price_signal_confidence=0.9,
            )
        )

        self.assertGreater(boosted.final_score, baseline.final_score)
        self.assertEqual(unsupported.final_score, baseline.final_score)
        self.assertIn("price_signal:explicit_evidence_boost", boosted.explanation)

    def test_price_signal_scoring_helper_requires_evidence(self) -> None:
        signal = extract_price_signal(clean_evidence(raw_evidence("Tool costs $99/month.")))
        self.assertIsNotNone(signal)
        missing_citation = PriceSignal(
            price_signal_id="price_signal_missing",
            evidence_id="ev_missing",
            source_id="github_issues",
            source_type="github_issues",
            source_url="https://example.com/ev_missing",
            topic_id="ai_cfo_smb",
            query_kind="pain_query",
            current_spend_hint="$99/month",
            effort_cost_hint=None,
            price_complaint=None,
            willingness_to_pay_indicator="not_detected",
            evidence_cited="",
            confidence=0.7,
        )

        self.assertEqual(price_signal_scoring_boost(signal), 0.05)
        self.assertEqual(price_signal_scoring_boost(missing_citation), 0.0)

    def test_founder_discovery_package_displays_price_hints(self) -> None:
        project_root = Path("codex_tmp_price_signal_founder_package")
        if project_root.exists():
            shutil.rmtree(project_root)
        try:
            project_root.mkdir(parents=True)
            evidence_path = project_root / "price_fixture.json"
            evidence = raw_evidence(
                "Cash flow reporting is hard. We pay $99/month and still maintain a manual spreadsheet.",
                evidence_id="raw_founder_price",
            )
            evidence_path.write_text(
                json.dumps({"raw_evidence": [evidence.__dict__]}, indent=2),
                encoding="utf-8",
            )

            result = run_discovery_weekly(
                project_root=project_root,
                topic_id="ai_cfo_smb",
                run_id="price_signal_founder_package",
                input_raw_evidence=evidence_path.resolve(),
            )

            package_json = json.loads(result.artifact_paths["founder_discovery_package_json"].read_text(encoding="utf-8"))
            package_md = result.artifact_paths["founder_discovery_package_md"].read_text(encoding="utf-8")
        finally:
            if project_root.exists():
                shutil.rmtree(project_root)

        self.assertEqual(package_json["price_signal_count"], 1)
        self.assertIn("$99/mo", package_md)
        self.assertIn("Price hints", package_md)


if __name__ == "__main__":
    unittest.main()
