from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from oos.cli import main
from oos.customer_voice_queries import (
    APPROVAL_STATE_APPROVED,
    APPROVAL_STATE_PROPOSED,
    CUSTOMER_VOICE_QUERY_PROMPT_CONTRACT,
    GENERATION_METHOD_DETERMINISTIC_SEED,
    QUERY_KIND_CUSTOMER_VOICE,
    approve_customer_voice_query,
    generate_customer_voice_queries,
    get_customer_voice_personas,
    get_customer_voice_topic_ids,
)


class TestCustomerVoiceQueries(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_root = Path("codex_tmp_customer_voice_queries")
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)
        self.tmp_root.mkdir(parents=True)

    def tearDown(self) -> None:
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)

    def test_ai_cfo_smb_personas_include_required_roles(self) -> None:
        persona_ids = {persona.persona_id for persona in get_customer_voice_personas("ai_cfo_smb")}
        self.assertEqual(
            {
                "smb_owner",
                "bookkeeper",
                "accountant",
                "fractional_cfo",
                "finance_manager",
                "operations_manager",
                "freelancer_solo_operator",
            },
            persona_ids,
        )

    def test_each_active_ai_cfo_smb_persona_has_at_least_five_queries(self) -> None:
        for persona in get_customer_voice_personas("ai_cfo_smb"):
            queries = generate_customer_voice_queries("ai_cfo_smb", persona_ids=[persona.persona_id])
            self.assertGreaterEqual(len(queries), 5, persona.persona_id)

    def test_queries_are_not_generic_founder_only_language(self) -> None:
        queries = generate_customer_voice_queries("ai_cfo_smb")
        query_texts = [query.query_text for query in queries]
        self.assertNotIn("small business problem", query_texts)
        self.assertNotIn("business problem", query_texts)
        persona_ids = {query.persona_id for query in queries}
        self.assertIn("bookkeeper", persona_ids)
        self.assertIn("accountant", persona_ids)
        self.assertIn("operations_manager", persona_ids)
        self.assertIn("freelancer_solo_operator", persona_ids)

    def test_generated_query_ids_are_deterministic_and_stable(self) -> None:
        first = generate_customer_voice_queries("ai_cfo_smb")
        second = generate_customer_voice_queries("ai_cfo_smb")
        self.assertEqual([query.query_id for query in first], [query.query_id for query in second])
        self.assertTrue(all(query.query_id.startswith("cvq_ai_cfo_smb_") for query in first))

    def test_max_queries_per_persona_cap_works(self) -> None:
        queries = generate_customer_voice_queries("ai_cfo_smb", max_queries_per_persona=2)
        counts: dict[str, int] = {}
        for query in queries:
            counts[query.persona_id] = counts.get(query.persona_id, 0) + 1
        self.assertEqual(set(counts.values()), {2})

    def test_persona_ids_filter_works(self) -> None:
        queries = generate_customer_voice_queries("ai_cfo_smb", persona_ids=["bookkeeper"])
        self.assertGreaterEqual(len(queries), 5)
        self.assertEqual({query.persona_id for query in queries}, {"bookkeeper"})

    def test_source_type_filter_works(self) -> None:
        queries = generate_customer_voice_queries("ai_cfo_smb", source_type_filter=["stack_exchange"])
        self.assertTrue(queries)
        self.assertTrue(all("stack_exchange" in query.expected_source_fit for query in queries))
        self.assertTrue(all(query.expected_source_fit == ["stack_exchange"] for query in queries))

    def test_future_topics_are_inactive_by_default(self) -> None:
        self.assertEqual(get_customer_voice_personas("personal_finance_household"), [])
        self.assertEqual(get_customer_voice_personas("freelancer_solo_finance"), [])
        self.assertEqual(get_customer_voice_personas("immigrant_finance_israel"), [])
        self.assertEqual(generate_customer_voice_queries("personal_finance_household"), [])
        inactive_topic_ids = set(get_customer_voice_topic_ids(include_inactive=True))
        self.assertIn("personal_finance_household", inactive_topic_ids)
        self.assertIn("freelancer_solo_finance", inactive_topic_ids)
        self.assertIn("immigrant_finance_israel", inactive_topic_ids)
        self.assertNotIn("personal_finance_household", set(get_customer_voice_topic_ids()))

    def test_every_query_has_required_fields_and_approval_state(self) -> None:
        queries = generate_customer_voice_queries("ai_cfo_smb")
        for query in queries:
            self.assertEqual(query.query_kind, QUERY_KIND_CUSTOMER_VOICE)
            self.assertEqual(query.generation_method, GENERATION_METHOD_DETERMINISTIC_SEED)
            self.assertEqual(query.approval_state, APPROVAL_STATE_PROPOSED)
            self.assertTrue(query.query_intent)
            self.assertTrue(query.expected_source_fit)
            self.assertTrue(query.rationale)
            self.assertTrue(query.tags)
            query.validate()

    def test_approve_customer_voice_query_returns_approved_copy(self) -> None:
        query = generate_customer_voice_queries("ai_cfo_smb", max_queries_per_persona=1)[0]
        approved = approve_customer_voice_query(query)
        self.assertEqual(query.approval_state, APPROVAL_STATE_PROPOSED)
        self.assertEqual(approved.approval_state, APPROVAL_STATE_APPROVED)
        self.assertEqual(approved.query_id, query.query_id)

    def test_generated_ordering_is_deterministic(self) -> None:
        queries = generate_customer_voice_queries("ai_cfo_smb")
        ordered = sorted(queries, key=lambda query: (query.topic_id, query.persona_id, query.priority, query.query_id))
        self.assertNotEqual([], queries)
        self.assertEqual([query.query_id for query in queries], [query.query_id for query in generate_customer_voice_queries("ai_cfo_smb")])
        self.assertEqual([query.query_id for query in queries], [query.query_id for query in queries])
        self.assertEqual(len(ordered), len(queries))

    def test_prompt_contract_is_disabled_by_default_and_mentions_no_auto_activation(self) -> None:
        self.assertIn("disabled by default", CUSTOMER_VOICE_QUERY_PROMPT_CONTRACT)
        self.assertIn("never activate", CUSTOMER_VOICE_QUERY_PROMPT_CONTRACT)
        self.assertIn("approval_state=proposed", CUSTOMER_VOICE_QUERY_PROMPT_CONTRACT)

    def test_no_llm_network_calls_are_required(self) -> None:
        queries = generate_customer_voice_queries("ai_cfo_smb")
        self.assertTrue(queries)
        self.assertTrue(all(query.generation_method == GENERATION_METHOD_DETERMINISTIC_SEED for query in queries))

    def test_cli_preview_writes_json_and_markdown(self) -> None:
        output_json = (self.tmp_root / "customer_voice_queries.json").resolve()
        output_md = (self.tmp_root / "customer_voice_queries.md").resolve()
        exit_code = main(
            [
                "generate-customer-voice-queries",
                "--project-root",
                str(self.tmp_root),
                "--topic",
                "ai_cfo_smb",
                "--max-queries-per-persona",
                "3",
                "--output",
                str(output_json),
                "--output-md",
                str(output_md),
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue(output_json.exists())
        self.assertTrue(output_md.exists())
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        self.assertEqual(payload["topic_id"], "ai_cfo_smb")
        self.assertEqual(payload["query_kind"], QUERY_KIND_CUSTOMER_VOICE)
        self.assertEqual(len(payload["queries"]), 21)
        self.assertIn("# Customer Voice Queries", output_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
