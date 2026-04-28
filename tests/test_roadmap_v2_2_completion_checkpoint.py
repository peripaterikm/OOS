from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROADMAP_PATH = ROOT / "docs" / "roadmaps" / "OOS_roadmap_v2_2_8_weeks_checklist.md"
CHECKPOINT_PATH = ROOT / "docs" / "dev_ledger" / "03_run_reports" / "roadmap-v2-2-completion-checkpoint.md"
PROJECT_STATE_PATH = ROOT / "docs" / "dev_ledger" / "00_project_state.md"
MINI_EPIC_PATH = ROOT / "docs" / "dev_ledger" / "02_mini_epics" / "8.2-roadmap-v2-2-completion-checkpoint.md"


class TestRoadmapV22CompletionCheckpoint(unittest.TestCase):
    def test_completion_checkpoint_document_exists_with_required_sections(self) -> None:
        self.assertTrue(CHECKPOINT_PATH.exists())
        checkpoint = CHECKPOINT_PATH.read_text(encoding="utf-8")

        self.assertIn("Part 1 - Founder-Written Narrative", checkpoint)
        self.assertIn("Part 2 - System-Generated Report", checkpoint)
        self.assertIn("Actual LLM/API Call Counts", checkpoint)
        self.assertIn("Latency Profile From Local Validation", checkpoint)
        self.assertIn("Quality Findings From Evaluation Dataset", checkpoint)
        self.assertIn("Fallback And Failure Summary", checkpoint)

    def test_checkpoint_documents_no_push_merge_tag_or_live_api_calls(self) -> None:
        checkpoint = CHECKPOINT_PATH.read_text(encoding="utf-8")

        self.assertIn("Live LLM/API calls made during Roadmap v2.2 completion: `0`", checkpoint)
        self.assertIn("Push performed: `no`", checkpoint)
        self.assertIn("Merge performed: `no`", checkpoint)
        self.assertIn("Tag created: `no`", checkpoint)
        self.assertIn("roadmap-v2.2-complete", checkpoint)

    def test_active_roadmap_is_8_2_in_progress_or_complete_without_side_effects(self) -> None:
        roadmap = ROADMAP_PATH.read_text(encoding="utf-8")

        self.assertRegex(roadmap, r"\*\*0\.2\.2\*\* Current item: \*\*(8\.2|Completed / final milestone state)\*\*")
        self.assertRegex(roadmap, r"\*\*0\.2\.4\*\* Completed from this roadmap: \*\*(15|16) / 16\*\*")
        self.assertRegex(roadmap, r"\*\*0\.2\.5\*\* Remaining: \*\*(1|0) / 16\*\*")
        self.assertIn("## 8.2. Roadmap v2.2 completion checkpoint", roadmap)
        if "Current item: **Completed / final milestone state**" in roadmap:
            self.assertRegex(
                roadmap,
                re.compile(
                    r"## 8\.2\. Roadmap v2\.2 completion checkpoint\s+"
                    r"\*\*Status:\*\* \[ \] Not started  \[ \] In progress  \[ \] Blocked  \[x\] Done",
                    re.MULTILINE,
                ),
            )
            self.assertIn("Tag target documented; actual tag deferred", roadmap)
            self.assertIn("Main branch merge deferred", roadmap)
        self.assertIn("**9.8** Milestone H: Roadmap v2.2 complete after **8.2**", roadmap)

    def test_dev_ledger_final_state_and_record_exist(self) -> None:
        self.assertTrue(MINI_EPIC_PATH.exists())
        state = PROJECT_STATE_PATH.read_text(encoding="utf-8")

        self.assertRegex(state, r"Roadmap v2\.2 status: complete|Current item: `(8\.2|Completed / final milestone state)`")
        self.assertRegex(state, r"Completed: `(15|16|0|1|2|3|4|5|6|7|8|9|10|11) / 16`")
        self.assertRegex(state, r"Remaining: `(1|0|16|15|14|13|12|11|10|9|8|7|6|5) / 16`")
        self.assertRegex(state, r"Latest completed roadmap item: (Roadmap v2\.(2|3) )?`?(8\.1|8\.2|1\.1|1\.2|2\.1|2\.2|3\.1|4\.1|4\.2|4\.3|5\.1|5\.2|6\.2-lite)`?")


if __name__ == "__main__":
    unittest.main()
