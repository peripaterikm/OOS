import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.artifact_store import ArtifactStore
from oos.models import (
    CouncilDecision,
    Evidence,
    Experiment,
    Hypothesis,
    IdeaScreenStatus,
    IdeaVariant,
    KillReason,
    OpportunityCard,
    PortfolioState,
    PortfolioStateEnum,
    Signal,
    SignalStatus,
)


class TestArtifactStoreRoundTrip(unittest.TestCase):
    def test_roundtrip_all_models_and_utf8(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "artifacts"
            store = ArtifactStore(root_dir=root)

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

            # Ensure UTF-8 JSON does not escape Cyrillic by default.
            opp_path = store.path_for("opportunities", "opp_1")
            text = opp_path.read_text(encoding="utf-8")
            self.assertIn("Сократить ручной ввод", text)


if __name__ == "__main__":
    unittest.main()

