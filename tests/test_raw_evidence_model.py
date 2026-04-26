import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oos.artifact_store import ArtifactStore
from oos.models import (
    RawEvidence,
    author_or_context_is_private_safe,
    compute_raw_evidence_content_hash,
    model_from_dict,
)


def make_raw_evidence(**overrides: object) -> RawEvidence:
    title = str(overrides.get("title", "Manual invoice reconciliation is painful"))
    body = str(
        overrides.get(
            "body",
            "I spend two hours every Friday copying bank exports into a spreadsheet before closing books.",
        )
    )
    values = {
        "evidence_id": "raw_ev_1",
        "source_id": "hacker_news_algolia",
        "source_type": "public_api",
        "source_name": "Hacker News Algolia",
        "source_url": "https://news.ycombinator.com/item?id=123",
        "collected_at": "2026-04-26T10:00:00+00:00",
        "title": title,
        "body": body,
        "language": "en",
        "topic_id": "ai_cfo_smb",
        "query_kind": "pain_search",
        "content_hash": compute_raw_evidence_content_hash(title=title, body=body),
        "author_or_context": "SMB owner",
        "raw_metadata": {"points": 42, "tags": ["fixture", "offline"]},
        "access_policy": "fixture_offline_first",
        "collection_method": "fixture",
    }
    values.update(overrides)
    return RawEvidence(**values)


class TestRawEvidenceModel(unittest.TestCase):
    def test_raw_evidence_can_be_created_with_required_fields(self) -> None:
        evidence = make_raw_evidence()

        evidence.validate()

        self.assertEqual(evidence.evidence_id, "raw_ev_1")
        self.assertEqual(evidence.id, "raw_ev_1")

    def test_missing_required_fields_are_rejected(self) -> None:
        payload = make_raw_evidence().__dict__.copy()
        del payload["source_url"]

        with self.assertRaises(TypeError):
            RawEvidence(**payload)

        with self.assertRaisesRegex(ValueError, "RawEvidence.source_url"):
            make_raw_evidence(source_url="").validate()

    def test_round_trips_through_artifact_store(self) -> None:
        with TemporaryDirectory() as tmp:
            store = ArtifactStore(root_dir=Path(tmp) / "artifacts")
            evidence = make_raw_evidence()

            ref = store.write_model(evidence)
            loaded = store.read_model(RawEvidence, "raw_ev_1")

            self.assertEqual(ref.kind, "raw_evidence")
            self.assertEqual(ref.path, Path(tmp) / "artifacts" / "raw_evidence" / "raw_ev_1.json")
            self.assertEqual(loaded, evidence)

    def test_source_url_is_preserved(self) -> None:
        with TemporaryDirectory() as tmp:
            source_url = "https://example.com/questions/123?sort=active#answer-456"
            store = ArtifactStore(root_dir=Path(tmp) / "artifacts")
            store.write_model(make_raw_evidence(source_url=source_url))

            payload = json.loads((Path(tmp) / "artifacts" / "raw_evidence" / "raw_ev_1.json").read_text())

            self.assertEqual(payload["source_url"], source_url)

    def test_content_hash_is_deterministic_for_normalized_content(self) -> None:
        first = compute_raw_evidence_content_hash(
            title="Manual   invoice reconciliation",
            body="Copying\n\nbank exports\tinto sheets",
        )
        second = compute_raw_evidence_content_hash(
            title=" Manual invoice reconciliation ",
            body="Copying bank exports into sheets",
        )

        self.assertEqual(first, second)
        with self.assertRaisesRegex(ValueError, "content_hash"):
            make_raw_evidence(content_hash="not-the-normalized-hash").validate()

    def test_raw_metadata_survives_serialization(self) -> None:
        metadata = {
            "source_item_id": 123,
            "nested": {"score": 7, "labels": ["pain", "workflow"]},
            "nullable": None,
        }
        with TemporaryDirectory() as tmp:
            store = ArtifactStore(root_dir=Path(tmp) / "artifacts")
            store.write_model(make_raw_evidence(raw_metadata=metadata))

            loaded = store.read_model(RawEvidence, "raw_ev_1")

            self.assertEqual(loaded.raw_metadata, metadata)

    def test_author_or_context_privacy_rule(self) -> None:
        for context in ("SMB owner", "developer", "founder", "unverified public commenter"):
            self.assertTrue(author_or_context_is_private_safe(context))
            make_raw_evidence(author_or_context=context).validate()

        for handle in ("@direct_handle", "u/direct_handle", "username: direct_handle"):
            self.assertFalse(author_or_context_is_private_safe(handle))
            with self.assertRaisesRegex(ValueError, "author_or_context"):
                make_raw_evidence(author_or_context=handle).validate()

    def test_no_network_api_or_llm_calls_required(self) -> None:
        evidence = model_from_dict(RawEvidence, make_raw_evidence().__dict__)

        self.assertEqual(evidence.collection_method, "fixture")
        self.assertEqual(evidence.access_policy, "fixture_offline_first")


if __name__ == "__main__":
    unittest.main()
