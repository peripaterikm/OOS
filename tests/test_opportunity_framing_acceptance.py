import re
import unittest
from dataclasses import asdict
from pathlib import Path

from oos.opportunity_framing import StaticOpportunityFramingProvider, frame_opportunities
from tests.test_opportunity_framing import make_cluster, valid_opportunity
from tests.test_semantic_clustering import make_signal


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestOpportunityFramingAcceptance(unittest.TestCase):
    def test_opportunity_framing_module_has_no_live_llm_or_api_calls(self) -> None:
        source = (REPO_ROOT / "src" / "oos" / "opportunity_framing.py").read_text(encoding="utf-8")
        forbidden_tokens = [
            "OpenAI(",
            "Anthropic(",
            "requests.post",
            "httpx.post",
            "chat.completions",
            "responses.create",
        ]

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_opportunity_framing_is_not_wired_into_run_signal_batch(self) -> None:
        source = (REPO_ROOT / "src" / "oos" / "orchestrator.py").read_text(encoding="utf-8")
        forbidden_tokens = [
            "opportunity_framing",
            "frame_opportunities",
            "OpportunityFramingResult",
        ]

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_source_signals_and_clusters_are_not_deleted_or_mutated(self) -> None:
        signals = [make_signal("sig_1"), make_signal("sig_2")]
        cluster = make_cluster()
        original_signals = [asdict(signal) for signal in signals]
        original_cluster = cluster.to_dict()

        result = frame_opportunities(
            clusters=[cluster],
            signals=signals,
            provider=StaticOpportunityFramingProvider(payload={"opportunities": [valid_opportunity()]}),
        )

        self.assertFalse(result.fallback_used)
        self.assertEqual([asdict(signal) for signal in signals], original_signals)
        self.assertEqual(cluster.to_dict(), original_cluster)
        self.assertEqual(result.source_signal_ids, ["sig_1", "sig_2"])
        self.assertEqual(result.source_cluster_ids, ["cluster_ops"])

    def test_active_roadmap_is_advanced_to_4_2(self) -> None:
        source = (REPO_ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_2_8_weeks_checklist.md").read_text(
            encoding="utf-8"
        )

        current_item = re.search(r"\*\*0\.2\.2\*\* Current item: \*\*(\d+\.\d+|Completed / final milestone state)\*\*", source)
        completed = re.search(r"\*\*0\.2\.4\*\* Completed from this roadmap: \*\*(\d+) / 16\*\*", source)
        remaining = re.search(r"\*\*0\.2\.5\*\* Remaining: \*\*(\d+) / 16\*\*", source)

        self.assertIsNotNone(current_item)
        self.assertIsNotNone(completed)
        self.assertIsNotNone(remaining)
        if current_item.group(1) != "Completed / final milestone state":
            self.assertGreaterEqual(tuple(map(int, current_item.group(1).split("."))), (4, 2))
        self.assertGreaterEqual(int(completed.group(1)), 7)
        self.assertLessEqual(int(remaining.group(1)), 9)
        self.assertRegex(
            source,
            re.compile(
                r"## 4\.1\. LLM opportunity cards with defined non-obvious angle\s+"
                r"\*\*Status:\*\* \[ \] Not started  \[ \] In progress  \[ \] Blocked  \[x\] Done",
                re.MULTILINE,
            ),
        )


if __name__ == "__main__":
    unittest.main()
