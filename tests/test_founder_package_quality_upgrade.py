import json
import shutil
import unittest
from pathlib import Path

from oos.discovery_weekly import run_discovery_weekly
from oos.founder_package import build_founder_package_quality_sections, render_founder_package_quality_sections
from oos.models import CandidateSignal, EvidenceClassification, RawEvidence, compute_raw_evidence_content_hash


ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / "codex_tmp_founder_package_quality_upgrade"


def raw_evidence(
    evidence_id: str,
    body: str,
    *,
    query_kind: str = "pain_query",
    source_type: str = "github_issues",
) -> dict:
    title = "Finance workflow pain"
    evidence = RawEvidence(
        evidence_id=evidence_id,
        source_id=source_type,
        source_type=source_type,
        source_name=source_type,
        source_url=f"https://example.com/{evidence_id}",
        collected_at="2026-05-05T00:00:00+00:00",
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
    return evidence.__dict__


def candidate_signal(
    signal_id: str,
    *,
    signal_type: str = "pain_signal",
    confidence: float = 0.8,
    urgency_hint: str = "medium",
    current_workaround: str = "manual spreadsheet",
    query_kind: str = "pain_query",
) -> CandidateSignal:
    signal = CandidateSignal(
        signal_id=signal_id,
        evidence_id=f"ev_{signal_id}",
        source_id="github_issues",
        source_type="github_issues",
        source_url=f"https://example.com/{signal_id}",
        topic_id="ai_cfo_smb",
        query_kind=query_kind,
        signal_type=signal_type,
        pain_summary="Manual invoice reconciliation takes too long.",
        target_user="developer",
        current_workaround=current_workaround,
        buying_intent_hint="possible",
        urgency_hint=urgency_hint,
        confidence=confidence,
        measurement_methods={
            "signal_type": "rule_based",
            "pain_summary": "rule_based",
            "target_user": "rule_based",
            "current_workaround": "rule_based",
            "buying_intent_hint": "rule_based",
            "urgency_hint": "rule_based",
            "confidence": "rule_based",
        },
        extraction_mode="rule_based_v2",
        classification="needs_human_review" if signal_type == "needs_human_review" else "pain_signal_candidate",
        classification_confidence=confidence,
        traceability={
            "evidence_id": f"ev_{signal_id}",
            "source_url": f"https://example.com/{signal_id}",
            "source_id": "github_issues",
            "topic_id": "ai_cfo_smb",
            "query_kind": query_kind,
        },
        scoring_model_version="signal_scoring_v2_embeddings_disabled",
        scoring_breakdown={"final_score": confidence},
    )
    signal.validate()
    return signal


def classification_for(signal: CandidateSignal) -> EvidenceClassification:
    classification = EvidenceClassification(
        evidence_id=signal.evidence_id,
        source_id=signal.source_id,
        source_type=signal.source_type,
        source_url=signal.source_url,
        topic_id=signal.topic_id,
        query_kind=signal.query_kind,
        classification=signal.classification,
        confidence=signal.classification_confidence,
        matched_rules=[signal.classification],
        reason="Fixture classification.",
        requires_human_review=signal.signal_type == "needs_human_review",
        is_noise=False,
    )
    classification.validate()
    return classification


class TestFounderPackageQualityUpgrade(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(TMP_ROOT, ignore_errors=True)
        self.project_root = TMP_ROOT / "project"
        self.project_root.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def test_package_includes_all_quality_sections_with_optional_artifacts(self) -> None:
        run_id = "quality_sections"
        run_dir = self.project_root / "artifacts" / "discovery_runs" / run_id
        run_dir.mkdir(parents=True)
        self._write_optional_artifacts(run_dir)
        evidence_path = self._write_raw_evidence(
            [
                raw_evidence(
                    "ev_price",
                    "Cash flow reporting is urgent before payroll. We pay $99/month and still use a manual spreadsheet.",
                    query_kind="customer_voice_query",
                ),
                raw_evidence(
                    "ev_burden",
                    "Month-end invoice reconciliation takes 20 hours/month in spreadsheets and blocks cash planning.",
                ),
            ]
        )

        result = run_discovery_weekly(
            project_root=self.project_root,
            topic_id="ai_cfo_smb",
            run_id=run_id,
            input_raw_evidence=evidence_path,
        )
        package = json.loads(result.artifact_paths["founder_discovery_package_json"].read_text(encoding="utf-8"))
        markdown = result.artifact_paths["founder_discovery_package_md"].read_text(encoding="utf-8")
        sections = package["quality_sections"]["sections"]

        self.assertIn("time_sensitive_opportunities", sections)
        self.assertIn("implied_burdens", sections)
        self.assertIn("price_signals", sections)
        self.assertIn("weak_pattern_candidates", sections)
        self.assertIn("kill_archive_warnings", sections)
        self.assertIn("customer_voice_query_yield", sections)
        self.assertIn("llm_review_outputs", sections)
        self.assertIn("evidence_confidence_risk_notes", sections)
        self.assertGreaterEqual(sections["implied_burdens"]["count"], 1)
        self.assertGreaterEqual(sections["price_signals"]["count"], 1)
        self.assertEqual(sections["weak_pattern_candidates"]["items"][0]["id"], "weak_pattern_001")
        self.assertEqual(sections["kill_archive_warnings"]["items"][0]["id"], "kill_warning_001")
        self.assertEqual(sections["llm_review_outputs"]["items"][0]["id"], "llm_review_quality")
        self.assertIn("## Quality review sections", markdown)
        self.assertIn("### Price Signals", markdown)
        self.assertIn("$99/mo", markdown)

    def test_quality_sections_show_empty_states_without_artifacts(self) -> None:
        signal = candidate_signal("manual_signal", current_workaround="unknown")
        sections = build_founder_package_quality_sections(
            candidate_signals=[signal],
            classifications=[classification_for(signal)],
            price_signals=[],
            run_dir=self.project_root / "missing_run_dir",
            collection_metadata={},
        )
        markdown = render_founder_package_quality_sections(sections)

        self.assertIn("No explicit price signals available.", markdown)
        self.assertIn("No weak_pattern_candidates.json artifact available.", markdown)
        self.assertIn("No kill_archive_warnings.json artifact available.", markdown)
        self.assertIn("No offline LLM review outputs available.", markdown)

    def test_evidence_confidence_risk_notes_are_traceable(self) -> None:
        review_signal = candidate_signal("review_signal", signal_type="needs_human_review", confidence=0.34, urgency_hint="unknown")
        sections = build_founder_package_quality_sections(
            candidate_signals=[review_signal],
            classifications=[classification_for(review_signal)],
            price_signals=[],
            run_dir=None,
            collection_metadata={},
        )
        risk_items = sections["sections"]["evidence_confidence_risk_notes"]["items"]

        self.assertEqual(risk_items[0]["evidence_id"], "ev_review_signal")
        self.assertIn("needs human review", risk_items[0]["risk_note"])
        self.assertIn("low confidence", risk_items[0]["risk_note"])

    def test_output_is_deterministic_and_readable(self) -> None:
        signals = [
            candidate_signal("signal_b", confidence=0.7),
            candidate_signal("signal_a", confidence=0.9, urgency_hint="high"),
        ]
        classifications = [classification_for(signal) for signal in signals]

        first = build_founder_package_quality_sections(
            candidate_signals=list(reversed(signals)),
            classifications=classifications,
            price_signals=[],
            run_dir=None,
            collection_metadata={},
        )
        second = build_founder_package_quality_sections(
            candidate_signals=signals,
            classifications=classifications,
            price_signals=[],
            run_dir=None,
            collection_metadata={},
        )

        self.assertEqual(render_founder_package_quality_sections(first), render_founder_package_quality_sections(second))
        self.assertIn("### Time Sensitive Opportunities", render_founder_package_quality_sections(first))

    def _write_raw_evidence(self, items: list[dict]) -> Path:
        path = self.project_root / "raw_evidence.json"
        path.write_text(json.dumps({"raw_evidence": items}, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def _write_optional_artifacts(self, run_dir: Path) -> None:
        (run_dir / "weak_pattern_candidates.json").write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "pattern_id": "weak_pattern_001",
                            "summary": "Repeated weak spreadsheet reconciliation signals.",
                            "evidence_ids": ["ev_price", "ev_burden"],
                            "confidence": 0.42,
                        }
                    ]
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        (run_dir / "kill_archive_warnings.json").write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "warning_id": "kill_warning_001",
                            "warning": "Similar idea died as custom consulting.",
                            "severity": "warning",
                            "evidence_id": "ev_price",
                        }
                    ]
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        (run_dir / "customer_voice_query_yield.json").write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "id": "cvq_yield_001",
                            "summary": "1 customer voice query produced 1 candidate signal.",
                            "confidence": 1.0,
                        }
                    ]
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        (run_dir / "llm_signal_review_dry_run.json").write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "review_id": "llm_review_quality",
                            "candidate_signal_id": "candidate_signal_ev_price_pain_signal_candidate",
                            "evidence_id": "ev_price",
                            "source_url": "https://example.com/ev_price",
                            "original_confidence": 0.8,
                            "review_output": {
                                "pain_summary": "Advisory review says the evidence supports a real finance workflow pain.",
                                "pain_score": 0.75,
                            },
                        }
                    ]
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
