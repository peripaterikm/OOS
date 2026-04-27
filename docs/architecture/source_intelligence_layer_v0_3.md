# Source Intelligence Layer v0.3

## Purpose

The Source Intelligence Layer is the upstream discovery layer for OOS. Its job is to collect public internet evidence from approved sources, convert that evidence into traceable candidate signals, and feed those signals into the existing Roadmap v2.2 meaning loop.

The founder should define topics, approve sources, review discovery packages, approve or reject suggested priority changes, and make final decisions. The founder should not normally copy posts, browse sources manually, or format JSONL files.

The expected artifact path is:

```text
RawEvidence
-> CandidateSignal
-> existing OOS meaning loop
-> founder review
-> founder decision
```

## Scope For Roadmap v2.3

Roadmap v2.3 is a fixture-first and offline-test-first implementation of autonomous source discovery. It may add real public collectors only in the specific collector items, and those collectors must be disabled/offline by default in tests.

Roadmap v2.3 does not add live LLM calls, secrets, paid API dependencies, automatic priority changes, or automatic founder decisions.

Item 1.1 is documentation and policy closure only. It does not implement collectors, internet calls, APIs, secrets, live LLM calls, dependencies, or product feature code.

## Pipeline

```text
Source Registry
-> Topic Profiles
-> Query Planner
-> Collection Scheduler
-> Collector Interface
-> RawEvidence Store
-> Evidence Cleaner
-> Evidence Classifier
-> CandidateSignal Extraction
-> Source Yield Analytics
-> Weekly Discovery Package
-> Existing OOS Meaning Loop
-> Founder Review / Founder Decision
```

## Source Access Policy

Every source must have explicit access and compliance metadata before implementation. A source must not be treated as available merely because content exists on the public internet.

| Source | Roadmap phase | Enabled by default | Policy |
| --- | --- | --- | --- |
| Hacker News Algolia | Phase B | yes, fixture/offline first | Public API adapter; live use only behind explicit flag/config. |
| GitHub Issues | Phase B | yes, fixture/offline first | Public API adapter; no tokens committed; live use disabled by default. |
| Stack Exchange | Phase B | no production/high-volume without key | `requires_registered_app_key: true`; no secrets committed; disabled/offline-safe mode required. |
| RSS / regulator feeds | Phase B | yes, fixture/offline first | Feed-only collection; no scraping beyond feed content. |
| G2 | Later / access review | no | `access_realistic_for_solo_founder: false`; `enabled: false`; `commercial_review_required: true`. Do not implement a G2 collector in v2.3. |
| Capterra / Trustpilot | Later / access review | no | Later alternatives requiring access and terms review; not guaranteed free sources. |
| Reddit | Phase C - controlled internal research source | yes after collector implementation | High-value default internal research source; `collector_available: false` until implemented; included in standard discovery runs automatically once collector exists; external productization requires review. |
| LinkedIn | Out of scope for v2.3 | no | Do not automate without explicit official API and legal approval. |
| GDELT | Phase D / experimental | no | High noise risk; not a Phase B core source. |

### Phase B source policies

HN Algolia:

- low-friction Phase B source;
- public search adapter;
- fixture/offline-first tests;
- live network disabled by default unless an explicit flag/config allows it.

GitHub Issues:

- low-friction Phase B source;
- public issues/search adapter;
- fixture/offline-first tests;
- no tokens or secrets committed;
- live network disabled by default unless an explicit flag/config allows it.

Stack Exchange:

- Phase B source;
- `requires_registered_app_key: true` for production/high-volume use;
- no API key committed;
- tests must not require a key;
- offline fixture mode required.

RSS / regulator / changelog feeds:

- Phase B source;
- public feed content only;
- no scraping outside feed content;
- suitable for regulatory, why-now, competitor changelog, and market-change signals.

### Reddit internal research policy

Reddit is a high-value default internal research source for OOS, not an excluded source. It is a Phase C controlled internal research source with these policy fields:

```yaml
reddit:
  phase: "C - controlled internal research source"
  status: "high-value default source"
  enabled_by_default: true
  included_in_standard_discovery_runs: true
  collector_available: false
  active_after_collector_implementation: true
  usage_mode: "internal_research"
```

Important interpretation:

- `enabled_by_default: true` means Reddit participates in standard discovery runs automatically after a Reddit collector is implemented.
- `collector_available: false` means the Query Planner must not generate executable Reddit `QueryPlan` records yet.
- No manual per-run enabling should be required after the Reddit collector exists.
- External or commercial productization requires a separate review checkpoint.

Hard constraints:

- do not store usernames by default;
- do not store bulk thread dumps by default;
- do not redistribute Reddit-derived data to third parties;
- do not train models on Reddit content;
- review before external productization.

Storage strategy:

- `source_url` is required;
- relevant excerpt or summary is required;
- selected context is allowed;
- full thread archive is not the default.

Scaling strategy:

- scale by measured source yield;
- do not reduce signal quality for abstract caution alone.

### Deferred and disabled sources

Trustpilot and Capterra are later access-review candidates. They are not guaranteed free Phase B sources and require terms/access review before implementation.

G2 is disabled by default. It requires commercial review, is not realistic for a solo founder without explicit access/cost approval, and must not receive a v2.3 collector unless re-approved later.

LinkedIn automation is out of scope for v2.3 unless explicit official API and legal approval exists.

GDELT is experimental / Phase D because of high noise risk. It is not a Phase B core source.

## Privacy Policy

`RawEvidence.author_or_context` must store role or context by default, not usernames or handles. Examples:

- `SMB owner`
- `developer`
- `founder`
- `unverified public commenter`

Storing handles/usernames requires explicit source policy approval and is out of scope for Roadmap v2.3.

## Topic Policy

Roadmap v2.3 starts with one active topic profile:

```yaml
topic_id: ai_cfo_smb
status: active
```

Only these future/stub topics may appear, and they must be explicitly inactive:

```yaml
topic_id: insurance_israel
status: inactive_future

topic_id: life_management_system
status: inactive_future
```

CLI examples must not use undefined active topics.

## RawEvidence Contract

`RawEvidence` is the canonical source object before signal extraction. Required fields:

- `evidence_id`
- `source_id`
- `source_type`
- `source_name`
- `source_url`
- `collected_at`
- `title`
- `body`
- `language`
- `topic_id`
- `query_kind`
- `content_hash`
- `author_or_context`
- `raw_metadata`
- `access_policy`
- `collection_method`

Rules:

- `source_url` must be preserved.
- `content_hash` must be deterministic.
- `author_or_context` must not store usernames/handles by default.
- Tests must not require network access.

## Source Registry And Topic Profiles

The Source Registry must track:

- `source_id`
- `source_type`
- `source_name`
- `enabled`
- `access_policy`
- `commercial_review_required`
- `requires_registered_app_key`
- `access_realistic_for_solo_founder`
- `offline_fixture_required`
- `live_collection_allowed_by_default`
- `enabled_by_default`
- `included_in_standard_discovery_runs`
- `collector_available`
- `active_after_collector_implementation`
- `usage_mode`
- rate and collection limits

Topic profiles must track:

- `topic_id`
- status: `active`, `inactive_future`, or `disabled`
- included/excluded keywords
- allowed source IDs
- query kinds
- max queries per source and topic

## Evidence Cleaner v2.3

Allowed:

- whitespace normalization
- URL normalization
- content hash generation
- language detection only if existing tooling supports it without new dependencies

Not allowed in v2.3:

- boilerplate removal
- aggressive scraping cleanup
- destructive overwrites of raw evidence

## Evidence Classifier

Allowed classes:

- `pain_signal_candidate`
- `workaround_signal_candidate`
- `buying_intent_candidate`
- `competitor_weakness_candidate`
- `trend_trigger_candidate`
- `needs_human_review`
- `noise`

Critical rule: for `hacker_news_algolia` and `github_issues`, unknown or ambiguous content must default to `needs_human_review`, not `noise`, to avoid false negatives on high-potential discussions.

No source evidence may be deleted by the classifier.

## CandidateSignal Contract

Required fields:

- `signal_id`
- `evidence_id`
- `source_url`
- `topic_id`
- `query_kind`
- `signal_type`
- `pain_summary`
- `target_user`
- `current_workaround`
- `buying_intent_hint`
- `urgency_hint`
- `confidence`
- `measurement_methods`
- `extraction_mode`

One `RawEvidence` item may yield zero, one, or many candidate signals. Every candidate signal must preserve `evidence_id` and `source_url`.

## Scoring Measurement Methods

Every scoring dimension must define `measurement_method`:

- `rule_based`
- `llm_stub`
- `founder_manual`

Live LLM scoring is out of scope for Roadmap v2.3. Unsupported dimensions must not be silently treated as measured.

## Source Yield Analytics

Yield is measured at this key:

```text
source_id x topic_id x query_kind
```

Metrics:

- `queries_run`
- `evidence_collected`
- `candidate_signals_extracted`
- `high_quality_signals`
- `opportunities_created`
- `ideas_shortlisted`
- `founder_approved_count`
- `founder_killed_count`

Roadmap v2.3 may produce `suggested_priority_updates` only. It must not automatically apply priority changes. Founder approve/reject is required before changes are applied. Automatic feedback application is v2.4+.

Feedback and yield must be tracked at `source_id x topic_id x query_kind`, not only at `source_id`, so weak query kinds do not unfairly demote an entire source.

## Traceability Requirement

Acceptance tests must prove this chain is preserved:

```text
weekly_discovery_package
-> idea/opportunity
-> extracted signal
-> raw evidence
-> source_url
```

Breaking this chain must fail tests and must not be allowed to fail silently.

## Non-Goals For Item 1.1

Item 1.1 does not implement:

- collectors;
- internet calls;
- APIs;
- secrets;
- live LLM calls;
- dependencies;
- product feature code.

Those belong to later Roadmap v2.3 implementation items after the spec and access policy are closed.

## Run Reports

Every discovery or validation run must write evidence to `docs/dev_ledger/03_run_reports/` or runtime artifacts when appropriate. Reports should include:

- branch
- command
- started/completed time if available
- validation commands
- validation results
- known warnings
- source registry/topic profile versions
- collector mode: fixture/offline/live
- `no_live_llm_confirmed`
- `no_push_merge_tag_confirmed`

## v0.3 Consolidation Note

This v0.3 spec consolidates the previous v0.1 and v0.2 planning drafts. Those drafts are archived under `docs/architecture/archive/` for reference and are no longer active roadmap files.
