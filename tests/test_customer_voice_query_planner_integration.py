from __future__ import annotations

import json
import shutil
import unittest
from dataclasses import replace
from pathlib import Path

from oos.cli import main
from oos.customer_voice_queries import (
    APPROVAL_STATE_REJECTED,
    APPROVAL_STATE_RETIRED,
    QUERY_KIND_CUSTOMER_VOICE,
    approve_customer_voice_query,
    generate_customer_voice_queries,
)
from oos.query_planner import build_customer_voice_query_plans
from oos.source_registry import default_source_registry


class TestCustomerVoiceQueryPlannerIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = default_source_registry()
        self.tmp_root = Path("codex_tmp_customer_voice_query_plans")
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)
        self.tmp_root.mkdir(parents=True)

    def tearDown(self) -> None:
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)

    def _queries(self):
        return generate_customer_voice_queries(
            "ai_cfo_smb",
            max_queries_per_persona=2,
            source_type_filter=["github_issues", "stack_exchange", "reddit"],
        )

    def test_proposed_queries_do_not_become_query_plans_by_default(self) -> None:
        plans = build_customer_voice_query_plans(
            topic_id="ai_cfo_smb",
            customer_voice_queries=self._queries(),
            source_registry=self.registry,
        )
        self.assertEqual(plans, [])

    def test_approved_queries_become_query_plans(self) -> None:
        approved = [approve_customer_voice_query(query) for query in self._queries()]
        plans = build_customer_voice_query_plans(
            topic_id="ai_cfo_smb",
            customer_voice_queries=approved,
            source_registry=self.registry,
            source_type_filter=["github_issues"],
            max_total_queries=3,
        )
        self.assertEqual(len(plans), 3)
        self.assertTrue(all(plan.query_kind == QUERY_KIND_CUSTOMER_VOICE for plan in plans))
        self.assertTrue(all(plan.source_type == "github_issues" for plan in plans))
        self.assertTrue(all(plan.live_network_enabled is False for plan in plans))

    def test_rejected_and_retired_queries_do_not_become_query_plans(self) -> None:
        queries = self._queries()[:2]
        non_executable = [
            replace(queries[0], approval_state=APPROVAL_STATE_REJECTED),
            replace(queries[1], approval_state=APPROVAL_STATE_RETIRED),
        ]
        plans = build_customer_voice_query_plans(
            topic_id="ai_cfo_smb",
            customer_voice_queries=non_executable,
            source_registry=self.registry,
        )
        self.assertEqual(plans, [])

    def test_expected_source_fit_is_respected(self) -> None:
        query = approve_customer_voice_query(
            generate_customer_voice_queries(
                "ai_cfo_smb",
                persona_ids=["bookkeeper"],
                max_queries_per_persona=1,
                source_type_filter=["stack_exchange"],
            )[0]
        )
        plans = build_customer_voice_query_plans(
            topic_id="ai_cfo_smb",
            customer_voice_queries=[query],
            source_registry=self.registry,
        )
        self.assertEqual({plan.source_type for plan in plans}, {"stack_exchange"})

    def test_source_type_filter_works(self) -> None:
        approved = [approve_customer_voice_query(query) for query in self._queries()]
        plans = build_customer_voice_query_plans(
            topic_id="ai_cfo_smb",
            customer_voice_queries=approved,
            source_registry=self.registry,
            source_type_filter=["github_issues"],
        )
        self.assertTrue(plans)
        self.assertEqual({plan.source_type for plan in plans}, {"github_issues"})

    def test_max_queries_per_persona_works(self) -> None:
        approved = [approve_customer_voice_query(query) for query in self._queries()]
        plans = build_customer_voice_query_plans(
            topic_id="ai_cfo_smb",
            customer_voice_queries=approved,
            source_registry=self.registry,
            source_type_filter=["github_issues"],
            max_queries_per_persona=1,
        )
        counts: dict[str, int] = {}
        for plan in plans:
            persona_id = str(plan.raw_metadata["persona_id"])
            counts[persona_id] = counts.get(persona_id, 0) + 1
        self.assertTrue(plans)
        self.assertEqual(set(counts.values()), {1})

    def test_max_total_queries_works(self) -> None:
        approved = [approve_customer_voice_query(query) for query in self._queries()]
        plans = build_customer_voice_query_plans(
            topic_id="ai_cfo_smb",
            customer_voice_queries=approved,
            source_registry=self.registry,
            max_total_queries=5,
        )
        self.assertEqual(len(plans), 5)

    def test_ordering_is_deterministic(self) -> None:
        approved = [approve_customer_voice_query(query) for query in self._queries()]
        first = build_customer_voice_query_plans(
            topic_id="ai_cfo_smb",
            customer_voice_queries=approved,
            source_registry=self.registry,
            source_type_filter=["github_issues"],
        )
        second = build_customer_voice_query_plans(
            topic_id="ai_cfo_smb",
            customer_voice_queries=list(reversed(approved)),
            source_registry=self.registry,
            source_type_filter=["github_issues"],
        )
        self.assertEqual([plan.query_plan_id for plan in first], [plan.query_plan_id for plan in second])

    def test_metadata_preserves_customer_voice_traceability(self) -> None:
        query = approve_customer_voice_query(self._queries()[0])
        plans = build_customer_voice_query_plans(
            topic_id="ai_cfo_smb",
            customer_voice_queries=[query],
            source_registry=self.registry,
            source_type_filter=["github_issues"],
        )
        self.assertEqual(plans[0].raw_metadata["persona_id"], query.persona_id)
        self.assertEqual(plans[0].raw_metadata["customer_voice_query_id"], query.query_id)
        self.assertEqual(plans[0].raw_metadata["query_intent"], query.query_intent)
        self.assertEqual(plans[0].raw_metadata["approval_state"], "approved")

    def test_future_inactive_topics_do_not_generate_active_plans_by_default(self) -> None:
        self.assertEqual(generate_customer_voice_queries("personal_finance_household"), [])
        plans = build_customer_voice_query_plans(
            topic_id="personal_finance_household",
            customer_voice_queries=[],
            source_registry=self.registry,
        )
        self.assertEqual(plans, [])

    def test_reddit_plans_are_not_emitted_when_collector_unavailable(self) -> None:
        approved = [
            approve_customer_voice_query(query)
            for query in generate_customer_voice_queries(
                "ai_cfo_smb",
                source_type_filter=["reddit"],
                max_queries_per_persona=1,
            )
        ]
        plans = build_customer_voice_query_plans(
            topic_id="ai_cfo_smb",
            customer_voice_queries=approved,
            source_registry=self.registry,
            source_type_filter=["reddit"],
        )
        self.assertEqual(plans, [])

    def test_cli_preview_without_approval_flag_writes_zero_plans(self) -> None:
        output_json = (self.tmp_root / "plans_without_approval.json").resolve()
        output_md = (self.tmp_root / "plans_without_approval.md").resolve()
        exit_code = main(
            [
                "preview-customer-voice-query-plans",
                "--project-root",
                str(self.tmp_root),
                "--topic",
                "ai_cfo_smb",
                "--max-total-queries",
                "10",
                "--output",
                str(output_json),
                "--output-md",
                str(output_md),
            ]
        )
        self.assertEqual(exit_code, 0)
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        self.assertGreater(payload["generated_queries_count"], 0)
        self.assertEqual(payload["approved_queries_count"], 0)
        self.assertEqual(payload["query_plans_count"], 0)
        self.assertIn("approval_required", payload["skipped_reasons"])
        self.assertIn("# Customer Voice Query Plan Preview", output_md.read_text(encoding="utf-8"))

    def test_cli_preview_with_approval_flag_writes_bounded_plans(self) -> None:
        output_json = (self.tmp_root / "plans_with_approval.json").resolve()
        output_md = (self.tmp_root / "plans_with_approval.md").resolve()
        exit_code = main(
            [
                "preview-customer-voice-query-plans",
                "--project-root",
                str(self.tmp_root),
                "--topic",
                "ai_cfo_smb",
                "--source-type",
                "github_issues",
                "--max-queries-per-persona",
                "2",
                "--max-total-queries",
                "10",
                "--approve-generated-preview-queries",
                "--output",
                str(output_json),
                "--output-md",
                str(output_md),
            ]
        )
        self.assertEqual(exit_code, 0)
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        self.assertEqual(payload["approved_queries_count"], payload["generated_queries_count"])
        self.assertLessEqual(payload["query_plans_count"], 10)
        self.assertTrue(payload["query_plans"])
        self.assertEqual({plan["source_type"] for plan in payload["query_plans"]}, {"github_issues"})

    def test_cli_does_not_run_collectors_network_or_llm(self) -> None:
        output_json = (self.tmp_root / "safety.json").resolve()
        output_md = (self.tmp_root / "safety.md").resolve()
        exit_code = main(
            [
                "preview-customer-voice-query-plans",
                "--project-root",
                str(self.tmp_root),
                "--topic",
                "ai_cfo_smb",
                "--approve-generated-preview-queries",
                "--max-total-queries",
                "2",
                "--output",
                str(output_json),
                "--output-md",
                str(output_md),
            ]
        )
        self.assertEqual(exit_code, 0)
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["safety"],
            {"collectors_run": False, "live_network_calls": False, "llm_calls": False},
        )


if __name__ == "__main__":
    unittest.main()
