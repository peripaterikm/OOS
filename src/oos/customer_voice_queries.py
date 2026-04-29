from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable

QUERY_KIND_CUSTOMER_VOICE = "customer_voice_query"
GENERATION_METHOD_DETERMINISTIC_SEED = "deterministic_seed"
GENERATION_METHOD_LLM_GENERATED_FUTURE = "llm_generated_future"
APPROVAL_STATE_PROPOSED = "proposed"
APPROVAL_STATE_APPROVED = "approved"
APPROVAL_STATE_REJECTED = "rejected"
APPROVAL_STATE_RETIRED = "retired"

QUERY_INTENTS = {
    "pain",
    "workaround",
    "buying_intent",
    "how_to",
    "comparison",
    "urgent_problem",
    "job_to_be_done",
}

APPROVAL_STATES = {
    APPROVAL_STATE_PROPOSED,
    APPROVAL_STATE_APPROVED,
    APPROVAL_STATE_REJECTED,
    APPROVAL_STATE_RETIRED,
}

CUSTOMER_VOICE_QUERY_PROMPT_CONTRACT = """
Customer Voice Query Generator prompt contract, disabled by default.

Goal: propose customer-language search queries for a topic and persona without
collapsing every topic into the founder/owner viewpoint.

Instructions:
- Generate queries in the words a real customer/operator might type or post.
- Cover multiple personas in the topic, not only the economic buyer.
- Include explicit pain, workaround, buying intent, how-to, comparison,
  urgent problem, and job-to-be-done angles where appropriate.
- Avoid overfitting to known examples; propose adjacent language variants.
- Preserve topic_id, persona_id, source fit, rationale, and approval_state.
- Set generation_method to llm_generated_future only when a live LLM provider is
  explicitly enabled by a future roadmap item.
- Default all generated queries to approval_state=proposed; never activate them
  for collection without founder approval.
""".strip()


@dataclass(frozen=True)
class CustomerVoicePersona:
    persona_id: str
    topic_id: str
    segment: str
    role_label: str
    pain_language_style: str
    typical_contexts: list[str]
    typical_tools: list[str]
    source_fit: list[str]
    is_active: bool
    priority: int = 100

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CustomerVoiceQuery:
    query_id: str
    topic_id: str
    persona_id: str
    query_text: str
    query_kind: str
    query_intent: str
    expected_source_fit: list[str]
    language: str
    generation_method: str
    priority: int
    rationale: str
    tags: list[str]
    approval_state: str = APPROVAL_STATE_PROPOSED

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def validate(self) -> None:
        for field_name in (
            "query_id",
            "topic_id",
            "persona_id",
            "query_text",
            "query_kind",
            "query_intent",
            "language",
            "generation_method",
            "rationale",
            "approval_state",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"CustomerVoiceQuery.{field_name} must be a non-empty string")
        if self.query_kind != QUERY_KIND_CUSTOMER_VOICE:
            raise ValueError("CustomerVoiceQuery.query_kind must be customer_voice_query")
        if self.query_intent not in QUERY_INTENTS:
            raise ValueError(f"Unsupported CustomerVoiceQuery.query_intent: {self.query_intent}")
        if self.approval_state not in APPROVAL_STATES:
            raise ValueError(f"Unsupported CustomerVoiceQuery.approval_state: {self.approval_state}")
        if not self.expected_source_fit:
            raise ValueError("CustomerVoiceQuery.expected_source_fit must be non-empty")
        if not isinstance(self.tags, list):
            raise ValueError("CustomerVoiceQuery.tags must be a list")


@dataclass(frozen=True)
class _QuerySeed:
    text: str
    intent: str
    source_fit: tuple[str, ...]
    rationale: str
    tags: tuple[str, ...]


_COMMON_FINANCE_SOURCES = ("hacker_news_algolia", "github_issues", "stack_exchange", "reddit")
_HOW_TO_SOURCES = ("stack_exchange", "reddit", "github_issues")
_OPERATOR_SOURCES = ("hacker_news_algolia", "reddit", "github_issues")

_PERSONAS: tuple[CustomerVoicePersona, ...] = (
    CustomerVoicePersona(
        persona_id="smb_owner",
        topic_id="ai_cfo_smb",
        segment="Small business owner / founder / CEO",
        role_label="owner/founder/CEO",
        pain_language_style="Strategic anxiety about cash visibility, affordability, and where money went.",
        typical_contexts=["hiring decisions", "late customer payments", "cash position reviews", "owner reporting"],
        typical_tools=["QuickBooks", "Xero", "bank portal", "spreadsheet"],
        source_fit=["hacker_news_algolia", "reddit", "github_issues"],
        is_active=True,
        priority=10,
    ),
    CustomerVoicePersona(
        persona_id="bookkeeper",
        topic_id="ai_cfo_smb",
        segment="Bookkeeper supporting small-business operations",
        role_label="bookkeeper",
        pain_language_style="Operational cleanup, reconciliation, receipts, invoices, and close-cycle friction.",
        typical_contexts=["bank reconciliation", "month-end close", "receipt collection", "invoice tracking"],
        typical_tools=["QuickBooks", "Xero", "Excel", "Google Sheets", "receipt inbox"],
        source_fit=["stack_exchange", "github_issues", "reddit"],
        is_active=True,
        priority=20,
    ),
    CustomerVoicePersona(
        persona_id="accountant",
        topic_id="ai_cfo_smb",
        segment="Accountant serving SMB clients",
        role_label="accountant",
        pain_language_style="Client document chaos, compliance, reporting, and cleanup workload.",
        typical_contexts=["client cleanup", "management reports", "tax prep", "month-end review"],
        typical_tools=["QuickBooks", "Xero", "Excel", "client portal"],
        source_fit=["stack_exchange", "github_issues", "reddit"],
        is_active=True,
        priority=30,
    ),
    CustomerVoicePersona(
        persona_id="fractional_cfo",
        topic_id="ai_cfo_smb",
        segment="Fractional CFO / finance advisor",
        role_label="fractional CFO",
        pain_language_style="Management reporting, forecasting, owner explanations, and source consolidation.",
        typical_contexts=["forecasting", "board packet", "cash flow explanation", "data consolidation"],
        typical_tools=["QuickBooks", "Xero", "NetSuite", "spreadsheets", "BI export"],
        source_fit=["hacker_news_algolia", "github_issues", "reddit"],
        is_active=True,
        priority=40,
    ),
    CustomerVoicePersona(
        persona_id="finance_manager",
        topic_id="ai_cfo_smb",
        segment="Finance manager in a growing SMB",
        role_label="finance manager",
        pain_language_style="Cash planning, AP/AR, budgets, reporting, and spreadsheet workflow strain.",
        typical_contexts=["weekly cash planning", "AP/AR reviews", "budget updates", "cash report maintenance"],
        typical_tools=["Excel", "Google Sheets", "QuickBooks", "Xero", "ERP exports"],
        source_fit=["github_issues", "stack_exchange", "reddit"],
        is_active=True,
        priority=50,
    ),
    CustomerVoicePersona(
        persona_id="operations_manager",
        topic_id="ai_cfo_smb",
        segment="Operations manager coordinating finance-adjacent workflows",
        role_label="operations manager",
        pain_language_style="Supplier bills, customer payments, project budgets, and cross-system process gaps.",
        typical_contexts=["supplier bills", "customer payments", "project budget tracking", "sales-finance handoffs"],
        typical_tools=["spreadsheet", "project tracker", "CRM", "accounting software"],
        source_fit=["hacker_news_algolia", "github_issues", "reddit"],
        is_active=True,
        priority=60,
    ),
    CustomerVoicePersona(
        persona_id="freelancer_solo_operator",
        topic_id="ai_cfo_smb",
        segment="Freelancer / solo operator with business-finance pain",
        role_label="freelancer / solo operator",
        pain_language_style="Irregular income, late clients, tax set-aside, and personal/business money separation.",
        typical_contexts=["invoice follow-up", "tax set-aside", "bill planning", "personal/business separation"],
        typical_tools=["spreadsheet", "bank app", "invoicing tool", "QuickBooks Self-Employed"],
        source_fit=["hacker_news_algolia", "github_issues", "reddit"],
        is_active=True,
        priority=70,
    ),
    CustomerVoicePersona(
        persona_id="household_budgeter_stub",
        topic_id="personal_finance_household",
        segment="Household budget manager",
        role_label="household budgeter",
        pain_language_style="Future inactive stub for household cash flow and bills language.",
        typical_contexts=["rent", "groceries", "family budget", "debt payoff"],
        typical_tools=["spreadsheet", "bank app", "budgeting app"],
        source_fit=["reddit", "rss_feed"],
        is_active=False,
        priority=10,
    ),
    CustomerVoicePersona(
        persona_id="solo_finance_stub",
        topic_id="freelancer_solo_finance",
        segment="Solo worker / freelancer finance",
        role_label="solo operator",
        pain_language_style="Future inactive stub for irregular income and tax-planning pain.",
        typical_contexts=["late clients", "quarterly taxes", "bill planning"],
        typical_tools=["spreadsheet", "invoicing tool", "bank app"],
        source_fit=["reddit", "hacker_news_algolia", "github_issues"],
        is_active=False,
        priority=10,
    ),
    CustomerVoicePersona(
        persona_id="immigrant_finance_israel_stub",
        topic_id="immigrant_finance_israel",
        segment="Immigrant household/operator navigating Israeli finance",
        role_label="immigrant finance user",
        pain_language_style="Future inactive stub for multilingual banking, tax, salary, and bureaucracy pain.",
        typical_contexts=["bank account setup", "tax forms", "salary slips", "currency transfer"],
        typical_tools=["bank app", "government portal", "spreadsheet"],
        source_fit=["reddit", "rss_feed"],
        is_active=False,
        priority=10,
    ),
)

_QUERY_SEEDS: dict[str, tuple[_QuerySeed, ...]] = {
    "smb_owner": (
        _QuerySeed("why am I profitable but have no cash", "pain", _OPERATOR_SOURCES, "Owner language for profit/cash mismatch pain.", ("cash_flow", "owner", "visibility")),
        _QuerySeed("clients pay late and I can't pay suppliers", "urgent_problem", _COMMON_FINANCE_SOURCES, "Late AR creates supplier-payment urgency.", ("late_payments", "suppliers", "cash_flow")),
        _QuerySeed("how do I know if my small business can afford a new hire", "job_to_be_done", _OPERATOR_SOURCES, "Affordability decision phrased as an owner job.", ("hiring", "cash_planning", "owner")),
        _QuerySeed("I don't understand where the money went this month", "pain", _OPERATOR_SOURCES, "Direct cash-visibility frustration.", ("cash_visibility", "owner", "monthly_review")),
        _QuerySeed("accountant sends reports but I still don't know cash position", "pain", _OPERATOR_SOURCES, "Reports exist but owner cannot answer cash question.", ("reports", "cash_position", "accountant")),
    ),
    "bookkeeper": (
        _QuerySeed("how to reconcile bank transactions with invoices faster", "how_to", _HOW_TO_SOURCES, "Bookkeeper searches for a faster reconciliation workflow.", ("reconciliation", "invoices", "workflow")),
        _QuerySeed("client sends receipts late every month what to do", "pain", ("stack_exchange", "reddit"), "Recurring client-document collection pain.", ("receipts", "client_documents", "month_end")),
        _QuerySeed("best way to track unpaid invoices for small business", "how_to", _HOW_TO_SOURCES, "Practical unpaid-invoice tracking language.", ("unpaid_invoices", "tracking", "smb")),
        _QuerySeed("spreadsheet for monthly close bookkeeping", "workaround", ("stack_exchange", "github_issues", "reddit"), "Spreadsheet workaround for close workflow.", ("spreadsheet", "monthly_close", "bookkeeping")),
        _QuerySeed("automate matching payments to invoices", "buying_intent", ("github_issues", "stack_exchange", "reddit"), "Automation intent around payment matching.", ("automation", "payments", "invoices")),
    ),
    "accountant": (
        _QuerySeed("small business client books are always messy", "pain", ("reddit", "stack_exchange", "hacker_news_algolia"), "Accountant pain about recurring cleanup work.", ("cleanup", "client_books", "accountant")),
        _QuerySeed("how to clean up client bookkeeping faster", "how_to", _HOW_TO_SOURCES, "Workflow-improvement query for cleanup speed.", ("cleanup", "bookkeeping", "workflow")),
        _QuerySeed("clients ask for cash flow report from QuickBooks", "job_to_be_done", ("stack_exchange", "github_issues", "reddit"), "Client request for cash-flow reporting from accounting software.", ("cash_flow", "quickbooks", "reporting")),
        _QuerySeed("prepare management report from accounting software and spreadsheets", "how_to", ("stack_exchange", "github_issues", "reddit"), "Management-report preparation from multiple tools.", ("management_reporting", "spreadsheets", "accounting_software")),
        _QuerySeed("client documents missing before tax deadline", "urgent_problem", ("reddit", "stack_exchange"), "Deadline-driven document collection pain.", ("tax", "deadline", "client_documents")),
    ),
    "fractional_cfo": (
        _QuerySeed("build monthly cash flow forecast from QuickBooks and spreadsheets", "how_to", ("github_issues", "stack_exchange", "reddit"), "Forecast assembly across QuickBooks and spreadsheets.", ("cash_flow_forecast", "quickbooks", "spreadsheet")),
        _QuerySeed("automate management reporting for small business clients", "buying_intent", ("hacker_news_algolia", "github_issues", "reddit"), "Automation/buying-intent language for reporting.", ("automation", "management_reporting", "clients")),
        _QuerySeed("consolidate P&L cash flow balance sheet from multiple sources", "job_to_be_done", ("github_issues", "stack_exchange", "reddit"), "Consolidation job across core financial statements.", ("consolidation", "p_l", "cash_flow", "balance_sheet")),
        _QuerySeed("explain cash flow to business owner simply", "job_to_be_done", ("hacker_news_algolia", "reddit"), "Communication job for owner-facing finance explanation.", ("cash_flow", "owner_explanation", "fractional_cfo")),
        _QuerySeed("forecast is wrong because accounting data is late", "pain", ("hacker_news_algolia", "github_issues", "reddit"), "Forecast quality pain caused by delayed accounting data.", ("forecasting", "data_latency", "accounting")),
    ),
    "finance_manager": (
        _QuerySeed("weekly cash planning template for small business", "workaround", ("stack_exchange", "github_issues", "reddit"), "Template/workaround language for cash planning.", ("cash_planning", "template", "weekly")),
        _QuerySeed("track accounts payable and receivable in one place", "job_to_be_done", ("github_issues", "stack_exchange", "reddit"), "AP/AR consolidation job language.", ("accounts_payable", "accounts_receivable", "tracking")),
        _QuerySeed("forecast supplier payments and customer collections", "job_to_be_done", ("github_issues", "stack_exchange", "reddit"), "Cash timing forecast across AP and AR.", ("forecasting", "suppliers", "collections")),
        _QuerySeed("spreadsheet keeps breaking for cash flow report", "pain", ("github_issues", "reddit", "hacker_news_algolia"), "Spreadsheet fragility with cash-flow reporting.", ("spreadsheet", "cash_flow", "reporting")),
        _QuerySeed("budget actuals report takes too long every month", "pain", ("github_issues", "stack_exchange", "reddit"), "Monthly budget-vs-actual reporting burden.", ("budget", "actuals", "month_end")),
    ),
    "operations_manager": (
        _QuerySeed("track supplier bills and customer payments in one spreadsheet", "workaround", ("github_issues", "reddit", "hacker_news_algolia"), "Ops workaround for supplier/customer payment tracking.", ("supplier_bills", "customer_payments", "spreadsheet")),
        _QuerySeed("no one knows which invoice was paid", "pain", _OPERATOR_SOURCES, "Cross-team invoice status confusion.", ("invoice", "payment_status", "operations")),
        _QuerySeed("project budget overrun discovered too late", "pain", ("hacker_news_algolia", "reddit", "github_issues"), "Project budget visibility arrives after damage is done.", ("project_budget", "overrun", "visibility")),
        _QuerySeed("sales operations and finance use different spreadsheets", "workaround", ("github_issues", "hacker_news_algolia", "reddit"), "Cross-system spreadsheet fragmentation.", ("sales_ops", "finance", "spreadsheet")),
        _QuerySeed("customer paid but operations still thinks invoice is open", "pain", ("github_issues", "reddit"), "Payment-status sync pain between finance and ops.", ("invoice", "payment_status", "handoff")),
    ),
    "freelancer_solo_operator": (
        _QuerySeed("clients pay late how to plan bills", "urgent_problem", ("hacker_news_algolia", "reddit", "github_issues"), "Freelancer bill planning under late client payments.", ("late_clients", "bills", "cash_flow")),
        _QuerySeed("freelancer irregular income spreadsheet", "workaround", ("github_issues", "reddit", "hacker_news_algolia"), "Spreadsheet workaround for irregular income.", ("irregular_income", "spreadsheet", "freelancer")),
        _QuerySeed("how much to set aside for taxes self employed", "how_to", ("stack_exchange", "reddit"), "Tax set-aside how-to language.", ("taxes", "self_employed", "planning")),
        _QuerySeed("track invoices and personal expenses separately", "job_to_be_done", ("github_issues", "stack_exchange", "reddit"), "Separation job between invoices and personal expenses.", ("invoices", "personal_expenses", "separation")),
        _QuerySeed("can I pay myself this month freelancer", "job_to_be_done", ("hacker_news_algolia", "reddit"), "Solo-operator owner-pay cash question.", ("pay_myself", "freelancer", "cash_planning")),
    ),
}


def _stable_query_id(topic_id: str, persona_id: str, priority: int, query_text: str) -> str:
    normalized = " ".join(query_text.lower().strip().split())
    digest = hashlib.sha256(f"{topic_id}|{persona_id}|{priority}|{normalized}".encode("utf-8")).hexdigest()[:10]
    return f"cvq_{topic_id}_{persona_id}_{priority:03d}_{digest}"


def get_customer_voice_personas(topic_id: str, include_inactive: bool = False) -> list[CustomerVoicePersona]:
    personas = [persona for persona in _PERSONAS if persona.topic_id == topic_id]
    if not include_inactive:
        personas = [persona for persona in personas if persona.is_active]
    return sorted(personas, key=lambda persona: (persona.topic_id, persona.priority, persona.persona_id))


def get_customer_voice_topic_ids(include_inactive: bool = False) -> list[str]:
    topic_ids = {persona.topic_id for persona in _PERSONAS if include_inactive or persona.is_active}
    return sorted(topic_ids)


def generate_customer_voice_queries(
    topic_id: str,
    persona_ids: list[str] | None = None,
    max_queries_per_persona: int | None = None,
    source_type_filter: list[str] | None = None,
) -> list[CustomerVoiceQuery]:
    if max_queries_per_persona is not None and max_queries_per_persona < 0:
        raise ValueError("max_queries_per_persona must be non-negative")

    requested_personas = set(persona_ids or [])
    source_filter = {source.strip() for source in source_type_filter or [] if source.strip()}
    queries: list[CustomerVoiceQuery] = []

    for persona in get_customer_voice_personas(topic_id=topic_id, include_inactive=False):
        if requested_personas and persona.persona_id not in requested_personas:
            continue
        seeds = _QUERY_SEEDS.get(persona.persona_id, ())
        emitted_for_persona = 0
        for index, seed in enumerate(seeds, start=1):
            expected_source_fit = list(seed.source_fit)
            if source_filter:
                expected_source_fit = [source for source in expected_source_fit if source in source_filter]
                if not expected_source_fit:
                    continue
            query = CustomerVoiceQuery(
                query_id=_stable_query_id(topic_id, persona.persona_id, index, seed.text),
                topic_id=topic_id,
                persona_id=persona.persona_id,
                query_text=seed.text,
                query_kind=QUERY_KIND_CUSTOMER_VOICE,
                query_intent=seed.intent,
                expected_source_fit=expected_source_fit,
                language="en",
                generation_method=GENERATION_METHOD_DETERMINISTIC_SEED,
                priority=index,
                rationale=seed.rationale,
                tags=list(seed.tags),
                approval_state=APPROVAL_STATE_PROPOSED,
            )
            query.validate()
            queries.append(query)
            emitted_for_persona += 1
            if max_queries_per_persona is not None and emitted_for_persona >= max_queries_per_persona:
                break

    return sorted(queries, key=lambda query: (query.topic_id, _persona_priority(query.persona_id), query.priority, query.query_id))


def _persona_priority(persona_id: str) -> int:
    for persona in _PERSONAS:
        if persona.persona_id == persona_id:
            return persona.priority
    return 10_000


def approve_customer_voice_query(query: CustomerVoiceQuery) -> CustomerVoiceQuery:
    return replace(query, approval_state=APPROVAL_STATE_APPROVED)


def customer_voice_query_payload(topic_id: str, queries: Iterable[CustomerVoiceQuery]) -> dict[str, object]:
    query_list = list(queries)
    persona_ids = sorted({query.persona_id for query in query_list})
    return {
        "topic_id": topic_id,
        "query_kind": QUERY_KIND_CUSTOMER_VOICE,
        "generation_method": GENERATION_METHOD_DETERMINISTIC_SEED,
        "approval_required_before_active_use": True,
        "prompt_contract_status": "defined_disabled_by_default",
        "personas": [persona.to_dict() for persona in get_customer_voice_personas(topic_id, include_inactive=False) if persona.persona_id in persona_ids],
        "future_topic_stubs": [
            persona.to_dict()
            for persona in _PERSONAS
            if not persona.is_active and persona.topic_id in {"personal_finance_household", "freelancer_solo_finance", "immigrant_finance_israel"}
        ],
        "queries": [query.to_dict() for query in query_list],
    }


def customer_voice_query_markdown(topic_id: str, queries: Iterable[CustomerVoiceQuery]) -> str:
    query_list = list(queries)
    lines = [
        "# Customer Voice Queries",
        "",
        f"- Topic: `{topic_id}`",
        f"- Query kind: `{QUERY_KIND_CUSTOMER_VOICE}`",
        f"- Generation method: `{GENERATION_METHOD_DETERMINISTIC_SEED}`",
        "- Approval required before active use: `true`",
        "- Live LLM/API calls: `none`",
        "",
        "## Personas",
    ]
    for persona in get_customer_voice_personas(topic_id, include_inactive=False):
        if any(query.persona_id == persona.persona_id for query in query_list):
            lines.append(f"- `{persona.persona_id}` - {persona.role_label}: {persona.pain_language_style}")
    lines.extend(["", "## Queries"])
    for query in query_list:
        sources = ", ".join(f"`{source}`" for source in query.expected_source_fit)
        lines.append(
            f"- `{query.query_id}` (`{query.persona_id}`, `{query.query_intent}`, {sources}): {query.query_text}"
        )
    lines.extend([
        "",
        "## Future Topic Stubs",
        "- `personal_finance_household` - inactive stub",
        "- `freelancer_solo_finance` - inactive stub",
        "- `immigrant_finance_israel` - inactive stub",
    ])
    return "\n".join(lines) + "\n"


def write_customer_voice_query_preview(
    *,
    topic_id: str,
    queries: Iterable[CustomerVoiceQuery],
    output_json: Path,
    output_md: Path,
) -> tuple[Path, Path]:
    query_list = list(queries)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(customer_voice_query_payload(topic_id, query_list), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(customer_voice_query_markdown(topic_id, query_list), encoding="utf-8")
    return output_json, output_md
