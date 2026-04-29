from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from .llm_contracts import LLMMessage, LLMRequest


PII_TYPE_EMAIL = "email"
PII_TYPE_PHONE = "phone"
PII_TYPE_URL = "url"
PII_TYPE_IPV4 = "ipv4"
PII_TYPE_CREDIT_CARD = "credit_card"
PII_TYPE_ISRAELI_ID = "israeli_id"
PII_TYPE_IBAN = "iban"
PII_TYPE_BANK_ACCOUNT = "bank_account"
PII_TYPE_SECRET = "secret"
PII_TYPE_PRIVATE_KEY = "private_key"

DEFAULT_BLOCKED_PII_TYPES = [
    PII_TYPE_SECRET,
    PII_TYPE_PRIVATE_KEY,
    PII_TYPE_CREDIT_CARD,
]

_PII_REPLACEMENTS = {
    PII_TYPE_EMAIL: "[EMAIL_REDACTED]",
    PII_TYPE_PHONE: "[PHONE_REDACTED]",
    PII_TYPE_URL: "[URL_REDACTED]",
    PII_TYPE_IPV4: "[IP_REDACTED]",
    PII_TYPE_CREDIT_CARD: "[CARD_REDACTED]",
    PII_TYPE_ISRAELI_ID: "[ISRAELI_ID_REDACTED]",
    PII_TYPE_IBAN: "[IBAN_REDACTED]",
    PII_TYPE_BANK_ACCOUNT: "[BANK_ACCOUNT_REDACTED]",
    PII_TYPE_SECRET: "[SECRET_REDACTED]",
    PII_TYPE_PRIVATE_KEY: "[SECRET_REDACTED]",
}

_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("openai_api_key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("github_personal_access_token", re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b")),
    ("github_fine_grained_token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("slack_bot_token", re.compile(r"\bxoxb-[A-Za-z0-9-]{10,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
]

_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)
_URL_RE = re.compile(r"\bhttps?://[^\s<>()\[\]{}\"']+|\bwww\.[^\s<>()\[\]{}\"']+")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_LONG_DIGIT_RE = re.compile(r"(?<!\d)(?:\d[ -]?){9,19}\d(?!\d)")
_NINE_DIGIT_RE = re.compile(r"(?<!\d)\d{9}(?!\d)")


@dataclass(frozen=True)
class PIIFinding:
    pii_type: str
    start: int
    end: int
    original_text: str
    replacement: str
    confidence: float
    detection_method: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PIIRedactionResult:
    original_text: str
    redacted_text: str
    findings: list[PIIFinding] = field(default_factory=list)
    redaction_count: int = 0
    contains_pii: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptSafetyPolicy:
    redact_pii: bool = True
    block_on_pii_types: list[str] = field(default_factory=lambda: list(DEFAULT_BLOCKED_PII_TYPES))
    max_prompt_chars: int = 12_000
    allow_urls: bool = False
    allow_emails: bool = False
    allow_phone_numbers: bool = False
    allow_person_names: bool = False
    require_redaction_before_llm: bool = True
    fail_closed: bool = True
    policy_name: str = "default_prompt_safety_policy"


@dataclass(frozen=True)
class PromptSafetyReport:
    is_safe: bool
    blocked: bool
    block_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    pii_findings: list[PIIFinding] = field(default_factory=list)
    redacted_text: str = ""
    policy_name: str = "default_prompt_safety_policy"
    external_calls_made: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["pii_findings"] = [finding.to_dict() for finding in self.pii_findings]
        return data


def default_prompt_safety_policy() -> PromptSafetyPolicy:
    return PromptSafetyPolicy()


def local_preview_prompt_safety_policy() -> PromptSafetyPolicy:
    return PromptSafetyPolicy(
        redact_pii=True,
        block_on_pii_types=list(DEFAULT_BLOCKED_PII_TYPES),
        max_prompt_chars=12_000,
        allow_urls=True,
        allow_emails=False,
        allow_phone_numbers=False,
        allow_person_names=False,
        require_redaction_before_llm=True,
        fail_closed=True,
        policy_name="local_preview_prompt_safety_policy",
    )


def redact_pii(text: str) -> PIIRedactionResult:
    original_text = text or ""
    findings = _find_pii(original_text)
    redacted_text = _apply_redactions(original_text, findings)
    return PIIRedactionResult(
        original_text=original_text,
        redacted_text=redacted_text,
        findings=findings,
        redaction_count=len(findings),
        contains_pii=bool(findings),
    )


def evaluate_prompt_safety(text: str, policy: PromptSafetyPolicy | None = None) -> PromptSafetyReport:
    active_policy = policy or default_prompt_safety_policy()
    redaction = redact_pii(text or "")
    safe_text = redaction.redacted_text if active_policy.redact_pii else redaction.original_text
    block_reasons: list[str] = []
    warnings: list[str] = []

    if len(safe_text) > active_policy.max_prompt_chars:
        block_reasons.append("max_prompt_chars_exceeded")

    for finding in redaction.findings:
        if finding.pii_type in active_policy.block_on_pii_types:
            block_reasons.append(f"blocked_pii_type:{finding.pii_type}")
        elif finding.pii_type == PII_TYPE_URL and not active_policy.allow_urls:
            warnings.append("url_redacted")
        elif finding.pii_type == PII_TYPE_EMAIL and not active_policy.allow_emails:
            warnings.append("email_redacted")
        elif finding.pii_type == PII_TYPE_PHONE and not active_policy.allow_phone_numbers:
            warnings.append("phone_redacted")

    if active_policy.require_redaction_before_llm and redaction.contains_pii and not active_policy.redact_pii:
        block_reasons.append("redaction_required_before_llm")

    block_reasons = _dedupe(block_reasons)
    warnings = _dedupe(warnings)
    blocked = bool(block_reasons) and active_policy.fail_closed
    return PromptSafetyReport(
        is_safe=not blocked,
        blocked=blocked,
        block_reasons=block_reasons,
        warnings=warnings,
        pii_findings=redaction.findings,
        redacted_text=safe_text,
        policy_name=active_policy.policy_name,
        external_calls_made=False,
    )


def build_safe_llm_messages(
    messages: list[LLMMessage],
    policy: PromptSafetyPolicy | None = None,
) -> tuple[list[LLMMessage], PromptSafetyReport]:
    separator = "\n\n---MESSAGE---\n\n"
    combined_text = separator.join(message.content for message in messages)
    report = evaluate_prompt_safety(combined_text, policy=policy)
    if report.blocked:
        return [], report

    safe_messages: list[LLMMessage] = []
    for message in messages:
        redaction = redact_pii(message.content)
        safe_messages.append(
            LLMMessage(
                role=message.role,
                content=redaction.redacted_text if (policy or default_prompt_safety_policy()).redact_pii else message.content,
            )
        )
    return safe_messages, report


def build_safe_llm_request(
    request: LLMRequest,
    policy: PromptSafetyPolicy | None = None,
) -> tuple[LLMRequest | None, PromptSafetyReport]:
    safe_messages, report = build_safe_llm_messages(request.messages, policy=policy)
    if report.blocked:
        return None, report

    safety_summary: dict[str, object] = {
        "policy_name": report.policy_name,
        "redaction_count": len(report.pii_findings),
        "blocked": report.blocked,
        "warnings": list(report.warnings),
        "external_calls_made": False,
    }
    metadata = dict(request.metadata)
    metadata["prompt_safety"] = safety_summary
    safe_request = replace(request, messages=safe_messages, metadata=metadata)
    return safe_request, report


def prompt_safety_envelope_text() -> str:
    return "\n".join(
        [
            "Prompt safety envelope:",
            "- Use only the provided redacted evidence excerpt.",
            "- Apply an asymmetric prior: default recommendation is review, not advance.",
            "- Do not invent facts, identities, sources, prices, or claims.",
            "- Cite evidence_id when available.",
            "- Structured review outputs must set evidence_cited = true only when evidence is cited.",
        ]
    )


def build_prompt_safety_envelope_message() -> LLMMessage:
    return LLMMessage(role="system", content=prompt_safety_envelope_text())


def _find_pii(text: str) -> list[PIIFinding]:
    candidates: list[PIIFinding] = []

    for match in _PRIVATE_KEY_RE.finditer(text):
        candidates.append(_finding(PII_TYPE_PRIVATE_KEY, match, 0.99, "private_key_regex"))
    for method, pattern in _SECRET_PATTERNS:
        for match in pattern.finditer(text):
            candidates.append(_finding(PII_TYPE_SECRET, match, 0.98, method))
    for match in _URL_RE.finditer(text):
        candidates.append(_finding(PII_TYPE_URL, match, 0.95, "url_regex"))
    for match in _EMAIL_RE.finditer(text):
        candidates.append(_finding(PII_TYPE_EMAIL, match, 0.95, "email_regex"))
    for match in _IPV4_RE.finditer(text):
        if _valid_ipv4(match.group(0)):
            candidates.append(_finding(PII_TYPE_IPV4, match, 0.9, "ipv4_regex"))
    for match in _IBAN_RE.finditer(text):
        candidates.append(_finding(PII_TYPE_IBAN, match, 0.9, "iban_regex"))
    for match in _LONG_DIGIT_RE.finditer(text):
        raw_value = match.group(0)
        normalized = _digits_only(match.group(0))
        if 13 <= len(normalized) <= 19 and _passes_luhn(normalized):
            candidates.append(_finding(PII_TYPE_CREDIT_CARD, match, 0.95, "luhn_check"))
        elif len(normalized) >= 10 and not (
            any(marker in raw_value for marker in ("+", "(", ")"))
            or (len(normalized) <= 15 and any(marker in raw_value for marker in ("-", " ")))
        ):
            candidates.append(_finding(PII_TYPE_BANK_ACCOUNT, match, 0.65, "long_digit_sequence"))
    for match in _NINE_DIGIT_RE.finditer(text):
        if _valid_israeli_id(match.group(0)):
            candidates.append(_finding(PII_TYPE_ISRAELI_ID, match, 0.85, "israeli_id_checksum"))

    return _dedupe_overlapping_findings(text, candidates)


def _finding(pii_type: str, match: re.Match[str], confidence: float, detection_method: str) -> PIIFinding:
    return PIIFinding(
        pii_type=pii_type,
        start=match.start(),
        end=match.end(),
        original_text=match.group(0),
        replacement=_PII_REPLACEMENTS[pii_type],
        confidence=confidence,
        detection_method=detection_method,
    )


def _apply_redactions(text: str, findings: list[PIIFinding]) -> str:
    if not findings:
        return text
    chunks: list[str] = []
    cursor = 0
    for finding in sorted(findings, key=lambda item: item.start):
        chunks.append(text[cursor : finding.start])
        chunks.append(finding.replacement)
        cursor = finding.end
    chunks.append(text[cursor:])
    return "".join(chunks)


def _dedupe_overlapping_findings(text: str, findings: list[PIIFinding]) -> list[PIIFinding]:
    priority = {
        PII_TYPE_PRIVATE_KEY: 0,
        PII_TYPE_SECRET: 1,
        PII_TYPE_CREDIT_CARD: 2,
        PII_TYPE_IBAN: 3,
        PII_TYPE_EMAIL: 4,
        PII_TYPE_URL: 5,
        PII_TYPE_IPV4: 6,
        PII_TYPE_ISRAELI_ID: 7,
        PII_TYPE_BANK_ACCOUNT: 8,
        PII_TYPE_PHONE: 9,
    }
    selected: list[PIIFinding] = []
    for finding in sorted(
        findings,
        key=lambda item: (item.start, priority.get(item.pii_type, 99), -(item.end - item.start)),
    ):
        if any(not (finding.end <= existing.start or finding.start >= existing.end) for existing in selected):
            continue
        selected.append(finding)

    masked_text = _mask_selected_spans(text, selected)
    for match in _PHONE_RE.finditer(masked_text):
        normalized = _digits_only(match.group(0))
        if 8 <= len(normalized) <= 15:
            selected.append(_finding(PII_TYPE_PHONE, match, 0.8, "phone_regex"))

    return sorted(selected, key=lambda item: item.start)


def _valid_ipv4(value: str) -> bool:
    try:
        return all(0 <= int(part) <= 255 for part in value.split("."))
    except ValueError:
        return False


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value)


def _passes_luhn(value: str) -> bool:
    digits = [int(character) for character in value if character.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _valid_israeli_id(value: str) -> bool:
    if not re.fullmatch(r"\d{9}", value):
        return False
    total = 0
    for index, character in enumerate(value):
        digit = int(character)
        step = digit * (1 if index % 2 == 0 else 2)
        total += step if step < 10 else step - 9
    return total % 10 == 0


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _mask_selected_spans(text: str, findings: list[PIIFinding]) -> str:
    if not findings:
        return text
    characters = list(text)
    for finding in findings:
        for index in range(finding.start, finding.end):
            characters[index] = " "
    return "".join(characters)
