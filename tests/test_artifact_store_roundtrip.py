import unittest
from pathlib import Path
import shutil

from oos.artifact_store import ArtifactStore
from oos.models import (
    CandidateSignal,
    CleanedEvidence,
    CouncilDecision,
    EvidenceClassification,
    Evidence,
    Experiment,
    FounderReviewDecision,
    FounderReviewDecisionEnum,
    Hypothesis,
    IdeaScreenStatus,
    IdeaVariant,
    KillReason,
    OpportunityCard,
    PortfolioState,
    PortfolioStateEnum,
    RawEvidence,
    Signal,
    SignalStatus,
    compute_raw_evidence_content_hash,
)


class TestArtifactStoreRoundTrip(unittest.TestCase):
    def test_roundtrip_all_models_and_utf8(self) -> None:
        tmp = Path("codex_tmp_artifact_store_roundtrip")
        if tmp.exists():
            shutil.rmtree(tmp)
        try:
            root = tmp / "artifacts"
            store = ArtifactStore(root_dir=root)

            raw_evidence = RawEvidence(
                evidence_id="raw_ev_1",
                source_id="hacker_news_algolia",
                source_type="public_api",
                source_name="Hacker News Algolia",
                source_url="https://news.ycombinator.com/item?id=123",
                collected_at="2026-04-26T10:00:00+00:00",
                title="Manual finance workflow",
                body="SMB owner describes copying bank exports into spreadsheets every week.",
                language="en",
                topic_id="ai_cfo_smb",
                query_kind="pain_search",
                content_hash=compute_raw_evidence_content_hash(
                    title="Manual finance workflow",
                    body="SMB owner describes copying bank exports into spreadsheets every week.",
                ),
                author_or_context="SMB owner",
                raw_metadata={"fixture": True},
                access_policy="fixture_offline_first",
                collection_method="fixture",
            )
            store.write_model(raw_evidence)
            self.assertEqual(store.read_model(RawEvidence, "raw_ev_1"), raw_evidence)

            cleaned = CleanedEvidence(
                evidence_id="raw_ev_1",
                source_id="hacker_news_algolia",
                source_type="public_api",
                source_url="https://news.ycombinator.com/item?id=123",
                topic_id="ai_cfo_smb",
                query_kind="pain_search",
                title="Manual finance workflow",
                body="SMB owner describes copying bank exports into spreadsheets every week.",
                normalized_title="Manual finance workflow",
                normalized_body="SMB owner describes copying bank exports into spreadsheets every week.",
                normalized_url="https://news.ycombinator.com/item?id=123",
                normalized_content_hash=compute_raw_evidence_content_hash(
                    title="Manual finance workflow",
                    body="SMB owner describes copying bank exports into spreadsheets every week.",
                ),
                language="en",
                original_content_hash=raw_evidence.content_hash,
                cleaning_notes=["whitespace_normalized", "url_normalized"],
            )
            store.write_model(cleaned)
            self.assertEqual(store.read_model(CleanedEvidence, "raw_ev_1"), cleaned)

            classification = EvidenceClassification(
                evidence_id="raw_ev_1",
                source_id="hacker_news_algolia",
                source_type="public_api",
                source_url="https://news.ycombinator.com/item?id=123",
                topic_id="ai_cfo_smb",
                query_kind="pain_search",
                classification="workaround_signal_candidate",
                confidence=0.75,
                matched_rules=["workaround_signal_candidate:spreadsheet"],
                reason="Matched deterministic workaround keyword rule.",
                requires_human_review=False,
                is_noise=False,
            )
            store.write_model(classification)
            self.assertEqual(store.read_model(EvidenceClassification, "raw_ev_1"), classification)

            candidate_signal = CandidateSignal(
                signal_id="candidate_signal_raw_ev_1_workaround_signal_candidate",
                evidence_id="raw_ev_1",
                source_id="hacker_news_algolia",
                source_type="public_api",
                source_url="https://news.ycombinator.com/item?id=123",
                topic_id="ai_cfo_smb",
                query_kind="pain_search",
                signal_type="workaround",
                pain_summary="SMB owner describes copying bank exports into spreadsheets every week.",
                target_user="founder",
                current_workaround="copying bank exports into spreadsheets every week",
                buying_intent_hint="not_detected",
                urgency_hint="low",
                confidence=0.73,
                measurement_methods={
                    "signal_type": "rule_based",
                    "pain_summary": "rule_based",
                    "target_user": "rule_based",
                    "current_workaround": "rule_based",
                    "buying_intent_hint": "rule_based",
                    "urgency_hint": "rule_based",
                    "confidence": "rule_based",
                },
                extraction_mode="rule_based_v1",
                classification="workaround_signal_candidate",
                classification_confidence=0.75,
                traceability={
                    "evidence_id": "raw_ev_1",
                    "source_url": "https://news.ycombinator.com/item?id=123",
                    "source_id": "hacker_news_algolia",
                    "topic_id": "ai_cfo_smb",
                    "query_kind": "pain_search",
                },
            )
            store.write_model(candidate_signal)
            self.assertEqual(
                store.read_model(CandidateSignal, "candidate_signal_raw_ev_1_workaround_signal_candidate"),
                candidate_signal,
            )

            signal = Signal(
                id="sig_1",
                source="manual",
                timestamp="2026-04-16T00:00:00",
                raw_content="Пользователь жалуется на ручной ввод.",
                extracted_pain="Ручной ввод занимает слишком много времени.",
                candidate_icp="операционный менеджер",
                validity_specificity=1,
                validity_recurrence=1,
                validity_workaround=1,
                validity_cost_signal=1,
                validity_icp_match=1,
                validity_score=5,
                status=SignalStatus.validated,
                rejection_reason=None,
                metadata={"lang": "ru"},
            )
            store.write_model(signal)
            self.assertEqual(store.read_model(Signal, "sig_1"), signal)

            opp = OpportunityCard(
                id="opp_1",
                title="Сократить ручной ввод",
                source_signal_ids=["sig_1"],
                pain_summary="Ручной ввод данных в таблицы",
                icp="операционные команды",
                opportunity_type="workflow_friction",
                why_it_matters="Экономия времени и снижение ошибок.",
                early_monetization_options=["subscription"],
                initial_notes="v1 note",
            )
            store.write_model(opp)
            self.assertEqual(store.read_model(OpportunityCard, "opp_1"), opp)

            idea = IdeaVariant(
                id="idea_1",
                opportunity_id="opp_1",
                short_concept="Импорт и валидация данных из форм",
                business_model="subscription",
                standardization_focus="шаблоны форм и правила валидации",
                ai_leverage="извлечение полей из текста",
                external_execution_needed="нет",
                rough_monetization_model="подписка по количеству пользователей",
                status=IdeaScreenStatus.candidate,
                screen_result_id=None,
            )
            store.write_model(idea)
            self.assertEqual(store.read_model(IdeaVariant, "idea_1"), idea)

            hyp = Hypothesis(
                id="hyp_1",
                idea_id="idea_1",
                critical_assumptions=["пользователи готовы менять процесс"],
                most_fragile_assumption="пользователи готовы менять процесс",
                success_signals=["сокращение времени ввода на 30%"],
                kill_criteria=["нет улучшения времени ввода"],
                notes="заметка",
            )
            store.write_model(hyp)
            self.assertEqual(store.read_model(Hypothesis, "hyp_1"), hyp)

            exp = Experiment(
                id="exp_1",
                idea_id="idea_1",
                hypothesis_id="hyp_1",
                cheapest_next_test="10 интервью + прототип в таблице",
                plan_7d="Провести 5 интервью и собрать требования.",
                plan_14d="Провести 10 интервью и протестировать прототип.",
                success_metrics={"interviews": 10},
                failure_metrics={"interviews": 0},
                status="planned",
                results_summary="",
            )
            store.write_model(exp)
            self.assertEqual(store.read_model(Experiment, "exp_1"), exp)

            ev = Evidence(
                id="ev_1",
                experiment_id="exp_1",
                type="qualitative",
                content="Респондент подтвердил боль и workaround.",
                timestamp="2026-04-16T00:00:00",
                source="interview",
            )
            store.write_model(ev)
            self.assertEqual(store.read_model(Evidence, "ev_1"), ev)

            cd = CouncilDecision(
                id="cd_1",
                idea_id="idea_1",
                skeptic_kill_scenarios=["слишком много исключений"],
                assumption_auditor_least_proven="готовность платить",
                pattern_matcher_similarity=["похоже на прошлый провал X"],
                final_recommendation="park",
                suspiciously_clean=False,
                notes="",
            )
            store.write_model(cd)
            self.assertEqual(store.read_model(CouncilDecision, "cd_1"), cd)

            ps = PortfolioState(
                id="ps_1",
                opportunity_id="opp_1",
                state=PortfolioStateEnum.Active,
                reason="в активной оценке",
                linked_council_decision_id="cd_1",
                linked_kill_reason_id=None,
            )
            store.write_model(ps)
            self.assertEqual(store.read_model(PortfolioState, "ps_1"), ps)

            kr = KillReason(
                id="kr_1",
                idea_id="idea_1",
                kill_date="2026-04-16T00:00:00",
                failed_checks=["productizable"],
                matched_anti_patterns=["founder_bottleneck"],
                summary="Не масштабируется без участия основателя.",
                looked_attractive_because="Казалось быстрым решением.",
                notes="",
            )
            store.write_model(kr)
            self.assertEqual(store.read_model(KillReason, "kr_1"), kr)

            frd = FounderReviewDecision(
                id="frd_1",
                opportunity_id="opp_1",
                decision=FounderReviewDecisionEnum.Parked,
                reason="Нужно проверить спрос до продолжения.",
                selected_next_experiment_or_action="Провести 5 интервью с операционными менеджерами.",
                timestamp="2026-04-16T00:00:00",
                portfolio_updated=True,
                readiness_report_id="v1_readiness_2026-04-16T00-00-00+00-00.json",
                weekly_review_id="weekly_review_2026-W16.json",
                council_decision_ids=["cd_1"],
                hypothesis_ids=["hyp_1"],
                experiment_ids=["exp_1"],
                linked_kill_reason_id=None,
            )
            store.write_model(frd)
            self.assertEqual(store.read_model(FounderReviewDecision, "frd_1"), frd)

            # Ensure UTF-8 JSON does not escape Cyrillic by default.
            opp_path = store.path_for("opportunities", "opp_1")
            text = opp_path.read_text(encoding="utf-8")
            self.assertIn("Сократить ручной ввод", text)

        finally:
            if tmp.exists():
                shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()

