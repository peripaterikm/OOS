from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .ideation import DeterministicIdeationStub, SafeAIIdeationAdapter, StaticJSONAIIdeationProvider
from .models import IdeaScreenStatus, IdeaVariant, OpportunityCard
from .real_signal_batch import CanonicalSignalBatchLoader


QUALITY_CRITERIA = [
    "schema_validity",
    "required_field_completeness",
    "downstream_compatibility",
    "traceability_preservation",
    "non_empty_useful_idea_content",
]

APPROVAL_THRESHOLD = len(QUALITY_CRITERIA)


@dataclass(frozen=True)
class IdeationEvaluationResult:
    mode: str
    passed: bool
    score: int
    criteria: Dict[str, bool]
    idea_count: int
    idea_ids: List[str]
    error: str = ""


def _utc_now_seconds() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _evaluation_opportunity(input_file: Path) -> OpportunityCard:
    items = CanonicalSignalBatchLoader().load(input_file)
    return OpportunityCard(
        id="opp_eval_1",
        title=items[0].title,
        source_signal_ids=[item.signal_id for item in items],
        pain_summary=" | ".join(item.title for item in items[:5]),
        icp="unknown",
        opportunity_type="real_signal_batch",
        why_it_matters="Evaluate ideation quality against real input signal titles.",
    )


def _criteria_for(ideas: List[IdeaVariant], opportunity: OpportunityCard) -> Dict[str, bool]:
    schema_validity = True
    for idea in ideas:
        try:
            idea.validate()
        except ValueError:
            schema_validity = False
            break

    required_fields = [
        "short_concept",
        "business_model",
        "standardization_focus",
        "ai_leverage",
        "external_execution_needed",
        "rough_monetization_model",
    ]
    required_field_completeness = bool(ideas) and all(
        all(str(getattr(idea, field, "")).strip() for field in required_fields) for idea in ideas
    )
    downstream_compatibility = bool(ideas) and all(
        idea.opportunity_id == opportunity.id and idea.status == IdeaScreenStatus.candidate for idea in ideas
    )
    traceability_preservation = bool(opportunity.source_signal_ids) and all(
        idea.opportunity_id == opportunity.id for idea in ideas
    )
    non_empty_useful_idea_content = bool(ideas) and all(
        len(idea.short_concept.strip()) >= 20
        and len(idea.standardization_focus.strip()) >= 10
        and len(idea.ai_leverage.strip()) >= 10
        for idea in ideas
    )

    return {
        "schema_validity": schema_validity,
        "required_field_completeness": required_field_completeness,
        "downstream_compatibility": downstream_compatibility,
        "traceability_preservation": traceability_preservation,
        "non_empty_useful_idea_content": non_empty_useful_idea_content,
    }


def _result_for(mode: str, ideas: List[IdeaVariant], opportunity: OpportunityCard, error: str = "") -> IdeationEvaluationResult:
    criteria = _criteria_for(ideas, opportunity)
    score = sum(1 for passed in criteria.values() if passed)
    return IdeationEvaluationResult(
        mode=mode,
        passed=score >= APPROVAL_THRESHOLD,
        score=score,
        criteria=criteria,
        idea_count=len(ideas),
        idea_ids=[idea.id for idea in ideas],
        error=error,
    )


def evaluate_ai_ideation(*, project_root: Path, input_file: Path, ai_response_json: str) -> Path:
    opportunity = _evaluation_opportunity(input_file)
    deterministic_ideas = DeterministicIdeationStub(store=None).generate(opportunity)
    deterministic_result = _result_for("deterministic", deterministic_ideas, opportunity)

    assisted_error = ""
    assisted_ideas: List[IdeaVariant] = []
    try:
        adapter = SafeAIIdeationAdapter(
            store=None,
            deterministic=DeterministicIdeationStub(store=None),
            provider=StaticJSONAIIdeationProvider(response_json=ai_response_json),
        )
        assisted_ideas = adapter._generate_ai_ideas(opportunity)
    except Exception as exc:
        assisted_error = str(exc)

    assisted_result = _result_for("assisted", assisted_ideas, opportunity, error=assisted_error)
    assisted_approved = assisted_result.passed
    rollback_recommendation = (
        "assisted_ideation_approved"
        if assisted_approved
        else "rollback_to_deterministic: keep assisted ideation disabled until evaluation passes all criteria"
    )

    payload: Dict[str, Any] = {
        "version": "ai_ideation_evaluation_v1",
        "generated_at": _utc_now_seconds(),
        "scope": "ideation_only",
        "input_file": str(input_file.resolve()),
        "opportunity": {
            "id": opportunity.id,
            "title": opportunity.title,
            "source_signal_ids": opportunity.source_signal_ids,
        },
        "quality_criteria": QUALITY_CRITERIA,
        "approval_threshold": APPROVAL_THRESHOLD,
        "deterministic": deterministic_result.__dict__,
        "assisted": assisted_result.__dict__,
        "rollback_rules": [
            "if assisted output fails schema validation, fallback to deterministic",
            "if assisted output is unusable or empty, fallback to deterministic",
            "if evaluation score is below threshold, assisted mode is not approved for use",
        ],
        "rollback_recommendation": rollback_recommendation,
        "where_assisted_helps": (
            "Use assisted ideation only when it produces complete, schema-valid variants "
            "that remain compatible with downstream OOS artifacts."
        ),
        "where_assisted_should_remain_disabled": (
            "Keep disabled for signal ingestion, screening, council, portfolio, weekly review, "
            "and any ideation output that fails the approval threshold."
        ),
    }

    evaluation_dir = project_root / "artifacts" / "evaluation"
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    report_path = evaluation_dir / "ai_ideation_evaluation.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path
