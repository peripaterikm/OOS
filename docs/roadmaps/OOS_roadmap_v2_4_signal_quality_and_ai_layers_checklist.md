# OOS Roadmap v2.4 Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎСљ Signal Quality, Customer Voice, and AI Layers Checklist

## 0.1 Purpose

Roadmap v2.4 extends the Source Intelligence MVP from a technically working live-collection loop into a higher-quality market intelligence system.

The core goal is to improve:

- signal quality;
- live-source relevance;
- customer-language discovery;
- structured LLM-assisted review;
- implied burden detection;
- opportunity/action readiness.

This roadmap is intentionally focused on **quality and intelligence**, not on adding many new sources.

## 0.2 Status

- [ ] **0.2.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_4_signal_quality_and_ai_layers_checklist.md`
- [ ] **0.2.2** Current item: **8.2**
- [ ] **0.2.3** Roadmap state: `blocked`
- [ ] **0.2.4** Completed from this roadmap: **16 / 17**
- [ ] **0.2.5** Remaining: **1 / 17**
- [ ] **0.2.6** Primary design reference: `docs/architecture/source_intelligence_signal_strategy_v0_5.md`
- [ ] **0.2.7** Source Intelligence architecture reference: `docs/architecture/source_intelligence_layer_v0_3.md`

## 0.3 Prerequisites

This roadmap assumes the following are already merged or available:

- Source Intelligence MVP discovery loop.
- Live collection mode for weekly discovery CLI.
- Working collectors for at least:
  - HN Algolia;
  - GitHub Issues;
  - Stack Exchange;
  - RSS feeds.
- Existing artifacts:
  - `RawEvidence`;
  - `CleanedEvidence`;
  - `EvidenceClassification`;
  - `CandidateSignal`;
  - Founder Discovery Package;
  - Meaning-loop dry run.

## 0.4 Strategic Principles

- [ ] **0.4.1** Evidence-first: every signal must trace back to `RawEvidence` and `source_url`.
- [ ] **0.4.2** Deterministic-first: deterministic filters/scoring run before LLM.
- [ ] **0.4.3** LLM is advisory, not authoritative.
- [ ] **0.4.4** Founder remains final decision-maker.
- [ ] **0.4.5** No live LLM/API calls by default.
- [ ] **0.4.6** No live network calls in tests.
- [ ] **0.4.7** Privacy by default: no usernames/handles stored unless explicitly allowed by policy.
- [ ] **0.4.8** PII redaction before any external LLM/API call.
- [ ] **0.4.9** Role-based LLM budgets with hard circuit breakers.
- [ ] **0.4.10** Source expansion is secondary to signal quality.

## 0.5 Current Known Problems To Solve

From live collection runs:

- HN and GitHub collectors work technically but surface noisy generic content.
- GitHub Issues can produce marketing/product-pitch artifacts as false-positive pain signals.
- HN summaries can leak HTML entities/tags.
- GitHub summaries can contain mojibake/encoding artifacts.
- RSS currently needs safer feed URL handling.
- Scoring is too flat.
- `small business` / `spreadsheet` alone is too weak as a finance pain anchor.
- The system needs customer-language queries, not only founder/expert-language queries.
- The system needs to detect implied burden, not only explicit complaint language.

---

# Milestone A Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎСљ Live Signal Quality Hardening

## 1.1 Live collection relevance hardening

### Goal

Improve quality of live HN/GitHub/RSS signals before adding LLM layers.

### Scope

- HTML/entity cleanup.
- UTF-8/mojibake handling.
- `ai_cfo_smb` relevance gate.
- Anti-marketing/generated-content downgrade.
- Better HN/GitHub query templates.
- RSS feed URL handling.
- More discriminative deterministic scoring.

### Out of scope

- LLM integration.
- New source types.
- Reddit.
- Embeddings.
- Cluster synthesis.

### Acceptance criteria

- [x] **1.1.1** HTML entities such as `&#x27;` are cleaned.
- [x] **1.1.2** Simple tags such as `<p>` do not appear in `pain_summary`.
- [x] **1.1.3** Mojibake fragments such as `Р В Р Р‹Р В РІР‚С™Р В Р Р‹Р РЋРЎСџ`, `Р В Р’В Р В РІР‚В Р В Р’В Р Р†Р вЂљРЎв„ў`, `Р В Р’В Р вЂ™Р’В Р В Р Р‹Р РЋРЎСџ` do not appear in normalized summaries from mocked collector responses.
- [x] **1.1.4** Generic small-business HN text without finance anchors is not high-confidence `pain_signal`.
- [x] **1.1.5** GitHub marketing/content-calendar/product-pitch text is downgraded to `noise` or low-confidence `needs_human_review`.
- [x] **1.1.6** Invoice/payment-cycle/manual-spreadsheet signal remains high-priority.
- [x] **1.1.7** RSS search-text queries are skipped safely, not fetched as URLs.
- [x] **1.1.8** Scoring is no longer flat across mixed fixture examples.
- [x] **1.1.9** Focused tests pass.
- [x] **1.1.10** Full test discovery passes.
- [x] **1.1.11** `oos-validate.ps1` passes.
- [x] **1.1.12** `verify.ps1` passes.

### Follow-up hardening

- [x] **1.1b** Manual live smoke follow-up added founder-package signal deduplication, common mojibake repairs, GitHub install/tutorial/generic-copy downgrades, explicit noise coverage for obvious junk, and ranking tests that keep genuine user pain above generic finance copy.
- Roadmap counters were not advanced by `1.1b`; this is a narrow quality patch under completed item **1.1** before item **1.2** live acceptance smoke runs.

### Expected files

- `src/oos/evidence_classifier.py`
- `src/oos/candidate_signal_extractor.py`
- `src/oos/source_registry.py`
- `src/oos/query_planner.py`
- `src/oos/hn_algolia_collector.py`
- `src/oos/github_issues_collector.py`
- `src/oos/rss_collector.py`
- `src/oos/live_collection.py`
- `tests/test_evidence_cleaner_classifier.py`
- `tests/test_candidate_signal_extractor.py`
- `tests/test_source_registry_query_planner.py`
- `tests/test_live_collection_mode.py`
- `docs/dev_ledger/02_mini_epics/1.1-live-collection-relevance-hardening.md`
- `docs/dev_ledger/03_run_reports/1.1-live-collection-relevance-hardening.md`

---

## 1.2 Live quality acceptance smoke runs

### Goal

Run manual live smoke tests after hardening and record whether live quality improved.

### Scope

Manual runs:

- HN only.
- GitHub only.
- Mixed run.
- Optional Stack Exchange.
- Optional RSS if feed URL configuration exists.

### Acceptance criteria

- [x] **1.2.1** `live_hn_002` run completed.
- [x] **1.2.2** `live_github_003` run completed.
- [x] **1.2.3** `live_mix_003` run completed.
- [x] **1.2.4** Top results show fewer HTML/encoding artifacts.
- [x] **1.2.5** At least one finance-relevant pain signal appears in GitHub or HN.
- [x] **1.2.6** Marketing/generated-content false positives no longer dominate top results.
- [x] **1.2.7** Result summary is recorded in Dev Ledger.
- [x] **1.2.8** No runtime artifacts are committed.


### Acceptance smoke formalization

- [x] **1.2.9** Deterministic local smoke checker validates already-generated live discovery artifacts without running collectors.
- [x] **1.2.10** RSS missing-feed behavior is accepted only as controlled `rss_feed_url_missing` skip, not `unknown url type`.
- [x] **1.2.11** Known limitation recorded: generic finance/consulting copy can still rank too high until semantic/LLM layers are added.

### Manual commands

```powershell
$env:PYTHONPATH="src"

.\.venv\Scripts\python.exe -m oos.cli run-discovery-weekly `
  --topic ai_cfo_smb `
  --project-root . `
  --run-id live_github_002 `
  --use-collectors `
  --allow-live-network `
  --source-type github_issues `
  --max-total-queries 2 `
  --max-queries-per-source 2 `
  --max-results-per-query 5 `
  --include-meaning-loop-dry-run
```

---

# Milestone B Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎСљ Customer Voice Query Generation

## 2.1 Customer Voice Query Generator contract and artifacts

### Goal

Add a query generation layer that searches in customer language, not only founder/expert language.

### Rationale

Founder-language queries such as `cash flow forecasting` miss latent pain. Customers may say:

- Р В Р вЂ Р В РІР‚С™Р РЋРЎв„ўI donР В Р вЂ Р В РІР‚С™Р Р†РІР‚С›РЎС›t know where the money went.Р В Р вЂ Р В РІР‚С™Р РЋРЎС™
- Р В Р вЂ Р В РІР‚С™Р РЋРЎв„ўMy bookkeeper quit and I need to close the month.Р В Р вЂ Р В РІР‚С™Р РЋРЎС™
- Р В Р вЂ Р В РІР‚С™Р РЋРЎв„ўHow do I know which invoices will be paid before rent is due?Р В Р вЂ Р В РІР‚С™Р РЋРЎС™

### Scope

- Add `CustomerVoiceQueryHypothesis` model.
- Add `query_kind = customer_voice_query`.
- Add LLM prompt contract, but disabled by default.
- Add deterministic fixture/stub query generation for tests.
- Add approval-state fields:
  - `proposed`;
  - `approved`;
  - `rejected`;
  - `retired`.

### Out of scope

- Live LLM calls.
- Auto-approval of generated queries.
- Query refinement advisor.

### Acceptance criteria

- [x] **2.1.1** Customer voice query artifact model exists.
- [x] **2.1.2** Prompt contract exists and has asymmetric instruction to avoid overfitting.
- [x] **2.1.3** Stub generator produces deterministic customer-language queries.
- [x] **2.1.4** Generated queries preserve topic/profile traceability.
- [x] **2.1.5** Queries require founder approval before active use.
- [x] **2.1.6** No live LLM calls in tests.
- [x] **2.1.7** Focused tests pass.
- [x] **2.1.8** Full validation passes.

### Implementation notes

- [x] **2.1.9** Active `ai_cfo_smb` customer voice generation is persona-based across owner, bookkeeper, accountant, fractional CFO, finance manager, operations manager, and freelancer/solo operator perspectives.
- [x] **2.1.10** Future topic stubs exist for `personal_finance_household`, `freelancer_solo_finance`, and `immigrant_finance_israel`, but they are inactive by default.
- [x] **2.1.11** CLI preview can write deterministic JSON/Markdown query artifacts without changing source registry or live planner behavior.
### Expected files

- `src/oos/customer_voice_queries.py`
- `tests/test_customer_voice_queries.py`
- `docs/dev_ledger/02_mini_epics/2.1-customer-voice-query-generator.md`
- `docs/dev_ledger/03_run_reports/2.1-customer-voice-query-generator.md`

---

## 2.2 Customer voice query planner integration

### Goal

Allow approved customer voice queries to participate in QueryPlanner without replacing deterministic expert queries.

### Scope

- QueryPlanner reads approved customer voice queries.
- Query plans include `query_kind = customer_voice_query`.
- Query yield tracked separately.
- Source limits still apply.
- Default mode can run without customer voice queries.

### Acceptance criteria

- [x] **2.2.1** QueryPlanner can include approved customer voice queries.
- [x] **2.2.2** Unapproved queries are ignored.
- [x] **2.2.3** Query plans remain deterministic and bounded.
- [x] **2.2.4** Source filters still work.
- [x] **2.2.5** Customer voice query yield is separated in summary metrics.
- [x] **2.2.6** Existing QueryPlanner tests remain green.
- [x] **2.2.7** Full validation passes.
### Implementation notes

- [x] **2.2.8** Customer Voice QueryPlans are emitted only from `approval_state=approved` queries; proposed, rejected, and retired queries remain non-executable.
- [x] **2.2.9** Preview CLI writes deterministic JSON/Markdown with generated, approved, and plan counts while reporting `collectors_run=false`, `live_network_calls=false`, and `llm_calls=false`.
- [x] **2.2.10** Source fit, source filters, collector availability, and Reddit gating are enforced before Customer Voice QueryPlans are emitted.

### Expected files

- `src/oos/query_planner.py`
- `src/oos/customer_voice_queries.py`
- `tests/test_customer_voice_query_planner_integration.py`
- `docs/dev_ledger/02_mini_epics/2.2-customer-voice-query-planner-integration.md`
- `docs/dev_ledger/03_run_reports/2.2-customer-voice-query-planner-integration.md`

---

# Milestone C Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎСљ Semantic Relevance and Scoring v2

## 3.1 Scoring model v2 and relevance dimensions

### Goal

Make scoring explicit, normalized, and extensible before adding embeddings or LLM scores.

### Scope

- Normalize scoring formula.
- Prevent double-counting when embeddings are disabled.
- Add fields:
  - `topic_keyword_relevance_score`;
  - `semantic_relevance_score`;
  - `anti_marketing_penalty`;
  - `kill_pattern_penalty`;
  - `signal_type_weight`;
  - `scoring_mode`.
- Add separate formulas:
  - embeddings enabled;
  - embeddings disabled.

### Acceptance criteria

- [x] **3.1.1** Scoring weights sum correctly for enabled/disabled modes.
- [x] **3.1.2** No double-counting of keyword relevance when embeddings are disabled.
- [x] **3.1.3** `signal_type_weight` is a soft multiplier, not hard sort priority.
- [x] **3.1.4** Scoring remains deterministic.
- [x] **3.1.5** Mixed fixtures produce non-flat confidence distribution.
- [x] **3.1.6** Full validation passes.
- [x] **3.1.7** `SignalScoreBreakdown` records component scores, caps, penalties, final score, and explanation.
- [x] **3.1.8** `CandidateSignal` artifacts include `scoring_model_version` and `scoring_breakdown` without requiring external providers.
- [x] **3.1.9** Semantic relevance, embeddings, and LLM review remain deferred to later roadmap items.

### Expected files

- `src/oos/candidate_signal_extractor.py`
- `src/oos/signal_scoring.py`
- `tests/test_signal_scoring_model_v2.py`
- `docs/dev_ledger/02_mini_epics/3.1-scoring-model-v2.md`
- `docs/dev_ledger/03_run_reports/3.1-scoring-model-v2.md`

---

## 3.2 Semantic relevance provider boundary

### Goal

Add semantic relevance support through a provider boundary without forcing new dependencies or external calls.

### Scope

- Add `SemanticRelevanceProvider` interface.
- Add deterministic stub provider for tests.
- Add placeholder for local embeddings provider.
- Do not add `sentence-transformers` dependency unless explicitly approved.
- Add configuration:
  - `semantic_relevance_enabled = false` by default.
  - `provider = stub | local_embeddings`.
- Add acceptance tests for disabled/stub modes.

### Out of scope

- Installing embedding models.
- Live embedding API.
- Large corpus vector index.

### Acceptance criteria

- [x] **3.2.1** Semantic provider interface exists.
- [x] **3.2.2** Stub provider works in tests.
- [x] **3.2.3** Disabled mode sets `semantic_relevance_score = 0`.
- [x] **3.2.4** Scoring redistributes weights correctly in disabled mode.
- [x] **3.2.5** No external dependencies added.
- [x] **3.2.6** No external API calls.
- [x] **3.2.7** Full validation passes.

### Expected files

- `src/oos/semantic_relevance.py`
- `src/oos/signal_scoring.py`
- `tests/test_semantic_relevance_provider_boundary.py`
- `docs/dev_ledger/02_mini_epics/3.2-semantic-relevance-provider-boundary.md`
- `docs/dev_ledger/03_run_reports/3.2-semantic-relevance-provider-boundary.md`

### Completion notes

- Completed as a provider-boundary-only implementation: disabled provider is default and `keyword_stub` is deterministic local preview/test support only.
- Scoring model v2 records semantic relevance diagnostics while preserving embeddings-disabled default scoring behavior.
- No embeddings, vector database, external API, live internet, or live LLM calls were added.

---

# Milestone D Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎСљ LLM Provider Boundaries and Safe Signal Review

## 4.1 Role-based LLM provider contracts and budgets

### Goal

Add provider contracts and budgets for future LLM use without enabling live calls by default.

### LLM roles

- Query Generator.
- Signal Review.
- Cluster Synthesis.
- Query Refinement Advisor.
- Implied Burden Detection.
- Price Signal Extraction.
- Experiment Blueprint.

### Scope

- Add `LLMProvider` interface.
- Add `NoopLLMProvider`.
- Add `StubLLMProvider`.
- Add role-specific budgets:
  - max calls;
  - max input tokens;
  - max output tokens;
  - max cost estimate;
  - fail-closed behavior.
- Add global circuit breaker.
- Add provider config:
  - `provider = none | openai | anthropic | local_openai_compatible | stub`.
- No live provider implementation required in this item.

### Acceptance criteria

- [x] **4.1.1** Role-specific budgets exist.
- [x] **4.1.2** Global circuit breaker exists.
- [x] **4.1.3** Default provider is `none` or `noop`.
- [x] **4.1.4** Stub provider deterministic in tests.
- [x] **4.1.5** Budget exhaustion fails closed.
- [x] **4.1.6** No secrets required.
- [x] **4.1.7** No live LLM calls in tests.
- [x] **4.1.8** Full validation passes.

### Expected files

- `src/oos/llm_contracts.py`
- `tests/test_llm_contracts_and_budgets.py`
- `docs/dev_ledger/02_mini_epics/4.1-llm-provider-contracts-and-budgets.md`
- `docs/dev_ledger/03_run_reports/4.1-llm-provider-contracts-and-budgets.md`

### Completion notes

- Completed as an infrastructure contract only: `disabled` is default and `deterministic_mock` is local/test-only.
- Budget policies, budget state, token/cost estimation, and fail-closed circuit breaker behavior were added without real provider clients.
- No secrets, dependencies, internet/API calls, or live LLM calls were added.

---

## 4.2 PII stripping and prompt safety envelope

### Goal

Protect evidence excerpts before any future external LLM prompt.

### Scope

- Add `RedactedEvidenceExcerpt` artifact/model.
- Strip or mask:
  - email addresses;
  - phone numbers;
  - obvious person names if reliable enough;
  - usernames/handles;
  - tokens/secrets patterns;
  - URLs only when not needed for evidence citation.
- Keep `evidence_id` and `source_url` outside excerpt for traceability.
- Add prompt safety envelope:
  - asymmetric prior;
  - evidence-bound instructions;
  - default recommendation = review, not advance;
  - no invention;
  - cite evidence ID.

### Acceptance criteria

- [x] **4.2.1** PII stripping exists.
- [x] **4.2.2** Redacted excerpt is generated before LLM prompt.
- [x] **4.2.3** Original evidence remains unchanged.
- [x] **4.2.4** Prompt includes asymmetric prior.
- [x] **4.2.5** Prompt requires `evidence_cited = true`.
- [x] **4.2.6** No external calls.
- [x] **4.2.7** Full validation passes.

### Expected files

- `src/oos/prompt_safety.py`
- `tests/test_prompt_safety_pii.py`
- `docs/dev_ledger/02_mini_epics/4.2-pii-stripping-and-prompt-safety.md`
- `docs/dev_ledger/03_run_reports/4.2-pii-stripping-and-prompt-safety.md`

### Completion notes

- Completed as a deterministic prompt-safety helper layer; it is not connected to live discovery or real LLM providers by default.
- Email, phone, URL, IPv4, card, Israeli ID, IBAN, bank-account-like long digits, secret-token, and private-key patterns are detected and redacted with stdlib-only logic.
- Secrets, private keys, and valid credit-card-like numbers block fail-closed by default.
- The safe LLM request builder preserves request metadata and roles while returning `None` for blocked prompts.
- No secrets, dependencies, internet/API calls, or live LLM calls were added.

---

## 4.3 LLM Signal Review and JTBD extraction contracts

### Goal

Define structured LLM review output for CandidateSignals without live calls by default.

### Scope

- Add `LLMSignalReview` model.
- Add structured schema fields:
  - `relevance_score`;
  - `pain_score`;
  - `buying_intent_score`;
  - `icp_fit_score`;
  - `summary`;
  - `red_flags`;
  - `recommendation = advance | review | park | reject`;
  - `evidence_cited`;
  - `jtbd_extracted`.
- Add deterministic stub review.
- Add prompt builder.
- Add budget role: `signal_review`.

### Acceptance criteria

- [x] **4.3.1** LLMSignalReview model exists.
- [x] **4.3.2** JTBD structure includes `when`, `want_to`, `so_that`, `confidence`.
- [x] **4.3.3** `evidence_cited` required.
- [x] **4.3.4** Stub review deterministic.
- [x] **4.3.5** No live LLM calls by default.
- [x] **4.3.6** Founder package can optionally display stub/review outputs.
- [x] **4.3.7** Full validation passes.

### Expected files

- `src/oos/llm_signal_review.py`
- `tests/test_llm_signal_review_contracts.py`
- `docs/dev_ledger/02_mini_epics/4.3-llm-signal-review-jtbd-contracts.md`
- `docs/dev_ledger/03_run_reports/4.3-llm-signal-review-jtbd-contracts.md`

### Completion notes

- Completed as a contract boundary only: no real provider calls, no live discovery integration, and no production LLM review execution.
- Added evidence-bound signal review input/output models, JTBD statement contracts, prompt builders, safe request construction, JSON parsing, and fail-closed output validation.
- Added a deterministic mock review flow for tests/local preview only.
- Added `llm_signal_review` as an allowed local-preview budget task type.
- No secrets, dependencies, internet/API calls, or live LLM calls were added.

---

# Milestone E - Offline LLM Review and Price Signals

## 5.1 LLM Signal Review offline dry-run

### Goal

Run the LLM Signal Review and JTBD contracts against existing discovery artifacts without real provider calls.

### Scope

- Read existing discovery run artifacts or explicit local artifact paths.
- Select CandidateSignals deterministically.
- Build evidence-bound `LLMSignalReviewInput` records.
- Build safe `LLMRequest` objects through prompt safety.
- Run deterministic mock review only.
- Validate structured `LLMSignalReviewOutput` / JTBD contracts.
- Write JSON and Markdown dry-run reports.
- Preserve candidate signal, evidence, source type, and source URL traceability.

### Acceptance criteria

- [x] **5.1.1** Offline dry-run model and report structures exist.
- [x] **5.1.2** Existing discovery run artifacts can be loaded.
- [x] **5.1.3** Candidate signal selection is deterministic and bounded.
- [x] **5.1.4** Safe LLM requests are built through prompt safety.
- [x] **5.1.5** Prompt-safety-blocked items fail closed and produce no review output.
- [x] **5.1.6** Deterministic mock review validates evidence citations and JTBD output contracts.
- [x] **5.1.7** JSON and Markdown dry-run reports are written deterministically.
- [x] **5.1.8** CLI command writes reports without live collection, provider calls, network calls, or live LLM/API calls.
- [x] **5.1.9** Full validation passes.

### Expected files

- `src/oos/llm_signal_review_dry_run.py`
- `src/oos/cli.py`
- `tests/test_llm_signal_review_dry_run.py`
- `docs/dev_ledger/02_mini_epics/5.1-llm-signal-review-offline-dry-run.md`
- `docs/dev_ledger/03_run_reports/5.1-llm-signal-review-offline-dry-run.md`

### Completion notes

- Completed as an offline deterministic dry-run only; no real provider calls, live discovery integration, or production LLM review execution were added.
- The dry-run reads existing `candidate_signals.json` and `cleaned_evidence.json` artifacts, builds safe review requests, runs the deterministic mock review, validates output contracts, and writes traceable reports.
- No secrets, dependencies, internet/API calls, provider `.complete()` calls, or live LLM calls were added.

---

## 5.2 Price signal extraction

### Goal

Extract budget/spend/willingness-to-pay hints from evidence.

### Scope

- Add `PriceSignal` model.
- Extract:
  - `current_spend_hint`;
  - `effort_cost_hint`;
  - `price_complaint`;
  - `willingness_to_pay_indicator`;
  - `evidence_cited`;
  - `confidence`.
- Add deterministic regex/rule baseline.
- Add LLM prompt contract for future use.
- Integrate as scoring boost only when evidence is explicit.

### Acceptance criteria

- [x] **5.2.1** Model exists.
- [x] **5.2.2** Dollar/month/hour hints extracted when explicit.
- [x] **5.2.3** Effort hints such as `20 hours/month` extracted.
- [x] **5.2.4** No invented budgets.
- [x] **5.2.5** Founder package can display price hints.
- [x] **5.2.6** Full validation passes.

### Expected files

- `src/oos/price_signal_extractor.py`
- `tests/test_price_signal_extractor.py`
- `docs/dev_ledger/02_mini_epics/5.2-price-signal-extraction.md`
- `docs/dev_ledger/03_run_reports/5.2-price-signal-extraction.md`

### Completion notes

- Added a serializable `PriceSignal` model and deterministic evidence-only extractor for explicit spend, effort cost, price complaint, and willingness-to-pay hints.
- Added a future-only LLM prompt contract that requires exact evidence citation, null/low-confidence fields when unsure, and no invented budgets.
- Added a narrow explicit-price scoring boost and founder discovery package display for price hints without overriding core signal quality.
- No dependencies, secrets, internet/API calls, live LLM/API calls, provider `.complete()` calls, push, PR, merge, or tag/release were added.

---

# Milestone F Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎСљ Pattern Intelligence

## 6.1 Weak signal aggregation protocol

### Goal

Upgrade clusters of weak signals from multiple sources into review-worthy patterns.

### Scope

- Add `WeakPatternCandidate` model.
- Add cluster upgrade rule:

```yaml
if:
  cluster.signal_count >= 5
  cluster.avg_confidence >= 0.30
  cluster.source_diversity >= 2
  cluster.max_confidence < 0.60
then:
  classification = weak_pattern_candidate
  review_priority = elevated
```

- Integrate with founder package.

### Acceptance criteria

- [x] **6.1.1** Weak pattern model exists.
- [x] **6.1.2** Weak signals from multiple sources can elevate cluster review priority.
- [x] **6.1.3** Single weak signal does not elevate.
- [x] **6.1.4** Founder package has weak pattern section.
- [x] **6.1.5** Full validation passes.

### Expected files

- `src/oos/weak_signal_aggregation.py`
- `tests/test_weak_signal_aggregation.py`
- `docs/dev_ledger/02_mini_epics/6.1-weak-signal-aggregation.md`
- `docs/dev_ledger/03_run_reports/6.1-weak-signal-aggregation.md`

### Completion notes

- Added `WeakPatternCandidate` model and deterministic `weak_signal_aggregation` protocol.
- Discovery runs now write `weak_pattern_candidates.json` before founder package rendering.
- Existing founder package quality sections render weak pattern candidates from that artifact.
- Final Roadmap v2.4 closure remains blocked by the `8.2` final checkpoint.

---

## 6.2 Cluster synthesis LLM contract

### Goal

Define cluster-level LLM synthesis that summarizes patterns, not individual signals.

### Scope

- Add `ClusterSynthesis` model.
- Input: 5Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎС™10 signals from one cluster.
- Output:
  - `emerging_pain_pattern`;
  - `strongest_evidence_ids`;
  - `icp_synthesis`;
  - `opportunity_sketch`;
  - `why_now_signal`;
  - `confidence`;
  - `evidence_cited`.
- Add deterministic stub.
- Add prompt contract.
- Add budget role: `cluster_synthesis`.

### Acceptance criteria

- [x] **6.2.1** ClusterSynthesis model exists.
- [x] **6.2.2** Stub synthesis deterministic.
- [x] **6.2.3** Evidence IDs preserved.
- [x] **6.2.4** Prompt uses cluster context, not isolated signal.
- [x] **6.2.5** No live LLM calls by default.
- [x] **6.2.6** Full validation passes.

### Expected files

- `src/oos/cluster_synthesis.py`
- `tests/test_cluster_synthesis_contract.py`
- `docs/dev_ledger/02_mini_epics/6.2-cluster-synthesis-llm-contract.md`
- `docs/dev_ledger/03_run_reports/6.2-cluster-synthesis-llm-contract.md`

### Implementation notes

- Added `ClusterSynthesis` model and deterministic `cluster_synthesis` contract/stub module.
- Stub synthesis accepts 5-10 cluster signals, preserves evidence IDs, and selects strongest evidence deterministically.
- Future LLM prompt contract requires cluster-level context, evidence citations, low confidence under uncertainty, and no isolated single-signal synthesis.
- `cluster_synthesis` already exists as an allowed local-preview budget role and remains disabled under the default fail-closed budget policy.
- No provider calls or live LLM/API calls were added.
- Full validation passed during the subsequent 7.1 gap-closure run, so `6.2.6` is complete.
- Final Roadmap v2.4 closure remains blocked by the `8.2` final checkpoint.

---

# Milestone G Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎСљ Feedback From Kills and Founder Decisions

## 7.1 Kill Archive feedback into scoring

### Goal

Prevent the system from repeatedly elevating patterns that resemble already-killed opportunities.

### Scope

- Add `kill_pattern_penalty`.
- Add `kill_pattern_flag`.
- Compare signal/cluster against Kill Archive patterns.
- Downgrade but do not auto-kill.
- Founder package shows:
  - similar killed opportunity;
  - kill reason;
  - evidence linkage.

### Acceptance criteria

- [x] **7.1.1** Kill Archive lookup integrated.
- [x] **7.1.2** Similar killed pattern triggers flag.
- [x] **7.1.3** Similar killed pattern reduces score.
- [x] **7.1.4** Founder package explains penalty.
- [x] **7.1.5** No auto-kill.
- [x] **7.1.6** Full validation passes.

### Expected files

- `src/oos/kill_archive_feedback.py`
- `src/oos/signal_scoring.py`
- `tests/test_kill_archive_feedback.py`
- `docs/dev_ledger/02_mini_epics/7.1-kill-archive-feedback.md`
- `docs/dev_ledger/03_run_reports/7.1-kill-archive-feedback.md`

### Completion notes

- Added deterministic Kill Archive feedback lookup for candidate signals using normalized-token overlap against existing `KillReason` artifacts.
- Similar killed patterns now set `kill_pattern_flag`, apply a conservative `kill_pattern_penalty`, and preserve linked evidence/source details.
- Discovery runs write `kill_archive_warnings.json`; founder packages render the similar killed opportunity, kill reason, penalty, and evidence linkage through the existing quality section.
- The feedback downgrades scores only; it does not auto-kill or change portfolio state.
- No dependencies, internet/API calls, or live LLM calls were added.
- Final Roadmap v2.4 closure remains blocked by the `8.2` final checkpoint.

---

## 7.2 Founder package quality upgrade

### Goal

Improve founder package to support signal review decisions after new quality layers.

### Scope

Add sections:

- Time-sensitive opportunities.
- Implied burdens.
- Price signals.
- Weak pattern candidates.
- Kill archive warnings.
- Customer voice query yield.
- LLM review outputs if available.
- Evidence confidence/risk notes.

### Acceptance criteria

- [x] **7.2.1** Founder package shows implied burden signals.
- [x] **7.2.2** Founder package shows price signals.
- [x] **7.2.3** Founder package shows weak patterns.
- [x] **7.2.4** Founder package shows kill archive warnings.
- [x] **7.2.5** Founder package remains readable and deterministic.
- [x] **7.2.6** Full validation passes.

### Expected files

- `src/oos/discovery_weekly.py`
- `src/oos/founder_package.py`
- `tests/test_founder_package_quality_upgrade.py`
- `docs/dev_ledger/02_mini_epics/7.2-founder-package-quality-upgrade.md`
- `docs/dev_ledger/03_run_reports/7.2-founder-package-quality-upgrade.md`

### Completion notes

- Completed as a deterministic founder-package display upgrade with compact quality sections for time sensitivity, implied burdens, price signals, weak patterns, kill archive warnings, customer voice query yield, offline LLM review outputs, and evidence confidence/risk notes.
- Optional upstream artifacts are rendered when present and otherwise produce clear empty states; no new weak-pattern, kill-archive, or LLM execution engines were added.
- Price hints remain evidence-only and preserve citations from the 5.2 price signal extractor without inventing budgets.
- No dependencies, internet/API calls, or live LLM calls were added.

---

# Milestone H Р В Р вЂ Р В РІР‚С™Р Р†Р вЂљРЎСљ End-to-End Validation and Completion

## 8.1 v2.4 end-to-end fixture and live-smoke validation

### Goal

Prove the v2.4 signal quality system works from live/fixture evidence through founder package.

### Scope

- Fixture run.
- HN live smoke.
- GitHub live smoke.
- Mixed live smoke.
- Optional source comparison.
- Validation report.

### Acceptance criteria

- [x] **8.1.1** Fixture run passes.
- [x] **8.1.2** HN live smoke passes.
- [x] **8.1.3** GitHub live smoke passes.
- [x] **8.1.4** Mixed live smoke passes.
- [x] **8.1.5** Top-3 signals include at least one real finance pain.
- [x] **8.1.6** Marketing/generated false positives do not dominate top results.
- [x] **8.1.7** `needs_human_review` is used for ambiguity.
- [x] **8.1.8** Git status clean after runtime artifact handling.
- [x] **8.1.9** Validation report recorded.

### Expected files

- `docs/dev_ledger/03_run_reports/8.1-v2-4-end-to-end-validation.md`
- `docs/dev_ledger/02_mini_epics/8.1-v2-4-end-to-end-validation.md`

### Completion notes

- Completed as a validation/report package only; no pipeline redesign, source expansion, unit-test live network calls, or live LLM/API calls were added.
- Fixture validation exercised evidence, cleaning/classification, candidate signals, price signals, founder package quality sections, and meaning-loop dry-run artifacts.
- Bounded live HN, GitHub, and mixed HN/GitHub smokes completed through existing collector mode with small query/result limits.
- Final live smoke validation produced no failed checks and one warning for GitHub top-3 user-pain-like count below threshold; mixed top-3 included finance pain, `needs_human_review` appeared in live GitHub/mixed outputs, and marketing/install/generic false positives did not dominate top results.

---

## 8.2 Roadmap v2.4 completion checkpoint

### Goal

Close Roadmap v2.4 with a clean final state.

### Scope

- Verify all completed items.
- Full test discovery.
- `oos-validate.ps1`.
- `verify.ps1`.
- Roadmap state update.
- Dev Ledger final report.
- No release tag unless explicitly approved.

### Acceptance criteria

- [x] **8.2.1** Full unittest discovery passes.
- [x] **8.2.2** `oos-validate.ps1` passes.
- [ ] **8.2.3** `verify.ps1` passes.
- [x] **8.2.4** `git diff --check` passes.
- [ ] **8.2.5** Roadmap status updated:
  - Current item: `Completed / final milestone state`.
  - Completed: `17 / 17`.
  - Remaining: `0 / 17`.
- [x] **8.2.6** Dev Ledger final state updated.
- [x] **8.2.7** No push/merge/tag/release unless explicitly approved.

### Expected files

- `docs/dev_ledger/02_mini_epics/8.2-roadmap-v2-4-completion-checkpoint.md`
- `docs/dev_ledger/03_run_reports/roadmap-v2-4-completion-checkpoint.md`
- `docs/roadmaps/OOS_roadmap_v2_4_signal_quality_and_ai_layers_checklist.md`

### Checkpoint notes

- Full unittest discovery passed with `Ran 653 tests`.
- `scripts/oos-validate.ps1` passed with `Ran 653 tests`.
- `verify.ps1` could not be run because no root-level `verify.ps1` file exists in this repository checkout.
- `git diff --check` passed for the checkpoint changes.
- Final `17 / 17` roadmap closure is not marked because the final `8.2` completion checkpoint still needs to be re-run after gap closure.
- No release tag was created.

---

# 9. Deferred Items

These are intentionally not part of v2.4 unless explicitly pulled forward.

## 9.1 Reddit collector

Deferred until:

- live relevance hardening is stable;
- noise rate is acceptable;
- source compliance review is complete;
- source-specific limits are defined.

Suggested acceptance threshold before Reddit:

```yaml
reddit_ready_when:
  consecutive_real_runs: 2
  top_3_relevant_finance_signals: true
  estimated_noise_rate: "< 30%"
  no_unhandled_privacy_findings: true
```

## 9.2 Facebook automation

Automatic Facebook group/profile scraping is out of scope.

Allowed future path:

- manual `facebook_manual` evidence mode;
- official Pages API only after legal/platform checkpoint.

## 9.3 Temporal Pain Tracking

Important but not part of v2.4 core implementation.

Potential future roadmap:

- `PainSignalTimeSeries`;
- acceleration score;
- weekly cluster trajectory;
- maturity stage.

## 9.4 Negative Space Analysis and Persona Synthesis

Deferred until corpus size is sufficient.

Suggested threshold:

- at least 50 high-quality CandidateSignals for one topic;
- at least 3 weekly runs;
- at least 2 source types represented.

---

# 10. Standard Validation Policy

Each mini-epic should run:

```powershell
$env:PYTHONPATH="src"; .\.venv\Scripts\python.exe -m unittest <focused tests> -v
$env:PYTHONPATH="src"; .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\scripts\oos-validate.ps1
.\scripts\verify.ps1
git diff --check
```

## 10.1 Git policy

- Use targeted `git add`.
- Do not use `git add .`.
- Local commits after each item.
- Push/PR only at agreed checkpoints.
- No force push unless explicitly approved.
- No merge/tag/release unless explicitly approved.

## 10.2 Known local warnings

Known ACL warnings may appear for:

- `.test-tmp/`
- `.tmp_tests/`
- `tmpcvst80r6/`
- `tmp7lj5knwe/`

Ignore them only if `git status --short` shows no real project file changes beyond intended edits.

---

# 11. Suggested Implementation Order

The default order is roadmap order.

If Codex usage is constrained, prioritize:

1. **1.1 Live collection relevance hardening**
2. **1.2 Live quality acceptance smoke**
3. **2.1 Customer Voice Query Generator**
4. **2.2 Customer Voice Query Planner Integration**
5. **5.1 LLM Signal Review Offline Dry-Run**
6. **5.2 Price Signal Extraction**
7. **7.2 Founder Package Quality Upgrade**

Then continue with semantic relevance and LLM infrastructure.

Reasoning:

- Quality hardening fixes current live-noise problem.
- Customer Voice Queries expands the search space cheaply.
- Implied Burden catches high-value hidden pains.
- Price Signals help prioritize willingness-to-pay.
- Founder Package upgrade makes outputs usable.

---

# 12. Completion Summary Template

At the end of every item, Codex must report:

```text
Branch:
Commit:
Files changed:
Implemented:
Validation:
Roadmap state:
Git status:
Explicit:
- No push performed unless requested
- No PR created unless requested
- No merge performed unless requested
- No tag/release created
- No live LLM/API calls unless explicitly enabled
- No live internet/API calls during tests/validation
```
