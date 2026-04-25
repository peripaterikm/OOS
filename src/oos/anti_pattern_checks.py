from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping

from .models import IdeaVariant
from .pattern_guided_ideation import PatternGuidedIdea


SEVERITIES = {"low", "medium", "high"}


@dataclass(frozen=True)
class AntiPatternFinding:
    idea_id: str
    anti_pattern_id: str
    label: str
    severity: str
    explanation: str
    evidence: List[str]
    matched_fields: List[str]
    recommendation: str
    penalty: int

    def validate(self) -> None:
        for field_name in ("idea_id", "anti_pattern_id", "label", "severity", "explanation", "recommendation"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.severity not in SEVERITIES:
            raise ValueError("severity must be low, medium, or high")
        if not isinstance(self.evidence, list) or not self.evidence:
            raise ValueError("evidence must be a non-empty list")
        if not isinstance(self.matched_fields, list) or not self.matched_fields:
            raise ValueError("matched_fields must be a non-empty list")
        if not isinstance(self.penalty, int) or self.penalty > 0:
            raise ValueError("penalty must be a non-positive integer")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class AntiPatternCheckResult:
    idea_id: str
    findings: List[AntiPatternFinding]
    total_penalty: int
    has_high_severity: bool
    genericness_penalty: int

    def validate(self) -> None:
        if not isinstance(self.idea_id, str) or not self.idea_id.strip():
            raise ValueError("idea_id must be a non-empty string")
        for finding in self.findings:
            finding.validate()
        if not isinstance(self.total_penalty, int) or self.total_penalty > 0:
            raise ValueError("total_penalty must be a non-positive integer")
        if self.genericness_penalty not in {0, -1, -2}:
            raise ValueError("genericness_penalty must be 0, -1, or -2")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "idea_id": self.idea_id,
            "findings": [finding.to_dict() for finding in self.findings],
            "total_penalty": self.total_penalty,
            "has_high_severity": self.has_high_severity,
            "genericness_penalty": self.genericness_penalty,
        }


@dataclass(frozen=True)
class AntiPatternSummary:
    results: List[AntiPatternCheckResult]
    total_findings: int
    ideas_with_high_severity: List[str]
    total_penalty_by_idea_id: Dict[str, int]

    def validate(self) -> None:
        for result in self.results:
            result.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "results": [result.to_dict() for result in self.results],
            "total_findings": self.total_findings,
            "ideas_with_high_severity": list(self.ideas_with_high_severity),
            "total_penalty_by_idea_id": dict(self.total_penalty_by_idea_id),
        }


@dataclass(frozen=True)
class AntiPatternRule:
    anti_pattern_id: str
    label: str
    severity: str
    fields: List[str]
    keywords: List[str]
    explanation: str
    recommendation: str
    penalty: int


ANTI_PATTERN_RULES = [
    AntiPatternRule(
        anti_pattern_id="generic_dashboard",
        label="Generic dashboard",
        severity="medium",
        fields=["idea_title", "product_concept", "wedge"],
        keywords=["generic dashboard", "dashboard", "analytics dashboard"],
        explanation="Dashboard language is often a shallow packaging move unless tied to a specific workflow wedge.",
        recommendation="Replace generic dashboard framing with a specific workflow, decision, or failure mode.",
        penalty=-1,
    ),
    AntiPatternRule(
        anti_pattern_id="generic_chatbot",
        label="Generic chatbot",
        severity="medium",
        fields=["idea_title", "product_concept", "wedge"],
        keywords=["generic chatbot", "chatbot", "chat bot"],
        explanation="Chatbot framing is too generic without a narrow job, evidence trail, and buyer.",
        recommendation="Define the job-to-be-done and why chat is the right interface.",
        penalty=-1,
    ),
    AntiPatternRule(
        anti_pattern_id="generic_ai_assistant",
        label="Generic AI assistant",
        severity="medium",
        fields=["idea_title", "product_concept", "wedge"],
        keywords=["generic ai assistant", "ai assistant", "assistant for everyone", "copilot for everyone"],
        explanation="AI assistant language is broad and can hide weak product specificity.",
        recommendation="Constrain the assistant to a specific workflow, user, and first experiment.",
        penalty=-1,
    ),
    AntiPatternRule(
        anti_pattern_id="uber_for_x",
        label="Uber for X",
        severity="medium",
        fields=["idea_title", "product_concept"],
        keywords=["uber for"],
        explanation="Uber-for-X framing often skips buyer urgency, supply constraints, and operational density.",
        recommendation="State the brokered workflow mechanics and why this marketplace can exist now.",
        penalty=-1,
    ),
    AntiPatternRule(
        anti_pattern_id="pure_consulting_disguised_as_product",
        label="Pure consulting disguised as product",
        severity="high",
        fields=["product_concept", "business_model_options", "first_experiment"],
        keywords=["consulting", "agency", "bespoke", "custom consulting", "done-for-you consulting"],
        explanation="The idea appears to sell custom labor rather than a repeatable productized workflow.",
        recommendation="Productize the repeatable part or park the idea before council spend.",
        penalty=-2,
    ),
    AntiPatternRule(
        anti_pattern_id="founder_time_heavy_service",
        label="Founder-time-heavy service",
        severity="high",
        fields=["product_concept", "first_experiment", "risks"],
        keywords=["founder manually", "founder does", "white-glove by founder", "concierge by founder"],
        explanation="The idea depends on founder labor, which creates scaling and bottleneck risk.",
        recommendation="Identify the automatable workflow or require founder review before proceeding.",
        penalty=-2,
    ),
]


UNCLEAR_BUYER_TERMS = {"", "everyone", "anyone", "users", "businesses", "companies", "teams"}
NO_URGENCY_TERMS = {"", "nice to have", "minor inconvenience", "not urgent", "someday", "eventually"}
UNCLEAR_EXPERIMENT_TERMS = {"", "tbd", "research more", "figure it out", "explore options", "talk to people"}


def check_anti_patterns(ideas: Iterable[Any]) -> AntiPatternSummary:
    results = [check_idea_for_anti_patterns(idea) for idea in ideas]
    return AntiPatternSummary(
        results=results,
        total_findings=sum(len(result.findings) for result in results),
        ideas_with_high_severity=[result.idea_id for result in results if result.has_high_severity],
        total_penalty_by_idea_id={result.idea_id: result.total_penalty for result in results},
    )


def check_idea_for_anti_patterns(idea: Any) -> AntiPatternCheckResult:
    data = _idea_fields(idea)
    idea_id = data["idea_id"] or "unknown_idea"
    findings: List[AntiPatternFinding] = []
    for rule in ANTI_PATTERN_RULES:
        evidence, matched_fields = _match_rule(rule, data)
        if evidence:
            findings.append(
                AntiPatternFinding(
                    idea_id=idea_id,
                    anti_pattern_id=rule.anti_pattern_id,
                    label=rule.label,
                    severity=rule.severity,
                    explanation=rule.explanation,
                    evidence=evidence,
                    matched_fields=matched_fields,
                    recommendation=rule.recommendation,
                    penalty=rule.penalty,
                )
            )
    findings.extend(_structural_findings(idea_id, data))
    genericness_penalty = compute_genericness_penalty_from_text(" ".join(data.values()))
    total_penalty = min(0, sum(finding.penalty for finding in findings) + genericness_penalty)
    result = AntiPatternCheckResult(
        idea_id=idea_id,
        findings=findings,
        total_penalty=total_penalty,
        has_high_severity=any(finding.severity == "high" for finding in findings),
        genericness_penalty=genericness_penalty,
    )
    result.validate()
    return result


def compute_genericness_penalty(idea: Any) -> int:
    return compute_genericness_penalty_from_text(" ".join(_idea_fields(idea).values()))


def compute_genericness_penalty_from_text(text: str) -> int:
    normalized = _normalize(text)
    generic_hits = [
        phrase
        for phrase in (
            "generic dashboard",
            "dashboard",
            "generic assistant",
            "generic ai assistant",
            "ai assistant",
            "chatbot",
            "vague saas",
            "better saas",
        )
        if phrase in normalized
    ]
    if len(generic_hits) >= 2:
        return -2
    if len(generic_hits) == 1:
        return -1
    return 0


def _match_rule(rule: AntiPatternRule, data: Mapping[str, str]) -> tuple[List[str], List[str]]:
    evidence: List[str] = []
    matched_fields: List[str] = []
    for field_name in rule.fields:
        value = _normalize(data.get(field_name, ""))
        for keyword in rule.keywords:
            if keyword in value:
                evidence.append(keyword)
                matched_fields.append(field_name)
                break
    return evidence, matched_fields


def _structural_findings(idea_id: str, data: Mapping[str, str]) -> List[AntiPatternFinding]:
    findings: List[AntiPatternFinding] = []
    target_user = _normalize(data["target_user"])
    pain = _normalize(data["pain_addressed"])
    first_experiment = _normalize(data["first_experiment"])
    if target_user in UNCLEAR_BUYER_TERMS:
        findings.append(
            AntiPatternFinding(
                idea_id=idea_id,
                anti_pattern_id="unclear_buyer",
                label="Unclear buyer",
                severity="high",
                explanation="The idea does not name a concrete buyer or user segment.",
                evidence=[data["target_user"] or "<missing>"],
                matched_fields=["target_user"],
                recommendation="Name the buyer and user before sending this idea to council.",
                penalty=-2,
            )
        )
    if pain in NO_URGENCY_TERMS or any(term in pain for term in NO_URGENCY_TERMS if term):
        findings.append(
            AntiPatternFinding(
                idea_id=idea_id,
                anti_pattern_id="no_urgent_pain",
                label="No urgent pain",
                severity="high",
                explanation="The pain reads as weak, non-urgent, or missing.",
                evidence=[data["pain_addressed"] or "<missing>"],
                matched_fields=["pain_addressed"],
                recommendation="Find evidence of urgency, cost, or active workaround before proceeding.",
                penalty=-2,
            )
        )
    if first_experiment in UNCLEAR_EXPERIMENT_TERMS or any(term in first_experiment for term in UNCLEAR_EXPERIMENT_TERMS if term):
        findings.append(
            AntiPatternFinding(
                idea_id=idea_id,
                anti_pattern_id="no_clear_first_experiment",
                label="No clear first experiment",
                severity="medium",
                explanation="The first experiment is missing or too vague to execute.",
                evidence=[data["first_experiment"] or "<missing>"],
                matched_fields=["first_experiment"],
                recommendation="Define a concrete first test with a user, action, and success signal.",
                penalty=-1,
            )
        )
    return findings


def _idea_fields(idea: Any) -> Dict[str, str]:
    if isinstance(idea, PatternGuidedIdea):
        return {
            "idea_id": idea.idea_id,
            "idea_title": idea.idea_title,
            "target_user": idea.target_user,
            "pain_addressed": idea.pain_addressed,
            "product_concept": idea.product_concept,
            "wedge": idea.wedge,
            "business_model_options": " ".join(idea.business_model_options),
            "first_experiment": idea.first_experiment,
            "risks": " ".join(idea.risks),
        }
    if isinstance(idea, IdeaVariant):
        return {
            "idea_id": idea.id,
            "idea_title": idea.short_concept,
            "target_user": "legacy target user",
            "pain_addressed": idea.short_concept,
            "product_concept": idea.short_concept,
            "wedge": idea.standardization_focus,
            "business_model_options": idea.business_model,
            "first_experiment": idea.ai_leverage,
            "risks": idea.external_execution_needed,
        }
    if isinstance(idea, Mapping):
        return {
            "idea_id": str(idea.get("idea_id") or idea.get("id") or "").strip(),
            "idea_title": str(idea.get("idea_title") or idea.get("title") or idea.get("short_concept") or "").strip(),
            "target_user": str(idea.get("target_user") or idea.get("buyer") or "").strip(),
            "pain_addressed": str(idea.get("pain_addressed") or idea.get("pain") or "").strip(),
            "product_concept": str(idea.get("product_concept") or idea.get("concept") or idea.get("short_concept") or "").strip(),
            "wedge": str(idea.get("wedge") or "").strip(),
            "business_model_options": " ".join(str(value) for value in idea.get("business_model_options", []))
            if isinstance(idea.get("business_model_options"), list)
            else str(idea.get("business_model_options") or idea.get("business_model") or "").strip(),
            "first_experiment": str(idea.get("first_experiment") or "").strip(),
            "risks": " ".join(str(value) for value in idea.get("risks", []))
            if isinstance(idea.get("risks"), list)
            else str(idea.get("risks") or "").strip(),
        }
    return {
        "idea_id": str(getattr(idea, "idea_id", getattr(idea, "id", ""))).strip(),
        "idea_title": str(getattr(idea, "idea_title", getattr(idea, "short_concept", ""))).strip(),
        "target_user": str(getattr(idea, "target_user", "")).strip(),
        "pain_addressed": str(getattr(idea, "pain_addressed", "")).strip(),
        "product_concept": str(getattr(idea, "product_concept", "")).strip(),
        "wedge": str(getattr(idea, "wedge", "")).strip(),
        "business_model_options": str(getattr(idea, "business_model_options", "")).strip(),
        "first_experiment": str(getattr(idea, "first_experiment", "")).strip(),
        "risks": str(getattr(idea, "risks", "")).strip(),
    }


def _normalize(value: str) -> str:
    return " ".join(str(value).lower().split())
