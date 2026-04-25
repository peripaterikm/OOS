import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestContradictionDetectionAcceptance(unittest.TestCase):
    def test_contradiction_detection_module_has_no_live_llm_or_api_calls(self) -> None:
        source = (REPO_ROOT / "src" / "oos" / "contradiction_detection.py").read_text(encoding="utf-8")
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

    def test_contradiction_detection_is_not_wired_into_run_signal_batch(self) -> None:
        source = (REPO_ROOT / "src" / "oos" / "orchestrator.py").read_text(encoding="utf-8")
        forbidden_tokens = [
            "contradiction_detection",
            "detect_contradictions",
            "ContradictionReport",
            "ContradictionRecord",
            "MergeCandidate",
        ]

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_implementation_does_not_delete_or_auto_merge_source_signals(self) -> None:
        source = (REPO_ROOT / "src" / "oos" / "contradiction_detection.py").read_text(encoding="utf-8")
        forbidden_patterns = [
            r"\.unlink\s*\(",
            r"os\.remove\s*\(",
            r"shutil\.rmtree\s*\(",
            r"\.pop\s*\(",
            r"\.remove\s*\(",
            r"do_not_auto_merge\s*=\s*False",
        ]

        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, source))

    def test_active_roadmap_is_advanced_to_4_1(self) -> None:
        source = (REPO_ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_2_8_weeks_checklist.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("**0.2.2** Current item: **4.1**", source)
        self.assertIn("**0.2.4** Completed from this roadmap: **6 / 16**", source)
        self.assertIn("**0.2.5** Remaining: **10 / 16**", source)
        self.assertRegex(
            source,
            re.compile(
                r"## 3\.2\. Contradiction detection and merge candidates\s+"
                r"\*\*Status:\*\* \[ \] Not started  \[ \] In progress  \[ \] Blocked  \[x\] Done",
                re.MULTILINE,
            ),
        )
        self.assertIn("**9.3** Milestone C: AI semantic clustering operational after **3.2**", source)


if __name__ == "__main__":
    unittest.main()
