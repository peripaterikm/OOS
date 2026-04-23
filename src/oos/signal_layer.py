from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .artifact_store import ArtifactStore
from .models import Signal, SignalStatus


def _iso_utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_signal_id() -> str:
    return f"sig_{uuid.uuid4().hex}"


@dataclass(frozen=True)
class RawSignal:
    """
    Input shape for raw signal ingestion.

    This is intentionally simple and file-friendly.
    """

    raw_content: str
    source: str = "manual"
    timestamp: str = ""
    extracted_pain: str = ""
    candidate_icp: str = "unknown"
    id: Optional[str] = None

    # Optional overrides for validity dimensions (0/1).
    validity_specificity: Optional[int] = None
    validity_recurrence: Optional[int] = None
    validity_workaround: Optional[int] = None
    validity_cost_signal: Optional[int] = None
    validity_icp_match: Optional[int] = None


@dataclass(frozen=True)
class ValidityResult:
    specificity: int
    recurrence: int
    active_workaround: int
    cost_signal: int
    icp_match: int
    score: int
    status: SignalStatus
    rejection_reason: Optional[str]


class SignalValidityEvaluator:
    """
    Interface for signal validity evaluation.

    Week 3 uses a deterministic rule-based implementation to keep tests stable.
    If an LLM-based evaluator is added later, it should implement this interface.
    """

    def evaluate(self, raw: RawSignal) -> ValidityResult:  # pragma: no cover (interface)
        raise NotImplementedError


class RuleBasedSignalValidityEvaluator(SignalValidityEvaluator):
    """
    Minimal deterministic evaluator for the 5 required validity dimensions.

    It is intentionally conservative and test-friendly.
    """

    _re_digit = re.compile(r"\d")
    _re_specificity_markers = re.compile(
        r"\b(error|fails?|cannot|can't|broken|bug|issue|step|workflow|export|import|manual|вручн|ошибк|сбой|не могу)\b",
        flags=re.IGNORECASE,
    )
    _re_recurrence_markers = re.compile(
        r"\b(often|always|every|daily|weekly|repeated|again|recurring|кажд|часто|постоянно|всегда|снова)\b",
        flags=re.IGNORECASE,
    )
    _re_workaround_markers = re.compile(
        r"\b(workaround|hack|script|spreadsheet|copy|paste|manually|вручн|костыл|обход|копир|вставля|экспорт)\b",
        flags=re.IGNORECASE,
    )
    _re_cost_markers = re.compile(
        r"\b(\$|usd|hours?|minutes?|days?|time|cost|lost|revenue|risk|штраф|деньг|врем|час|минут|дорог)\b",
        flags=re.IGNORECASE,
    )

    def evaluate(self, raw: RawSignal) -> ValidityResult:
        text = raw.raw_content or ""
        pain = raw.extracted_pain.strip() if raw.extracted_pain else ""
        icp = raw.candidate_icp.strip() if raw.candidate_icp else "unknown"

        # Allow explicit overrides (useful for deterministic imports / future tooling).
        spec = raw.validity_specificity
        rec = raw.validity_recurrence
        wor = raw.validity_workaround
        cost = raw.validity_cost_signal
        icp_match = raw.validity_icp_match

        if spec is None:
            has_details = bool(self._re_digit.search(text) or self._re_specificity_markers.search(text))
            has_pain = bool(pain) or ("pain" in text.lower()) or ("боль" in text.lower())
            spec = 1 if (has_details and has_pain) else 0
        if rec is None:
            rec = 1 if self._re_recurrence_markers.search(text) else 0
        if wor is None:
            wor = 1 if self._re_workaround_markers.search(text) else 0
        if cost is None:
            cost = 1 if self._re_cost_markers.search(text) else 0
        if icp_match is None:
            icp_match = 1 if (icp.lower() != "unknown" and icp != "") else 0

        score = int(spec) + int(rec) + int(wor) + int(cost) + int(icp_match)

        # Per docs/vision.md + scope-v1.md:
        # validated = 3+ dimensions met, weak = 2, noise = 0-1
        if score >= 3:
            status = SignalStatus.validated
            rejection_reason = None
        elif score == 2:
            status = SignalStatus.weak
            rejection_reason = None
        else:
            status = SignalStatus.noise
            missing = []
            if not spec:
                missing.append("specificity")
            if not rec:
                missing.append("recurrence")
            if not wor:
                missing.append("active_workaround")
            if not cost:
                missing.append("cost_signal")
            if not icp_match:
                missing.append("icp_match")
            rejection_reason = f"Only {score}/5 validity dimensions met. Missing: {', '.join(missing)}"

        return ValidityResult(
            specificity=int(spec),
            recurrence=int(rec),
            active_workaround=int(wor),
            cost_signal=int(cost),
            icp_match=int(icp_match),
            score=score,
            status=status,
            rejection_reason=rejection_reason,
        )


class RawSignalFileImporter:
    """
    File-based import for raw signals.

    Supported formats:
    - JSONL: one JSON object per line
    - JSON: an array of objects
    """

    def load(self, path: Path, default_source: str = "file_import") -> List[RawSignal]:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return []

        items: List[Dict[str, Any]]
        if text.startswith("["):
            items = json.loads(text)
            if not isinstance(items, list):
                raise ValueError("Expected a JSON array of objects")
        else:
            items = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                items.append(json.loads(line))

        raw_signals: List[RawSignal] = []
        for obj in items:
            if not isinstance(obj, dict):
                raise ValueError("Each raw signal must be a JSON object")
            raw_content = str(obj.get("raw_content", "")).strip()
            if not raw_content:
                raise ValueError("raw_content is required for each raw signal")

            raw_signals.append(
                RawSignal(
                    id=obj.get("id"),
                    source=str(obj.get("source") or default_source),
                    timestamp=str(obj.get("timestamp") or ""),
                    raw_content=raw_content,
                    extracted_pain=str(obj.get("extracted_pain") or ""),
                    candidate_icp=str(obj.get("candidate_icp") or "unknown"),
                    validity_specificity=obj.get("validity_specificity"),
                    validity_recurrence=obj.get("validity_recurrence"),
                    validity_workaround=obj.get("validity_workaround"),
                    validity_cost_signal=obj.get("validity_cost_signal"),
                    validity_icp_match=obj.get("validity_icp_match"),
                )
            )
        return raw_signals


@dataclass(frozen=True)
class SignalRoutingPaths:
    """
    Explicit routing destinations for Week 3.
    """

    main_signals_dir: Path
    weak_backlog_dir: Path
    noise_archive_dir: Path


class SignalRouter:
    """
    Persist Signals and route them to explicit destinations.

    - Main store: ArtifactStore for full Signal artifact under artifacts/signals.
    - Weak/noise: lightweight routing refs for review/backlog/archives.
    """

    def __init__(self, artifacts_root: Path):
        self.store = ArtifactStore(root_dir=artifacts_root)
        self.paths = SignalRoutingPaths(
            main_signals_dir=artifacts_root / "signals",
            weak_backlog_dir=artifacts_root / "weak_signals",
            noise_archive_dir=artifacts_root / "noise_archive",
        )

    def write_and_route(self, signal: Signal) -> Tuple[Path, Optional[Path]]:
        main_ref = self.store.write_model(signal).path

        route_ref_path: Optional[Path] = None
        if signal.status == SignalStatus.weak:
            route_ref_path = self._write_route_ref(self.paths.weak_backlog_dir, signal)
        elif signal.status == SignalStatus.noise:
            route_ref_path = self._write_route_ref(self.paths.noise_archive_dir, signal)

        return main_ref, route_ref_path

    def _write_route_ref(self, dir_path: Path, signal: Signal) -> Path:
        dir_path.mkdir(parents=True, exist_ok=True)
        path = dir_path / f"{signal.id}.json"
        payload = {
            "signal_id": signal.id,
            "status": signal.status.value,
            "validity_score": signal.validity_score,
            "rejection_reason": signal.rejection_reason,
            "timestamp": signal.timestamp,
            "source": signal.source,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


class SignalLayer:
    """
    Week 3 Signal Layer: ingestion + validity evaluation + explicit routing.
    """

    def __init__(
        self,
        artifacts_root: Path,
        evaluator: Optional[SignalValidityEvaluator] = None,
        importer: Optional[RawSignalFileImporter] = None,
    ):
        self.router = SignalRouter(artifacts_root=artifacts_root)
        self.evaluator = evaluator or RuleBasedSignalValidityEvaluator()
        self.importer = importer or RawSignalFileImporter()

    def ingest_manual(
        self,
        raw_content: str,
        extracted_pain: str,
        candidate_icp: str,
        *,
        source: str = "manual",
        timestamp: Optional[str] = None,
        signal_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        raw = RawSignal(
            id=signal_id,
            source=source,
            timestamp=timestamp or _iso_utc_now_seconds(),
            raw_content=raw_content,
            extracted_pain=extracted_pain,
            candidate_icp=candidate_icp,
        )
        return self._ingest_one(raw, metadata=metadata or {})

    def ingest_file(self, path: Path, *, default_source: str = "file_import") -> List[Signal]:
        raws = self.importer.load(path=path, default_source=default_source)
        signals: List[Signal] = []
        for raw in raws:
            signals.append(self._ingest_one(raw, metadata={"import_path": str(path)}))
        return signals

    def ingest_raw_signal(self, raw: RawSignal, *, metadata: Optional[Dict[str, Any]] = None) -> Signal:
        return self._ingest_one(raw, metadata=metadata or {})

    def _ingest_one(self, raw: RawSignal, metadata: Dict[str, Any]) -> Signal:
        rid = raw.id or _new_signal_id()
        ts = raw.timestamp or _iso_utc_now_seconds()

        # Ensure required fields exist (Week 2 model validation requires them).
        extracted_pain = raw.extracted_pain.strip() if raw.extracted_pain.strip() else raw.raw_content.strip()[:200]
        candidate_icp = raw.candidate_icp.strip() if raw.candidate_icp.strip() else "unknown"

        validity = self.evaluator.evaluate(
            RawSignal(
                id=rid,
                source=raw.source,
                timestamp=ts,
                raw_content=raw.raw_content,
                extracted_pain=extracted_pain,
                candidate_icp=candidate_icp,
                validity_specificity=raw.validity_specificity,
                validity_recurrence=raw.validity_recurrence,
                validity_workaround=raw.validity_workaround,
                validity_cost_signal=raw.validity_cost_signal,
                validity_icp_match=raw.validity_icp_match,
            )
        )

        signal = Signal(
            id=rid,
            source=raw.source,
            timestamp=ts,
            raw_content=raw.raw_content,
            extracted_pain=extracted_pain,
            candidate_icp=candidate_icp,
            validity_specificity=validity.specificity,
            validity_recurrence=validity.recurrence,
            validity_workaround=validity.active_workaround,
            validity_cost_signal=validity.cost_signal,
            validity_icp_match=validity.icp_match,
            validity_score=validity.score,
            status=validity.status,
            rejection_reason=validity.rejection_reason,
            metadata=metadata,
        )

        self.router.write_and_route(signal)
        return signal

