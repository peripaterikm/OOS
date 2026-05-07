from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from oos.weekly_run_manifest import (
    WEEKLY_RUN_MANIFEST_SCHEMA_VERSION,
    WeeklyRunManifest,
    canonical_artifact_paths,
    canonical_artifact_schema_versions,
    default_empty_states,
    generate_weekly_run_id,
    make_default_manifest,
    read_weekly_run_manifest,
    write_weekly_run_manifest,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _fixture_input_bytes() -> bytes:
    return b'{"signals":[{"id":"s1","title":"test"}]}'


# ---------------------------------------------------------------------------
# Run ID generation
# ---------------------------------------------------------------------------


class TestGenerateWeeklyRunId(unittest.TestCase):
    def test_deterministic_same_input_same_date(self) -> None:
        a = generate_weekly_run_id(date(2026, 5, 7), _fixture_input_bytes())
        b = generate_weekly_run_id(date(2026, 5, 7), _fixture_input_bytes())
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("weekly_run_2026-05-07_"))
        self.assertEqual(len(a), len("weekly_run_YYYY-MM-DD_") + 12)

    def test_different_date_produces_different_id(self) -> None:
        a = generate_weekly_run_id(date(2026, 5, 7), _fixture_input_bytes())
        b = generate_weekly_run_id(date(2026, 5, 8), _fixture_input_bytes())
        self.assertNotEqual(a, b)

    def test_different_input_produces_different_id(self) -> None:
        a = generate_weekly_run_id(date(2026, 5, 7), b"input-a")
        b = generate_weekly_run_id(date(2026, 5, 7), b"input-b")
        self.assertNotEqual(a, b)

    def test_rejects_non_date(self) -> None:
        with self.assertRaises(TypeError):
            generate_weekly_run_id("2026-05-07", _fixture_input_bytes())  # type: ignore[arg-type]

    def test_rejects_empty_bytes(self) -> None:
        with self.assertRaises(ValueError):
            generate_weekly_run_id(date(2026, 5, 7), b"")


# ---------------------------------------------------------------------------
# WeeklyRunManifest model
# ---------------------------------------------------------------------------


class TestWeeklyRunManifestModel(unittest.TestCase):
    def test_minimal_manifest_valid(self) -> None:
        m = make_default_manifest(
            "weekly_run_2026-05-07_abc123",
            "2026-05-07T10:00:00+00:00",
        )
        self.assertTrue(m.is_valid())
        self.assertEqual(m.run_id, "weekly_run_2026-05-07_abc123")
        self.assertEqual(m.schema_version, WEEKLY_RUN_MANIFEST_SCHEMA_VERSION)

    def test_to_dict_has_deterministic_key_order(self) -> None:
        m = make_default_manifest(
            "weekly_run_2026-05-07_abc123",
            "2026-05-07T10:00:00+00:00",
        )
        d = m.to_dict()
        # Top-level keys in expected order
        top_keys = list(d.keys())
        self.assertEqual(
            top_keys,
            [
                "run_id",
                "created_at",
                "schema_version",
                "artifact_paths",
                "artifact_schema_versions",
                "empty_states",
                "input_file",
                "input_signal_count",
                "advisory_only",
                "no_live_api",
                "no_live_llm",
            ],
        )
        # artifact_paths keys in canonical order
        ap_keys = list(d["artifact_paths"].keys())
        self.assertIn("manifest", ap_keys)
        self.assertIn("evidence_packs", ap_keys)
        self.assertIn("run_report_md", ap_keys)

    def test_from_dict_roundtrip(self) -> None:
        m1 = make_default_manifest(
            "weekly_run_2026-05-07_def456",
            "2026-05-07T11:00:00+00:00",
            input_file="examples/signals.jsonl",
            input_signal_count=42,
        )
        m2 = WeeklyRunManifest.from_dict(m1.to_dict())
        self.assertEqual(m1, m2)

    def test_json_roundtrip_stable(self) -> None:
        m1 = make_default_manifest(
            "weekly_run_2026-05-07_def456",
            "2026-05-07T11:00:00+00:00",
            input_file="examples/signals.jsonl",
            input_signal_count=7,
        )
        payload = m1.to_dict()
        json_str_a = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        json_str_b = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        self.assertEqual(json_str_a, json_str_b)
        # parse back
        m2 = WeeklyRunManifest.from_dict(json.loads(json_str_a))
        self.assertEqual(m1, m2)

    def test_artifact_keys_in_canonical_order(self) -> None:
        m = make_default_manifest("r1", "2026-05-07T10:00:00Z")
        keys = m.artifact_keys()
        self.assertIn("manifest", keys)
        self.assertIn("run_report_md", keys)
        # verify no extra/missing standard keys
        self.assertEqual(len(keys), 14)

    def test_empty_states_default_all_true(self) -> None:
        states = default_empty_states()
        self.assertEqual(len(states), 14)
        self.assertTrue(all(states.values()))

    def test_canonical_artifact_paths_all_relative(self) -> None:
        paths = canonical_artifact_paths()
        for key, path in paths.items():
            self.assertFalse(Path(path).is_absolute(), f"{key} path is absolute")
            self.assertNotIn("..", path, f"{key} path contains '..'")

    def test_canonical_schema_versions_all_known(self) -> None:
        versions = canonical_artifact_schema_versions()
        self.assertEqual(len(versions), 14)
        for key, ver in versions.items():
            self.assertTrue(
                isinstance(ver, str) and ver.strip(),
                f"schema version for {key} is invalid: {ver!r}",
            )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestWeeklyRunManifestValidation(unittest.TestCase):
    def _valid_manifest(self) -> WeeklyRunManifest:
        return make_default_manifest(
            "weekly_run_2026-05-07_xyz",
            "2026-05-07T12:00:00+00:00",
        )

    def test_valid_passes(self) -> None:
        m = self._valid_manifest()
        self.assertEqual(m.validate(), [])

    def test_missing_run_id(self) -> None:
        m = WeeklyRunManifest(run_id="", created_at="t", empty_states={"manifest": True})
        errors = m.validate()
        self.assertTrue(any("run_id" in e for e in errors))

    def test_unknown_artifact_key_in_paths(self) -> None:
        m = self._valid_manifest()
        m = WeeklyRunManifest(
            run_id=m.run_id,
            created_at=m.created_at,
            artifact_paths={**m.artifact_paths, "unknown_key": "x.json"},
            artifact_schema_versions=m.artifact_schema_versions,
            empty_states=m.empty_states,
        )
        errors = m.validate()
        self.assertTrue(any("unknown_key" in e for e in errors))

    def test_unknown_schema_version(self) -> None:
        m = self._valid_manifest()
        m = WeeklyRunManifest(
            run_id=m.run_id,
            created_at=m.created_at,
            artifact_paths=m.artifact_paths,
            artifact_schema_versions={**m.artifact_schema_versions, "manifest": "unknown.v9"},
            empty_states=m.empty_states,
        )
        errors = m.validate()
        self.assertTrue(any("unknown.v9" in e for e in errors))

    def test_path_traversal_rejected(self) -> None:
        m = self._valid_manifest()
        m = WeeklyRunManifest(
            run_id=m.run_id,
            created_at=m.created_at,
            artifact_paths={**m.artifact_paths, "manifest": "../evil/manifest.json"},
            artifact_schema_versions=m.artifact_schema_versions,
            empty_states=m.empty_states,
        )
        errors = m.validate()
        self.assertTrue(any(".." in e for e in errors))

    def test_absolute_path_rejected(self) -> None:
        m = self._valid_manifest()
        m = WeeklyRunManifest(
            run_id=m.run_id,
            created_at=m.created_at,
            artifact_paths={**m.artifact_paths, "manifest": "C:\\absolute\\manifest.json"},
            artifact_schema_versions=m.artifact_schema_versions,
            empty_states=m.empty_states,
        )
        errors = m.validate()
        self.assertTrue(any("relative" in e.lower() for e in errors))

    def test_missing_manifest_entry_rejected(self) -> None:
        m = self._valid_manifest()
        bad_paths = {k: v for k, v in m.artifact_paths.items() if k != "manifest"}
        m = WeeklyRunManifest(
            run_id=m.run_id,
            created_at=m.created_at,
            artifact_paths=bad_paths,
            artifact_schema_versions=m.artifact_schema_versions,
            empty_states=m.empty_states,
        )
        errors = m.validate()
        self.assertTrue(any("manifest" in e for e in errors))

    def test_advisory_only_false_rejected(self) -> None:
        m = self._valid_manifest()
        m = WeeklyRunManifest(
            run_id=m.run_id,
            created_at=m.created_at,
            artifact_paths=m.artifact_paths,
            artifact_schema_versions=m.artifact_schema_versions,
            empty_states=m.empty_states,
            advisory_only=False,
        )
        errors = m.validate()
        self.assertTrue(any("advisory_only" in e for e in errors))

    def test_no_live_api_false_rejected(self) -> None:
        m = self._valid_manifest()
        m = WeeklyRunManifest(
            run_id=m.run_id,
            created_at=m.created_at,
            artifact_paths=m.artifact_paths,
            artifact_schema_versions=m.artifact_schema_versions,
            empty_states=m.empty_states,
            no_live_api=False,
        )
        errors = m.validate()
        self.assertTrue(any("no_live_api" in e for e in errors))

    def test_no_live_llm_false_rejected(self) -> None:
        m = self._valid_manifest()
        m = WeeklyRunManifest(
            run_id=m.run_id,
            created_at=m.created_at,
            artifact_paths=m.artifact_paths,
            artifact_schema_versions=m.artifact_schema_versions,
            empty_states=m.empty_states,
            no_live_llm=False,
        )
        errors = m.validate()
        self.assertTrue(any("no_live_llm" in e for e in errors))

    def test_unknown_empty_state_key_rejected(self) -> None:
        m = self._valid_manifest()
        m = WeeklyRunManifest(
            run_id=m.run_id,
            created_at=m.created_at,
            artifact_paths=m.artifact_paths,
            artifact_schema_versions=m.artifact_schema_versions,
            empty_states={**m.empty_states, "bogus": True},
        )
        errors = m.validate()
        self.assertTrue(any("bogus" in e for e in errors))

    def test_wrong_schema_version_rejected(self) -> None:
        m = WeeklyRunManifest(
            run_id="r1",
            created_at="t",
            schema_version="wrong.v0",
            empty_states={"manifest": True},
        )
        errors = m.validate()
        self.assertTrue(any(WEEKLY_RUN_MANIFEST_SCHEMA_VERSION in e for e in errors))


# ---------------------------------------------------------------------------
# Empty-state manifest
# ---------------------------------------------------------------------------


class TestEmptyStateManifest(unittest.TestCase):
    def test_empty_state_produces_valid_manifest(self) -> None:
        m = make_default_manifest(
            "weekly_run_2026-05-07_empty",
            "2026-05-07T09:00:00+00:00",
        )
        self.assertTrue(m.is_valid())
        self.assertTrue(all(m.empty_states.values()))
        self.assertEqual(len(m.empty_states), 14)

    def test_empty_state_all_flags_true(self) -> None:
        m = make_default_manifest("r1", "t")
        for key in m.empty_states:
            self.assertTrue(
                m.empty_states[key],
                f"empty_states['{key}'] should be True for default empty manifest",
            )


# ---------------------------------------------------------------------------
# write / read manifest.json roundtrip
# ---------------------------------------------------------------------------


class TestWriteReadManifest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="oos_test_wrm_")
        self.run_dir = Path(self.tmpdir.name) / "weekly_run_test"

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_write_and_read_roundtrip(self) -> None:
        m1 = make_default_manifest(
            "weekly_run_2026-05-07_roundtrip",
            "2026-05-07T08:00:00+00:00",
            input_file="fixtures/test.jsonl",
            input_signal_count=5,
        )
        write_weekly_run_manifest(self.run_dir, m1)
        manifest_path = self.run_dir / "manifest.json"
        self.assertTrue(manifest_path.is_file())

        m2 = read_weekly_run_manifest(self.run_dir)
        self.assertEqual(m1, m2)

    def test_read_missing_manifest_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            read_weekly_run_manifest(self.run_dir)

    def test_read_invalid_json_raises(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "manifest.json").write_text("not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            read_weekly_run_manifest(self.run_dir)

    def test_read_invalid_manifest_content_raises(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        invalid = {"artifact_paths": {"manifest": "../etc/passwd"}}
        (self.run_dir / "manifest.json").write_text(
            json.dumps(invalid), encoding="utf-8"
        )
        with self.assertRaises(ValueError):
            read_weekly_run_manifest(self.run_dir)

    def test_write_invalid_manifest_raises(self) -> None:
        m = WeeklyRunManifest(run_id="", created_at="", empty_states={"manifest": True})
        with self.assertRaises(ValueError):
            write_weekly_run_manifest(self.run_dir, m)

    def test_read_rejects_path_traversal(self) -> None:
        # Craft a manifest that points a path outside the run dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        m = make_default_manifest(
            "weekly_run_2026-05-07_evil",
            "2026-05-07T09:00:00+00:00",
        )
        # Write it normally first
        write_weekly_run_manifest(self.run_dir, m)
        # Now corrupt the manifest.json to have an absolute path for evidence_packs
        manifest_path = self.run_dir / "manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["artifact_paths"]["evidence_packs"] = "C:\\windows\\temp\\evil.json"
        manifest_path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            read_weekly_run_manifest(self.run_dir)

    def test_full_artifact_path_fixture_roundtrip(self) -> None:
        """Round-trip a manifest with all 14 artifact paths (excluding manifest itself from count)."""
        m1 = make_default_manifest(
            "weekly_run_2026-05-07_full",
            "2026-05-07T10:00:00+00:00",
            input_file="examples/real_signal_batch.jsonl",
            input_signal_count=23,
        )
        # Mark some artifacts as non-empty for realism
        m1 = WeeklyRunManifest(
            run_id=m1.run_id,
            created_at=m1.created_at,
            artifact_paths=m1.artifact_paths,
            artifact_schema_versions=m1.artifact_schema_versions,
            empty_states={
                "manifest": False,
                "evidence_packs": False,
                "opportunity_candidates": False,
                "quality_gate_decisions": False,
                "founder_decisions_v2": True,
                "founder_feedback_mappings": True,
                "founder_preference_profile": True,
                "weekly_opportunity_review": False,
                "next_best_actions": False,
                "parking_lot_records": True,
                "run_report": False,
                "founder_inbox_v2_index": False,
                "founder_inbox_v2_md": False,
                "run_report_md": False,
            },
            input_file=m1.input_file,
            input_signal_count=m1.input_signal_count,
        )
        write_weekly_run_manifest(self.run_dir, m1)
        m2 = read_weekly_run_manifest(self.run_dir)
        self.assertEqual(m1, m2)

        # 14 artifact paths total in manifest (all canonical keys present)
        self.assertEqual(len(m2.artifact_paths), 14)
        # manifest.json is included in artifact_paths but counted separately
        self.assertIn("manifest", m2.artifact_paths)
        # Verify specific paths expected by the contract
        self.assertEqual(m2.artifact_paths["evidence_packs"], "evidence_packs.json")
        self.assertEqual(m2.artifact_paths["opportunity_candidates"], "opportunity_candidates.json")
        self.assertEqual(m2.artifact_paths["founder_inbox_v2_md"], "founder_inbox_v2.md")
        self.assertEqual(m2.artifact_paths["founder_inbox_v2_index"], "founder_inbox_v2_index.json")
        self.assertEqual(m2.artifact_paths["run_report_md"], "run_report.md")

    def test_write_creates_directory_if_missing(self) -> None:
        nested = self.run_dir / "nested" / "deep"
        m = make_default_manifest("r1", "t")
        write_weekly_run_manifest(nested, m)
        self.assertTrue((nested / "manifest.json").is_file())

    def test_no_artifacts_written_outside_tempdir(self) -> None:
        """Guard: write must only touch the designated run_dir."""
        before = set(Path(self.tmpdir.name).rglob("*"))
        m = make_default_manifest("r_safe", "2026-05-07T12:00:00Z")
        write_weekly_run_manifest(self.run_dir, m)
        after = set(Path(self.tmpdir.name).rglob("*"))
        new_paths = after - before
        self.assertTrue(
            all(str(p).startswith(str(self.run_dir.resolve())) for p in new_paths),
            "write_weekly_run_manifest wrote files outside the run directory",
        )


# ---------------------------------------------------------------------------
# Traceability metadata
# ---------------------------------------------------------------------------


class TestTraceabilityMetadata(unittest.TestCase):
    def test_manifest_includes_input_file_traceability(self) -> None:
        m = make_default_manifest(
            "weekly_run_2026-05-07_trace",
            "2026-05-07T09:00:00+00:00",
            input_file="examples/fixture_batch.jsonl",
            input_signal_count=10,
        )
        self.assertEqual(m.input_file, "examples/fixture_batch.jsonl")
        self.assertEqual(m.input_signal_count, 10)

    def test_manifest_has_advisory_and_no_live_flags(self) -> None:
        m = make_default_manifest("r1", "t")
        self.assertTrue(m.advisory_only)
        self.assertTrue(m.no_live_api)
        self.assertTrue(m.no_live_llm)

    def test_to_dict_includes_traceability_flags(self) -> None:
        m = make_default_manifest("r1", "t")
        d = m.to_dict()
        self.assertTrue(d["advisory_only"])
        self.assertTrue(d["no_live_api"])
        self.assertTrue(d["no_live_llm"])


if __name__ == "__main__":
    unittest.main()
