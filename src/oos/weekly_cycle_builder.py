"""Unified weekly cycle builder — deterministic orchestrator for v2.6 weekly runs.

Orchestrates the full v2.5 pipeline (evidence packs → opportunity candidates →
quality gates → founder decisions/feedback/profile → weekly review → next-best
actions → parking lot) into one deterministic pass, writing all 13 builder-written
artifacts defined by the WeeklyRunManifest contract.

No live LLM/API calls. No autonomous portfolio transitions. Advisory-only.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from oos.founder_inbox_v2 import (
    build_founder_inbox_v2,
    founder_inbox_v2_to_json,
    render_founder_inbox_v2_markdown,
)
from oos.weekly_run_reports import (
    build_weekly_run_report,
    render_weekly_run_report_markdown,
    write_weekly_run_report,
)
from oos.evidence_pack import (
    EvidencePack,
    EvidencePackItem,
    EvidencePackSourceSummary,
    evidence_pack_from_dict,
    evidence_pack_to_dict,
    make_evidence_pack_id,
)
from oos.founder_decision_taxonomy import (
    FounderDecisionV2,
    founder_decision_to_dict,
)
from oos.founder_feedback_mapping import (
    FounderFeedbackMapping,
    founder_feedback_mapping_to_dict,
)
from oos.founder_preference_profile import (
    FounderPreferenceProfile,
    build_founder_preference_profile,
    founder_preference_profile_to_dict,
)
from oos.next_best_founder_actions import (
    FounderAction,
    build_next_best_founder_actions,
    next_best_actions_to_json,
)
from oos.opportunity_quality_gate import (
    OpportunityGateResult,
    evaluate_opportunity_quality,
)
from oos.opportunity_sketch import (
    OpportunityCandidate,
    build_opportunity_sketch_from_evidence_pack,
    opportunity_sketch_to_dict,
)
from oos.parking_lot import (
    ParkingLotRecord,
    RevisitMatch,
    build_parking_lot_records,
    match_revisit_candidates,
    parking_lot_records_to_json,
)
from oos.weekly_opportunity_review import (
    WeeklyOpportunityReviewPackage,
    build_weekly_opportunity_review_package,
    weekly_review_package_to_json,
)
from oos.weekly_run_manifest import (
    canonical_artifact_paths,
    canonical_artifact_schema_versions,
    default_empty_states,
    generate_weekly_run_id,
    make_default_manifest,
    write_weekly_run_manifest,
)

WEEKLY_CYCLE_BUILDER_VERSION = "weekly_cycle_builder.v1"
SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


# ---------------------------------------------------------------------------
# Build result model
# ---------------------------------------------------------------------------


@dataclass
class WeeklyCycleBuildResult:
    """Result object returned by build_weekly_cycle()."""

    run_id: str
    run_dir: str
    manifest_path: str
    artifacts_written: list[str] = field(default_factory=list)
    artifact_count: int = 0
    empty_states: dict[str, bool] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True
    validation_passed: bool = False
    pipeline_summary: dict[str, Any] = field(default_factory=dict)
    schema_version: str = WEEKLY_CYCLE_BUILDER_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_dir": self.run_dir,
            "manifest_path": self.manifest_path,
            "artifacts_written": list(self.artifacts_written),
            "artifact_count": self.artifact_count,
            "empty_states": dict(self.empty_states),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
            "validation_passed": self.validation_passed,
            "pipeline_summary": dict(self.pipeline_summary),
            "schema_version": self.schema_version,
        }


# ---------------------------------------------------------------------------
# Helper: read input file
# ---------------------------------------------------------------------------


def _read_input_signals(input_file: Path) -> list[dict[str, Any]]:
    """Read signal/case dicts from a JSONL or JSON file.

    Returns a list of dicts. Supports:
    - JSONL (one JSON object per line)
    - JSON array (single array of objects)

    Empty input returns empty list.
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    raw = input_file.read_text(encoding="utf-8-sig")
    stripped = raw.strip()

    if not stripped:
        return []

    # Try JSON array first
    try:
        data = json.loads(stripped)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    # Try JSONL (one object per line)
    items: list[dict[str, Any]] = []
    for line_number, line in enumerate(stripped.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at line {line_number}: {exc.msg}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"Invalid JSONL at line {line_number}: expected object")
        items.append(obj)

    return items


def _compute_input_content_hash(input_file: Path) -> bytes:
    """Read input file bytes for deterministic run ID generation."""
    return input_file.read_bytes()


def _validate_run_id(run_id: str, weekly_runs_root: Path) -> str:
    """Validate *run_id* as one safe directory name below weekly_runs_root."""
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id must be a non-empty string")
    safe_run_id = run_id.strip()
    if safe_run_id in {".", ".."}:
        raise ValueError("run_id must not be '.' or '..'")
    if "/" in safe_run_id or "\\" in safe_run_id:
        raise ValueError("run_id must not contain path separators")
    if ":" in safe_run_id:
        raise ValueError("run_id must not contain drive or scheme separators")
    if not SAFE_RUN_ID_RE.fullmatch(safe_run_id):
        raise ValueError("run_id may contain only letters, digits, underscore, hyphen, and dot")
    candidate = (weekly_runs_root / safe_run_id).resolve()
    root = weekly_runs_root.resolve()
    if candidate.parent != root:
        raise ValueError("run_id resolves outside artifacts/weekly_runs")
    return safe_run_id


def _format_generated_at(generated_at: datetime | str | None) -> str:
    if generated_at is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(generated_at, datetime):
        resolved = generated_at
        if resolved.tzinfo is None:
            resolved = resolved.replace(tzinfo=timezone.utc)
        return resolved.isoformat()
    if isinstance(generated_at, str) and generated_at.strip():
        return generated_at
    raise ValueError("generated_at must be a non-empty ISO timestamp string or datetime")


# ---------------------------------------------------------------------------
# Input normalization: evaluation dataset format -> EvidencePack objects
# ---------------------------------------------------------------------------


def _evidence_packs_from_input(items: list[dict[str, Any]]) -> list[EvidencePack]:
    """Build EvidencePack objects from input items.

    Supports two input formats:
    1. Evaluation dataset format: items with evidence_pack already built
       (key: ``input_artifacts.evidence_pack`` or ``evidence_pack``)
    2. Direct EvidencePack dicts

    Does NOT construct CandidateSignal intermediate objects.
    """
    packs: list[EvidencePack] = []

    for item in items:
        # Direct evidence pack (evaluation dataset format)
        ep_data = item.get("input_artifacts", {}).get("evidence_pack") or item.get("evidence_pack")
        if ep_data and isinstance(ep_data, dict):
            try:
                pack = evidence_pack_from_dict(ep_data)
                packs.append(pack)
            except (ValueError, TypeError):
                continue
            continue

        # Try to parse the item itself as an EvidencePack
        if "evidence_pack_id" in item and "cluster_id" in item and "items" in item:
            try:
                pack = evidence_pack_from_dict(item)
                packs.append(pack)
            except (ValueError, TypeError):
                continue

    # Deduplicate by evidence_pack_id
    seen: set[str] = set()
    unique: list[EvidencePack] = []
    for pack in packs:
        if pack.evidence_pack_id not in seen:
            seen.add(pack.evidence_pack_id)
            unique.append(pack)

    return sorted(unique, key=lambda p: p.evidence_pack_id)


def _evidence_pack_from_canonical_signal(item: dict[str, Any]) -> EvidencePack | None:
    """Convert the documented real signal-batch record into one EvidencePack."""
    signal_id = str(item.get("signal_id", "")).strip()
    title = str(item.get("title", "")).strip()
    text = str(item.get("text", "")).strip()
    source_type = str(item.get("source_type", "")).strip()
    source_ref = str(item.get("source_ref") or item.get("source_url") or "").strip()
    if not all((signal_id, title, text, source_type, source_ref)):
        return None

    cluster_id = f"cluster_{signal_id}"
    evidence_id = f"evidence_{signal_id}"
    summary = f"{title}: {text}"
    pack = EvidencePack(
        evidence_pack_id=make_evidence_pack_id(cluster_id),
        cluster_id=cluster_id,
        source_signal_ids=[signal_id],
        evidence_ids=[evidence_id],
        source_urls=[source_ref],
        summaries=[summary],
        source_types=[source_type],
        topic_id="real_signal_batch",
        confidence_values=[0.7],
        source_diversity=1,
        recurrence_count=1,
        created_from="canonical_signal_batch",
        items=[
            EvidencePackItem(
                evidence_id=evidence_id,
                source_signal_id=signal_id,
                source_url=source_ref,
                source_type=source_type,
                summary=summary,
                confidence=0.7,
            )
        ],
        source_summaries=[
            EvidencePackSourceSummary(
                source_type=source_type,
                source_count=1,
                evidence_ids=[evidence_id],
            )
        ],
    )
    pack.validate()
    return pack


def _canonical_signal_packs_from_input(items: list[dict[str, Any]]) -> tuple[list[EvidencePack], list[str]]:
    packs: list[EvidencePack] = []
    errors: list[str] = []
    for index, item in enumerate(items, start=1):
        try:
            pack = _evidence_pack_from_canonical_signal(item)
        except (ValueError, TypeError) as exc:
            errors.append(f"Canonical signal at index {index} is invalid: {exc}")
            continue
        if pack is not None:
            packs.append(pack)
    return sorted(packs, key=lambda pack: pack.evidence_pack_id), errors


# ---------------------------------------------------------------------------
# Artifact writers
# ---------------------------------------------------------------------------


def _write_json_artifact(run_dir: Path, filename: str, data: Any) -> Path:
    """Write a JSON artifact file, return the path written."""
    path = run_dir / filename
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return path


def _write_markdown_artifact(run_dir: Path, filename: str, content: str) -> Path:
    """Write a Markdown artifact file, return the path written."""
    path = run_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Main builder function
# ---------------------------------------------------------------------------


def build_weekly_cycle(
    project_root: Path,
    input_file: Path,
    *,
    existing_artifacts_dir: Path | None = None,
    run_id: str | None = None,
    generated_at: datetime | str | None = None,
) -> WeeklyCycleBuildResult:
    """Build a complete deterministic weekly cycle run.

    Orchestrates the full v2.5 pipeline and writes all 13 builder-written
    artifacts into ``artifacts/weekly_runs/{run_id}/`` under *project_root*.

    Args:
        project_root: Root directory of the OOS project.
        input_file: Path to input signal batch (JSONL or JSON array).
        existing_artifacts_dir: Optional path to prior run artifacts for
            parking lot revisit matching.
        run_id: Optional explicit run ID. Auto-generated if not provided.
        generated_at: Optional fixed timestamp for deterministic artifact bytes.

    Returns:
        WeeklyCycleBuildResult with run metadata, artifact paths, and status.
    """
    project_root = project_root.resolve()
    input_file = input_file.resolve()
    weekly_runs_root = project_root / "artifacts" / "weekly_runs"
    warnings: list[str] = []
    errors: list[str] = []
    try:
        generated_at_str = _format_generated_at(generated_at)
    except ValueError as exc:
        return WeeklyCycleBuildResult(
            run_id="",
            run_dir="",
            manifest_path="",
            errors=[str(exc)],
            validation_passed=False,
        )

    # ── 1. Load input signals ──────────────────────────────────────────
    try:
        input_items = _read_input_signals(input_file)
    except (FileNotFoundError, ValueError) as exc:
        return WeeklyCycleBuildResult(
            run_id="",
            run_dir="",
            manifest_path="",
            errors=[str(exc)],
            validation_passed=False,
        )

    input_signal_count = len(input_items)

    # ── 2. Generate or validate run_id ─────────────────────────────────
    run_date = date.today()
    if run_id is None:
        input_content = _compute_input_content_hash(input_file)
        if not input_content:
            input_content = b"empty_input"
        run_id = generate_weekly_run_id(run_date, input_content)
    try:
        run_id = _validate_run_id(run_id, weekly_runs_root)
    except ValueError as exc:
        return WeeklyCycleBuildResult(
            run_id=str(run_id or ""),
            run_dir="",
            manifest_path="",
            errors=[str(exc)],
            validation_passed=False,
        )

    run_dir = weekly_runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # ── 3. Build evidence packs ────────────────────────────────────────
    # Supports two input formats:
    #   a) Evaluation dataset format: items with embedded evidence_pack dicts
    #   b) Direct EvidencePack dicts or CandidateSignal dicts (future support)
    evidence_packs = _evidence_packs_from_input(input_items)
    if not evidence_packs and input_items:
        evidence_packs, canonical_errors = _canonical_signal_packs_from_input(input_items)
        errors.extend(canonical_errors)
    if input_items and not evidence_packs:
        errors.append("Non-empty input did not contain supported EvidencePack or canonical signal batch records")

    # ── 4. Build opportunity candidates ────────────────────────────────
    opportunity_candidates: list[OpportunityCandidate] = []
    for pack in evidence_packs:
        try:
            candidate = build_opportunity_sketch_from_evidence_pack(pack)
            opportunity_candidates.append(candidate)
        except (ValueError, TypeError) as exc:
            errors.append(f"Opportunity candidate build failed for {pack.evidence_pack_id}: {exc}")

    # ── 5. Run quality gates ───────────────────────────────────────────
    gate_results: list[OpportunityGateResult] = []
    for candidate in opportunity_candidates:
        # Find matching evidence pack
        matching_pack = next(
            (p for p in evidence_packs if p.evidence_pack_id == candidate.evidence_pack_id),
            None,
        )
        try:
            result = evaluate_opportunity_quality(candidate, matching_pack)
            gate_results.append(result)
        except (ValueError, TypeError) as exc:
            warnings.append(f"Quality gate skipped for {candidate.opportunity_id}: {exc}")

    # ── 6. Build founder decisions (empty — founder hasn't decided yet) ─
    founder_decisions: list[FounderDecisionV2] = []

    # ── 7. Build feedback mappings (empty) ─────────────────────────────
    feedback_mappings: list[FounderFeedbackMapping] = []

    # ── 8. Build preference profile (empty — no decisions) ─────────────
    preference_profile: FounderPreferenceProfile | None = None
    if founder_decisions:
        try:
            preference_profile = build_founder_preference_profile(
                decisions=founder_decisions,
            )
        except (ValueError, TypeError) as exc:
            warnings.append(f"Preference profile build skipped: {exc}")

    # ── 9. Load prior artifacts for parking lot revisit ────────────────
    prior_parking_records: list[ParkingLotRecord] = []
    revisit_matches: list[RevisitMatch] = []
    if existing_artifacts_dir is not None and existing_artifacts_dir.exists():
        prior_parking_path = existing_artifacts_dir / "parking_lot_records.json"
        if prior_parking_path.exists():
            try:
                prior_data = json.loads(prior_parking_path.read_text(encoding="utf-8"))
                prior_items = prior_data if isinstance(prior_data, list) else prior_data.get("items", prior_data.get("records", []))
                for item in prior_items:
                    try:
                        prior_parking_records.append(ParkingLotRecord.from_dict(item))
                    except (ValueError, TypeError) as exc:
                        errors.append(f"Could not parse prior parking record: {exc}")
            except (json.JSONDecodeError, ValueError) as exc:
                warnings.append(f"Prior parking lot records could not be loaded: {exc}")

        if prior_parking_records:
            # Build evidence dicts for matching
            new_evidence: list[dict[str, Any]] = []
            for candidate in opportunity_candidates:
                new_evidence.append({
                    "opportunity_id": candidate.opportunity_id,
                    "evidence_id": candidate.evidence_ids[0] if candidate.evidence_ids else "",
                    "title": candidate.problem_statement,
                    "summary": candidate.opportunity_sketch,
                })
            revisit_matches = match_revisit_candidates(
                parking_lot_records=prior_parking_records,
                new_evidence=new_evidence,
            )

    # ── 10. Build parking lot records ──────────────────────────────────
    parking_lot_records = build_parking_lot_records(decisions=founder_decisions)

    # ── 11. Build weekly opportunity review package ────────────────────
    opportunity_dicts = [opportunity_sketch_to_dict(c) for c in opportunity_candidates]
    evidence_pack_dicts = [evidence_pack_to_dict(p) for p in evidence_packs]

    review_package = build_weekly_opportunity_review_package(
        decisions=founder_decisions,
        feedback_mappings=feedback_mappings,
        preference_profile=preference_profile,
        evidence_packs=evidence_pack_dicts,
        opportunity_candidates=opportunity_dicts,
        parking_lot_records=parking_lot_records,
        revisit_matches=revisit_matches,
    )

    # ── 12. Build next best actions ────────────────────────────────────
    review_package.generated_at = generated_at_str
    actions = build_next_best_founder_actions(review_package.to_dict())

    # ── 13. Build artifact counts ──────────────────────────────────────
    quality_gate_counts = _count_gate_decisions(gate_results)
    artifact_counts = {
        "input_signals": input_signal_count,
        "evidence_packs": len(evidence_packs),
        "opportunity_candidates": len(opportunity_candidates),
        "quality_gate_decisions": len(gate_results),
        "founder_decisions": len(founder_decisions),
        "feedback_mappings": len(feedback_mappings),
        "parking_lot_records": len(parking_lot_records),
        "revisit_matches": len(revisit_matches),
        "next_best_actions": len(actions),
    }

    # ── 14. Build empty states ─────────────────────────────────────────
    empty_states = default_empty_states()
    empty_states["manifest"] = False  # manifest is written
    empty_states["evidence_packs"] = len(evidence_packs) == 0
    empty_states["opportunity_candidates"] = len(opportunity_candidates) == 0
    empty_states["quality_gate_decisions"] = len(gate_results) == 0
    empty_states["founder_decisions_v2"] = len(founder_decisions) == 0
    empty_states["founder_feedback_mappings"] = len(feedback_mappings) == 0
    empty_states["founder_preference_profile"] = preference_profile is None
    empty_states["weekly_opportunity_review"] = False  # always built
    empty_states["next_best_actions"] = len(actions) == 0
    empty_states["parking_lot_records"] = len(parking_lot_records) == 0
    empty_states["run_report"] = False  # placeholder always written
    empty_states["founder_inbox_v2_index"] = False  # placeholder always written
    empty_states["founder_inbox_v2_md"] = False  # placeholder always written
    empty_states["run_report_md"] = False  # placeholder always written

    # ── 15. Write all artifacts ────────────────────────────────────────
    artifacts_written: list[str] = []

    # 15a. evidence_packs.json
    _write_json_artifact(
        run_dir,
        canonical_artifact_paths()["evidence_packs"],
        {
            "items": [evidence_pack_to_dict(p) for p in evidence_packs],
            "schema_version": canonical_artifact_schema_versions()["evidence_packs"],
            "empty": len(evidence_packs) == 0,
        },
    )
    artifacts_written.append("evidence_packs")

    # 15b. opportunity_candidates.json
    _write_json_artifact(
        run_dir,
        canonical_artifact_paths()["opportunity_candidates"],
        {
            "items": [opportunity_sketch_to_dict(c) for c in opportunity_candidates],
            "schema_version": canonical_artifact_schema_versions()["opportunity_candidates"],
            "empty": len(opportunity_candidates) == 0,
        },
    )
    artifacts_written.append("opportunity_candidates")

    # 15c. quality_gate_decisions.json
    _write_json_artifact(
        run_dir,
        canonical_artifact_paths()["quality_gate_decisions"],
        {
            "items": [r.to_dict() for r in gate_results],
            "schema_version": canonical_artifact_schema_versions()["quality_gate_decisions"],
            "empty": len(gate_results) == 0,
        },
    )
    artifacts_written.append("quality_gate_decisions")

    # 15d. founder_decisions_v2.json
    _write_json_artifact(
        run_dir,
        canonical_artifact_paths()["founder_decisions_v2"],
        {
            "items": [founder_decision_to_dict(d) for d in founder_decisions],
            "schema_version": canonical_artifact_schema_versions()["founder_decisions_v2"],
            "empty": True,
            "note": "Founder decisions are imported separately via the founder decision import flow (v2.6 item 5.1).",
        },
    )
    artifacts_written.append("founder_decisions_v2")

    # 15e. founder_feedback_mappings.json
    _write_json_artifact(
        run_dir,
        canonical_artifact_paths()["founder_feedback_mappings"],
        {
            "items": [founder_feedback_mapping_to_dict(m) for m in feedback_mappings],
            "schema_version": canonical_artifact_schema_versions()["founder_feedback_mappings"],
            "empty": True,
            "note": "Feedback mappings are derived from founder decisions after import.",
        },
    )
    artifacts_written.append("founder_feedback_mappings")

    # 15f. founder_preference_profile.json
    if preference_profile is not None:
        _write_json_artifact(
            run_dir,
            canonical_artifact_paths()["founder_preference_profile"],
            founder_preference_profile_to_dict(preference_profile),
        )
    else:
        _write_json_artifact(
            run_dir,
            canonical_artifact_paths()["founder_preference_profile"],
            {
                "profile_id": "empty_profile",
                "preferred_pain_types": [],
                "rejected_patterns": [],
                "promoted_patterns": [],
                "recurring_kill_reasons": [],
                "areas_needing_more_evidence": [],
                "source_decision_ids": [],
                "source_feedback_mapping_ids": [],
                "generated_at": generated_at_str,
                "decision_count": 0,
                "promote_count": 0,
                "park_count": 0,
                "kill_count": 0,
                "revisit_count": 0,
                "needs_more_evidence_count": 0,
                "schema_version": canonical_artifact_schema_versions()["founder_preference_profile"],
                "ml_training_claimed": False,
                "autonomous_decisions_made": False,
                "empty": True,
                "note": "Empty preference profile. Populated after founder decisions are imported.",
            },
        )
    artifacts_written.append("founder_preference_profile")

    # 15g. weekly_opportunity_review.json
    _write_json_artifact(
        run_dir,
        canonical_artifact_paths()["weekly_opportunity_review"],
        json.loads(weekly_review_package_to_json(review_package)),
    )
    artifacts_written.append("weekly_opportunity_review")

    # 15h. next_best_actions.json
    _write_json_artifact(
        run_dir,
        canonical_artifact_paths()["next_best_actions"],
        {
            "items": json.loads(next_best_actions_to_json(actions)),
            "schema_version": canonical_artifact_schema_versions()["next_best_actions"],
            "empty": len(actions) == 0,
        },
    )
    artifacts_written.append("next_best_actions")

    # 15i. parking_lot_records.json
    _write_json_artifact(
        run_dir,
        canonical_artifact_paths()["parking_lot_records"],
        {
            "items": json.loads(parking_lot_records_to_json(parking_lot_records)),
            "schema_version": canonical_artifact_schema_versions()["parking_lot_records"],
            "empty": len(parking_lot_records) == 0,
            "revisit_matches_count": len(revisit_matches),
        },
    )
    artifacts_written.append("parking_lot_records")

    # 15j. founder_inbox_v2.md (real — v2.6 item 4.1)
    action_dicts = [a.to_dict() for a in actions]
    gate_dicts = [r.to_dict() for r in gate_results]
    pack_dicts = [evidence_pack_to_dict(p) for p in evidence_packs]
    opp_dicts = [opportunity_sketch_to_dict(c) for c in opportunity_candidates]
    revisit_dicts = [m.to_dict() for m in revisit_matches]
    pl_dicts = [r.to_dict() for r in parking_lot_records]
    manifest_path = str(run_dir / "manifest.json")
    marks_path = canonical_artifact_paths()["founder_inbox_v2_md"]
    index_path = canonical_artifact_paths()["founder_inbox_v2_index"]

    inbox = build_founder_inbox_v2(
        run_id=run_id,
        manifest_path=manifest_path,
        generated_at=generated_at_str,
        review_package=review_package.to_dict(),
        actions=action_dicts,
        gate_results=gate_dicts,
        evidence_packs=pack_dicts,
        opportunity_candidates=opp_dicts,
        revisit_matches=revisit_dicts,
        parking_lot_records=pl_dicts,
        marks_path=marks_path,
        index_path=index_path,
    )

    inbox_md = render_founder_inbox_v2_markdown(inbox)
    _write_markdown_artifact(
        run_dir,
        marks_path,
        inbox_md,
    )
    artifacts_written.append("founder_inbox_v2_md")

    # 15l. founder_inbox_v2_index.json (real — v2.6 item 4.1)
    inbox_index = founder_inbox_v2_to_json(inbox)
    _write_json_artifact(
        run_dir,
        index_path,
        inbox_index,
    )
    artifacts_written.append("founder_inbox_v2_index")


    # ── 16. Build and write manifest ───────────────────────────────────
    manifest = make_default_manifest(
        run_id=run_id,
        created_at=generated_at_str,
        input_file=str(input_file.relative_to(project_root)) if str(input_file).startswith(str(project_root)) else str(input_file),
        input_signal_count=input_signal_count,
        empty_states=empty_states,
    )
    write_weekly_run_manifest(run_dir, manifest)
    artifacts_written.append("manifest")

    # ── 17. Build and write run report (after manifest is on disk) ────
    # Remove any stale run_report artifacts from a prior run so that
    # build_weekly_run_report sees a clean state (determinism requirement).
    _run_report_json = run_dir / "run_report.json"
    _run_report_md = run_dir / "run_report.md"
    if _run_report_json.exists():
        _run_report_json.unlink()
    if _run_report_md.exists():
        _run_report_md.unlink()
    try:
        report = build_weekly_run_report(project_root=project_root, run_id=run_id, generated_at=generated_at_str)
        write_weekly_run_report(report, run_dir)
    except Exception as exc:
        errors.append(f"Failed to build weekly run report: {exc}")
    artifacts_written.append("run_report")
    artifacts_written.append("run_report_md")

    # ── 18. Build result ───────────────────────────────────────────────
    pipeline_summary = {
        "input_file": str(input_file),
        "input_signal_count": input_signal_count,
        "evidence_packs_built": len(evidence_packs),
        "opportunity_candidates_built": len(opportunity_candidates),
        "quality_gate_results": len(gate_results),
        "quality_gate_counts": quality_gate_counts,
        "founder_decisions_count": len(founder_decisions),
        "feedback_mappings_count": len(feedback_mappings),
        "preference_profile_built": preference_profile is not None,
        "revisit_matches_found": len(revisit_matches),
        "parking_lot_record_count": len(parking_lot_records),
        "next_best_actions_count": len(actions),
        "artifacts_written": len(artifacts_written),
    }

    if existing_artifacts_dir is None:
        warnings.append("existing_artifacts_dir not provided; parking lot revisit matching skipped for prior runs.")
    elif not prior_parking_records:
        warnings.append("existing_artifacts_dir provided but no valid parking lot records found; revisit matching skipped.")

    errors.extend(_validate_builder_output(run_dir, input_signal_count, artifacts_written, pipeline_summary))
    validation_passed = len(errors) == 0

    return WeeklyCycleBuildResult(
        run_id=run_id,
        run_dir=str(run_dir),
        manifest_path=str(run_dir / "manifest.json"),
        artifacts_written=artifacts_written,
        artifact_count=len(artifacts_written),
        empty_states=empty_states,
        warnings=warnings,
        errors=errors,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
        validation_passed=validation_passed,
        pipeline_summary=pipeline_summary,
    )


def _count_gate_decisions(gate_results: list[OpportunityGateResult]) -> dict[str, int]:
    """Count quality gate decisions by type."""
    counts: dict[str, int] = {"total": len(gate_results)}
    for r in gate_results:
        counts[r.decision] = counts.get(r.decision, 0) + 1
    return counts


def _validate_builder_output(
    run_dir: Path,
    input_signal_count: int,
    artifacts_written: list[str],
    pipeline_summary: dict[str, Any],
) -> list[str]:
    validation_errors: list[str] = []
    paths = canonical_artifact_paths()
    try:
        from oos.weekly_run_manifest import read_weekly_run_manifest

        read_weekly_run_manifest(run_dir)
    except (FileNotFoundError, ValueError) as exc:
        validation_errors.append(f"Manifest readback validation failed: {exc}")

    for key, filename in paths.items():
        artifact_path = run_dir / filename
        if not artifact_path.is_file():
            validation_errors.append(f"Required artifact missing: {key} ({filename})")

    for key, filename in paths.items():
        if filename.endswith(".json"):
            artifact_path = run_dir / filename
            if artifact_path.is_file():
                try:
                    json.loads(artifact_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    validation_errors.append(f"JSON artifact is not parseable: {key}: {exc.msg}")

    if len(artifacts_written) != len(paths):
        validation_errors.append(
            f"Expected {len(paths)} artifacts_written entries, got {len(artifacts_written)}"
        )
    if input_signal_count > 0:
        required_non_empty = (
            "evidence_packs_built",
            "opportunity_candidates_built",
            "quality_gate_results",
        )
        for key in required_non_empty:
            if int(pipeline_summary.get(key, 0)) <= 0:
                validation_errors.append(f"Non-empty supported input produced no {key}")
    return validation_errors
