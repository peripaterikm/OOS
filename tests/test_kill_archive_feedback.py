import json
import shutil
import unittest
from pathlib import Path

from oos.discovery_weekly import run_discovery_weekly
from oos.founder_package import build_founder_package_quality_sections, render_founder_package_quality_sections
from oos.kill_archive_feedback import (
    apply_kill_archive_feedback,
    find_kill_archive_match,
    write_kill_archive_warnings,
)
from oos.models import CandidateSignal, EvidenceClassification, KillReason, RawEvidence, compute_raw_evidence_content_hash
from oos.signal_scoring import SignalScoringInput, build_signal_score_breakdown


ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / "codex_tmp_kill_archive_feedback"


def candidate_signal(
    signal_id: str = "sig_invoice_custom",
    *,
    pain_summary: str = "Manual invoice reconciliation depends on custom spreadsheet work for each client.",
    current_workaround: str = "manual spreadsheet",
    confidence: float = 0.72,
) -> CandidateSignal:
    signal = CandidateSignal(
        signal_id=signal_id,
        evidence_id=f"ev_{signal_id}",
        source_id="github_issues",
        source_type="github_issues",
        source_url=f"https://example.com/{signal_id}",
        topic_id="ai_cfo_smb",
        query_kind="pain_query",
        signal_type="pain_signal",
        pain_summary=pain_summary,
        target_user="finance ops",
        current_workaround=current_workaround,
        buying_intent_hint="possible",
        urgency_hint="medium",
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
        classification="pain_signal_candidate",
        classification_confidence=0.8,
        traceability={
            "evidence_id": f"ev_{signal_id}",
            "source_url": f"https://example.com/{signal_id}",
            "source_id": "github_issues",
            "topic_id": "ai_cfo_smb",
            "query_kind": "pain_query",
        },
        scoring_model_version="signal_scoring_v2_embeddings_disabled",
        scoring_breakdown={"final_score": confidence, "explanation": ["fixture"]},
    )
    signal.validate()
    return signal


def kill_reason(kill_id: str = "kill_custom_consulting") -> KillReason:
    kill = KillReason(
        id=kill_id,
        idea_id="opp_custom_invoice_consulting",
        kill_date="2026-05-05T00:00:00+00:00",
        failed_checks=["repeatability", "gross_margin"],
        matched_anti_patterns=["custom_per_client_handling", "spreadsheet_wrapper"],
        summary="Killed because invoice reconciliation became custom consulting per client.",
        looked_attractive_because="Finance teams had painful manual spreadsheet reconciliation.",
        notes="Avoid elevating similar custom invoice workflow patterns without founder review.",
    )
    kill.validate()
    return kill


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
        requires_human_review=False,
        is_noise=False,
    )
    classification.validate()
    return classification


class TestKillArchiveFeedback(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(TMP_ROOT, ignore_errors=True)
        self.project_root = TMP_ROOT / "project"
        self.project_root.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def test_similar_killed_pattern_triggers_flag_and_preserves_evidence(self) -> None:
        signal = candidate_signal()
        warning = find_kill_archive_match(signal, [kill_reason()])

        self.assertIsNotNone(warning)
        self.assertTrue(warning.kill_pattern_flag)
        self.assertEqual(warning.evidence_id, signal.evidence_id)
        self.assertEqual(warning.evidence_linkage["source_url"], signal.source_url)
        self.assertEqual(warning.similar_killed_opportunity, "opp_custom_invoice_consulting")
        self.assertIn("invoice", warning.matched_terms)

    def test_similar_killed_pattern_reduces_score_without_auto_kill(self) -> None:
        signal = candidate_signal(confidence=0.72)
        result = apply_kill_archive_feedback([signal], kill_reasons=[kill_reason()])

        updated = result.candidate_signals[0]
        self.assertEqual(len(result.warnings), 1)
        self.assertLess(updated.confidence, signal.confidence)
        self.assertTrue(updated.scoring_breakdown["kill_pattern_flag"])
        self.assertGreater(updated.scoring_breakdown["kill_pattern_penalty"], 0)
        self.assertEqual(updated.signal_type, "pain_signal")
        self.assertNotIn("auto_kill", json.dumps(updated.scoring_breakdown))

    def test_no_match_produces_no_penalty(self) -> None:
        signal = candidate_signal(
            "sig_unrelated",
            pain_summary="A founder asks for a better way to schedule interviews with candidates.",
            current_workaround="calendar booking",
            confidence=0.61,
        )
        result = apply_kill_archive_feedback([signal], kill_reasons=[kill_reason()])

        self.assertEqual(result.warnings, [])
        self.assertEqual(result.candidate_signals[0].confidence, 0.61)
        self.assertNotIn("kill_pattern_penalty", result.candidate_signals[0].scoring_breakdown)

    def test_signal_scoring_supports_kill_pattern_penalty(self) -> None:
        base = build_signal_score_breakdown(
            SignalScoringInput(
                topic_id="ai_cfo_smb",
                source_type="github_issues",
                query_kind="pain_query",
                classification_label="pain_signal_candidate",
                signal_type="pain_signal",
                title="Invoice reconciliation pain",
                body="Manual spreadsheet reconciliation takes too long.",
                classification_confidence=0.8,
            )
        )
        penalized = build_signal_score_breakdown(
            SignalScoringInput(
                topic_id="ai_cfo_smb",
                source_type="github_issues",
                query_kind="pain_query",
                classification_label="pain_signal_candidate",
                signal_type="pain_signal",
                title="Invoice reconciliation pain",
                body="Manual spreadsheet reconciliation takes too long.",
                classification_confidence=0.8,
                kill_pattern_flag=True,
                kill_pattern_penalty=0.12,
            )
        )

        self.assertTrue(penalized.kill_pattern_flag)
        self.assertEqual(penalized.kill_pattern_penalty, 0.12)
        self.assertLess(penalized.final_score, base.final_score)

    def test_founder_package_explains_penalty(self) -> None:
        signal = candidate_signal()
        result = apply_kill_archive_feedback([signal], kill_reasons=[kill_reason()])
        run_dir = self.project_root / "artifacts" / "discovery_runs" / "kill_warning"
        run_dir.mkdir(parents=True)
        write_kill_archive_warnings(run_dir / "kill_archive_warnings.json", result.warnings)

        sections = build_founder_package_quality_sections(
            candidate_signals=result.candidate_signals,
            classifications=[classification_for(result.candidate_signals[0])],
            price_signals=[],
            run_dir=run_dir,
            collection_metadata={},
        )
        markdown = render_founder_package_quality_sections(sections)

        item = sections["sections"]["kill_archive_warnings"]["items"][0]
        self.assertIn("opp_custom_invoice_consulting", item["summary"])
        self.assertIn("Killed because invoice reconciliation", markdown)
        self.assertIn("kill_archive_warnings", json.dumps(sections))

    def test_discovery_lookup_writes_kill_archive_warning_artifact(self) -> None:
        kills_dir = self.project_root / "artifacts" / "kills"
        kills_dir.mkdir(parents=True)
        (kills_dir / "kill_custom_consulting.json").write_text(
            json.dumps(kill_reason().__dict__, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        raw_path = self.project_root / "raw_evidence.json"
        title = "Invoice reconciliation pain"
        body = (
            "Finance ops teams have painful manual invoice reconciliation. "
            "They rely on custom spreadsheet work for each client and need a tool."
        )
        evidence = RawEvidence(
            evidence_id="ev_live_kill_match",
            source_id="github_issues",
            source_type="github_issues",
            source_name="github_issues",
            source_url="https://example.com/kill-match",
            collected_at="2026-05-05T00:00:00+00:00",
            title=title,
            body=body,
            language="en",
            topic_id="ai_cfo_smb",
            query_kind="pain_query",
            content_hash=compute_raw_evidence_content_hash(title=title, body=body),
            author_or_context="fixture",
            raw_metadata={"fixture": True},
            access_policy="fixture",
            collection_method="fixture",
        )
        raw_path.write_text(json.dumps({"raw_evidence": [evidence.__dict__]}, indent=2, sort_keys=True), encoding="utf-8")

        result = run_discovery_weekly(
            project_root=self.project_root,
            topic_id="ai_cfo_smb",
            run_id="kill_archive_integration",
            input_raw_evidence=raw_path,
        )
        warnings = json.loads(result.artifact_paths["kill_archive_warnings"].read_text(encoding="utf-8"))["items"]
        candidate_signals = json.loads(result.artifact_paths["candidate_signals"].read_text(encoding="utf-8"))

        self.assertEqual(len(warnings), 1)
        self.assertTrue(warnings[0]["kill_pattern_flag"])
        self.assertLess(candidate_signals[0]["confidence"], candidate_signals[0]["scoring_breakdown"]["kill_pattern_penalty"] + 1)
        self.assertNotIn("Killed", candidate_signals[0]["signal_type"])

    def test_output_ordering_is_deterministic(self) -> None:
        signals = [candidate_signal("sig_b"), candidate_signal("sig_a")]
        first = apply_kill_archive_feedback(signals, kill_reasons=[kill_reason()])
        second = apply_kill_archive_feedback(list(reversed(signals)), kill_reasons=[kill_reason()])

        self.assertEqual([item.warning_id for item in first.warnings], [item.warning_id for item in second.warnings])


if __name__ == "__main__":
    unittest.main()
