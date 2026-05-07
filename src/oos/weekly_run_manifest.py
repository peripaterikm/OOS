from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

WEEKLY_RUN_MANIFEST_SCHEMA_VERSION = "weekly_run_manifest.v1"

# ---------------------------------------------------------------------------
# Canonical artifact paths (relative to the run directory)
# ---------------------------------------------------------------------------

_ARTIFACT_FILENAMES: dict[str, str] = {
    "manifest": "manifest.json",
    "evidence_packs": "evidence_packs.json",
    "opportunity_candidates": "opportunity_candidates.json",
    "quality_gate_decisions": "quality_gate_decisions.json",
    "founder_decisions_v2": "founder_decisions_v2.json",
    "founder_feedback_mappings": "founder_feedback_mappings.json",
    "founder_preference_profile": "founder_preference_profile.json",
    "weekly_opportunity_review": "weekly_opportunity_review.json",
    "next_best_actions": "next_best_actions.json",
    "parking_lot_records": "parking_lot_records.json",
    "run_report": "run_report.json",
    "founder_inbox_v2_md": "founder_inbox_v2.md",
    "founder_inbox_v2_index": "founder_inbox_v2_index.json",
    "run_report_md": "run_report.md",
}

# Canonical ordering for deterministic serialization
_CANONICAL_ARTIFACT_KEYS: tuple[str, ...] = (
    "manifest",
    "evidence_packs",
    "opportunity_candidates",
    "quality_gate_decisions",
    "founder_decisions_v2",
    "founder_feedback_mappings",
    "founder_preference_profile",
    "weekly_opportunity_review",
    "next_best_actions",
    "parking_lot_records",
    "run_report",
    "founder_inbox_v2_index",
    "founder_inbox_v2_md",
    "run_report_md",
)

# Schema version for each artifact type (including future items)
_ARTIFACT_SCHEMA_VERSIONS: dict[str, str] = {
    "manifest": WEEKLY_RUN_MANIFEST_SCHEMA_VERSION,
    "evidence_packs": "evidence_pack.v1",
    "opportunity_candidates": "opportunity_sketch.v1",
    "quality_gate_decisions": "opportunity_quality_gate.v1",
    "founder_decisions_v2": "founder_decision_v2.v1",
    "founder_feedback_mappings": "founder_feedback_mapping.v1",
    "founder_preference_profile": "founder_preference_profile.v1",
    "weekly_opportunity_review": "weekly_opportunity_review.v1",
    "next_best_actions": "founder_action.v1",
    "parking_lot_records": "parking_lot.v1",
    "run_report": "weekly_run_report.v1",
    "founder_inbox_v2_index": "founder_inbox_v2_index.v1",
    # Markdown artifacts have no schema version; use the key name as version marker
    "founder_inbox_v2_md": "founder_inbox_v2_md.v1",
    "run_report_md": "run_report_md.v1",
}

KNOWN_ARTIFACT_KEYS = frozenset(_ARTIFACT_FILENAMES.keys())
KNOWN_SCHEMA_VERSIONS = frozenset(_ARTIFACT_SCHEMA_VERSIONS.values())

# ---------------------------------------------------------------------------
# Run ID generation
# ---------------------------------------------------------------------------


def generate_weekly_run_id(
    run_date: date,
    input_file_content: bytes,
) -> str:
    """Generate a deterministic weekly run ID.

    Format: ``weekly_run_{YYYY_MM_DD}_{content_hash_short}``
    where ``content_hash_short`` is the first 12 hex characters of
    ``sha256(input_file_content + run_date_iso)``.

    Args:
        run_date: The date the run was initiated (local or UTC).
        input_file_content: Raw bytes of the input file.

    Returns:
        A deterministic run ID string.
    """
    if not isinstance(run_date, date):
        raise TypeError("run_date must be a datetime.date")
    if not input_file_content:
        raise ValueError("input_file_content must be non-empty bytes")

    date_str = run_date.isoformat()  # YYYY-MM-DD
    seed = input_file_content + date_str.encode("utf-8")
    content_hash = hashlib.sha256(seed).hexdigest()[:12]
    return f"weekly_run_{date_str}_{content_hash}"


# ---------------------------------------------------------------------------
# WeeklyRunManifest model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WeeklyRunManifest:
    """Canonical manifest for one v2.6 weekly cycle run.

    Lists every expected artifact path, its schema version, and whether
    it is empty.  Paths are relative to the run directory.
    """

    run_id: str
    created_at: str
    schema_version: str = WEEKLY_RUN_MANIFEST_SCHEMA_VERSION
    artifact_paths: dict[str, str] = field(default_factory=dict)
    artifact_schema_versions: dict[str, str] = field(default_factory=dict)
    empty_states: dict[str, bool] = field(default_factory=dict)
    input_file: str | None = None
    input_signal_count: int | None = None
    advisory_only: bool = True
    no_live_api: bool = True
    no_live_llm: bool = True

    # ── helpers ──────────────────────────────────────────────────────

    def artifact_keys(self) -> tuple[str, ...]:
        """Return artifact keys in canonical order."""
        return tuple(k for k in _CANONICAL_ARTIFACT_KEYS if k in self.artifact_paths)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict with deterministic key order."""
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
            "artifact_paths": _ordered_artifact_dict(self.artifact_paths),
            "artifact_schema_versions": _ordered_artifact_dict(self.artifact_schema_versions),
            "empty_states": _ordered_artifact_dict(self.empty_states),
            "input_file": self.input_file,
            "input_signal_count": self.input_signal_count,
            "advisory_only": self.advisory_only,
            "no_live_api": self.no_live_api,
            "no_live_llm": self.no_live_llm,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WeeklyRunManifest:
        """Deserialize from a dict (e.g. parsed JSON)."""
        return cls(
            run_id=str(data.get("run_id", "")),
            created_at=str(data.get("created_at", "")),
            schema_version=str(data.get("schema_version", WEEKLY_RUN_MANIFEST_SCHEMA_VERSION)),
            artifact_paths=_normalize_artifact_dict(data.get("artifact_paths", {})),
            artifact_schema_versions=_normalize_artifact_dict(data.get("artifact_schema_versions", {})),
            empty_states=_normalize_bool_dict(data.get("empty_states", {})),
            input_file=data.get("input_file"),
            input_signal_count=data.get("input_signal_count"),
            advisory_only=bool(data.get("advisory_only", True)),
            no_live_api=bool(data.get("no_live_api", True)),
            no_live_llm=bool(data.get("no_live_llm", True)),
        )

    def validate(self) -> list[str]:
        """Return list of validation error strings (empty = valid)."""
        errors: list[str] = []

        # Required non-empty strings
        for field_name in ("run_id", "created_at", "schema_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{field_name} must be a non-empty string")

        if self.schema_version != WEEKLY_RUN_MANIFEST_SCHEMA_VERSION:
            errors.append(
                f"schema_version must be {WEEKLY_RUN_MANIFEST_SCHEMA_VERSION}"
            )

        # artifact_paths keys must be known
        for key in self.artifact_paths:
            if key not in KNOWN_ARTIFACT_KEYS:
                errors.append(f"Unknown artifact key in artifact_paths: '{key}'")

        # artifact_schema_versions keys must be known, values must be known
        for key, version in self.artifact_schema_versions.items():
            if key not in KNOWN_ARTIFACT_KEYS:
                errors.append(f"Unknown artifact key in artifact_schema_versions: '{key}'")
            if version not in KNOWN_SCHEMA_VERSIONS:
                errors.append(f"Unknown schema version for '{key}': '{version}'")

        # empty_states keys must be known
        for key in self.empty_states:
            if key not in KNOWN_ARTIFACT_KEYS:
                errors.append(f"Unknown artifact key in empty_states: '{key}'")

        # Path traversal check: no path may contain '..' or be absolute
        for key, path in self.artifact_paths.items():
            if ".." in str(path) or Path(str(path)).is_absolute():
                errors.append(
                    f"artifact_paths['{key}'] must be relative and not contain '..': '{path}'"
                )

        # Must not be missing the 'manifest' entry itself
        if "manifest" not in self.artifact_paths:
            errors.append("artifact_paths must include 'manifest'")

        # Advisory / no-live safety flags
        if not self.advisory_only:
            errors.append("advisory_only must be True")
        if not self.no_live_api:
            errors.append("no_live_api must be True")
        if not self.no_live_llm:
            errors.append("no_live_llm must be True")

        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0


# ---------------------------------------------------------------------------
# Serialization helpers (write / read manifest.json)
# ---------------------------------------------------------------------------


def write_weekly_run_manifest(
    run_dir: Path,
    manifest: WeeklyRunManifest,
) -> WeeklyRunManifest:
    """Write ``manifest.json`` into *run_dir* and return the manifest.

    The directory is created if it does not exist.  The manifest is validated
    before writing.
    """
    run_dir = run_dir.resolve()
    errors = manifest.validate()
    if errors:
        raise ValueError(
            f"WeeklyRunManifest validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / _ARTIFACT_FILENAMES["manifest"]
    payload = manifest.to_dict()
    manifest_path.write_text(
        _stable_json_dumps(payload),
        encoding="utf-8",
    )
    return manifest


def read_weekly_run_manifest(
    run_dir: Path,
) -> WeeklyRunManifest:
    """Read and validate a ``manifest.json`` from *run_dir*."""
    run_dir = run_dir.resolve()
    manifest_path = run_dir / _ARTIFACT_FILENAMES["manifest"]
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    raw = manifest_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in manifest: {manifest_path}") from exc

    manifest = WeeklyRunManifest.from_dict(data)
    errors = manifest.validate()
    if errors:
        raise ValueError(
            f"Manifest validation failed ({manifest_path}):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    # Path-traversal guard: all artifact paths must be inside run_dir
    for key, rel_path in manifest.artifact_paths.items():
        candidate = (run_dir / rel_path).resolve()
        if not str(candidate).startswith(str(run_dir) + "\\") and not str(candidate).startswith(str(run_dir) + "/"):
            raise ValueError(
                f"artifact_paths['{key}'] escapes run directory: '{rel_path}'"
            )

    return manifest


# ---------------------------------------------------------------------------
# Canonical artifact path helpers
# ---------------------------------------------------------------------------


def canonical_artifact_paths() -> dict[str, str]:
    """Return the canonical mapping of artifact key → relative filename."""
    return dict(_ARTIFACT_FILENAMES)


def canonical_artifact_schema_versions() -> dict[str, str]:
    """Return the canonical mapping of artifact key → schema version string."""
    return dict(_ARTIFACT_SCHEMA_VERSIONS)


def default_empty_states() -> dict[str, bool]:
    """Return a dict mapping every artifact key to ``True`` (empty)."""
    return {key: True for key in _CANONICAL_ARTIFACT_KEYS}


def make_default_manifest(
    run_id: str,
    created_at: str | None = None,
    *,
    input_file: str | None = None,
    input_signal_count: int | None = None,
    empty_states: dict[str, bool] | None = None,
) -> WeeklyRunManifest:
    """Create a fully-populated default manifest.

    By default every artifact is marked empty.  Pass ``empty_states`` to
    override individual entries.
    """
    resolved_empty = default_empty_states()
    if empty_states:
        resolved_empty.update(empty_states)

    return WeeklyRunManifest(
        run_id=run_id,
        created_at=created_at or _iso_utc_now_seconds(),
        schema_version=WEEKLY_RUN_MANIFEST_SCHEMA_VERSION,
        artifact_paths=canonical_artifact_paths(),
        artifact_schema_versions=canonical_artifact_schema_versions(),
        empty_states=resolved_empty,
        input_file=input_file,
        input_signal_count=input_signal_count,
        advisory_only=True,
        no_live_api=True,
        no_live_llm=True,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ordered_artifact_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Return *d* with keys in canonical artifact order."""
    result: dict[str, Any] = {}
    for key in _CANONICAL_ARTIFACT_KEYS:
        if key in d:
            result[key] = d[key]
    # preserve any extra keys not in canonical order (append at end, sorted)
    extra = sorted(set(d.keys()) - set(_CANONICAL_ARTIFACT_KEYS))
    for key in extra:
        result[key] = d[key]
    return result


def _normalize_artifact_dict(raw: Any) -> dict[str, str]:
    """Normalize a dict of {key: str} from JSON input."""
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _normalize_bool_dict(raw: Any) -> dict[str, bool]:
    """Normalize a dict of {key: bool} from JSON input."""
    if not isinstance(raw, dict):
        return {}
    return {str(k): bool(v) for k, v in raw.items()}


def _stable_json_dumps(obj: Any) -> str:
    """JSON dump with deterministic key ordering and UTF-8 safe."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=False, indent=2) + "\n"
