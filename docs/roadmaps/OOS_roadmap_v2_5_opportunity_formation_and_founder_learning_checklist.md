# OOS Roadmap v2.5 - Opportunity Formation & Founder Learning

## 0. Roadmap Overview

### Active Roadmap

- [ ] **0.1** Active roadmap: `docs/roadmaps/OOS_roadmap_v2_5_opportunity_formation_and_founder_learning_checklist.md`
- [ ] **0.2** Current item: **1.1 Founder manual review labels for first real run**
- [ ] **0.3** Roadmap state: `active / planned`
- [ ] **0.4** Completed from this roadmap: **0 / 24**
- [ ] **0.5** Remaining: **24 / 24**
- [ ] **0.6** Primary architecture reference: `docs/architecture/source_intelligence_signal_strategy_v0_5.md`

### Core Concept

Real open-source signals -> source/query quality hardening -> deterministic evidence pack -> LLM-assisted opportunity synthesis -> deterministic quality gate -> founder decision -> feedback into future scoring/review -> weekly action plan.

### Strategic Principles

- Evidence first: opportunity formation must cite source evidence, evidence IDs, source URLs, and risk/confidence notes.
- Deterministic first: cleanup, suppression, deduplication, evidence packs, and quality gates run before any LLM synthesis.
- Founder-led: founder decisions remain the authority for promote, park, kill, revisit, and needs-more-evidence outcomes.
- Narrow learning loop: founder feedback becomes deterministic pattern memory and scoring/review guidance, not ML training.
- Quality over source expansion: v2.5 improves the HN/GitHub open-source signal loop before broadening sources.
- Fixture-safe validation: tests and validation remain offline and deterministic.
- Runtime hygiene: live run artifacts stay under ignored artifact paths and must not create tracked changes.

### First Real Run Lessons

- HN + GitHub Issues collected `20` raw evidence items and produced `18` candidate signals.
- Top 10 included at least three plausible finance/SMB pains:
  - unpaid invoice follow-up / SMB cash collection pain;
  - YNAB balance-sheet / month-end reporting need;
  - SMB bookkeeping via sticky notes / Excel / inability to afford a developer.
- GitHub Issues produced marketing/vendor/SEO noise, including product-promo and service-page-like records.
- Candidate signals included duplicates, especially around HN accounting-agent and Winstwaker bookkeeping-service items.
- Founder-facing text still needs mojibake protection for fragments such as `вЂ™` and `вЂў`.
- Price extraction produced false positives:
  - `$75` receipt threshold treated as a spend hint;
  - `$1.25M` Section 179 deduction limit partially extracted as `$1.25`;
  - generic `affordable pricing` remained low confidence but still needs conservative handling.
- Weak patterns and kill archive warnings had clear empty states.
- `needs_human_review` was useful for ambiguity, with `6` first-run cases.

### Explicit Out Of Scope

- Broad source expansion.
- Live LLM execution by default.
- UI/dashboard work.
- New collectors.
- Reddit, Facebook, LinkedIn, scraping-heavy sources, or paid APIs.
- Embeddings/vector search unless explicitly approved in a future roadmap.
- ML training claims from founder feedback.
- Automated opportunity promotion.

### LLM Role Statement

LLM is a synthesis helper, not a judge, not a decision-maker. It may summarize an evidence pack, cite evidence IDs, and expose unsupported assumptions, but it must not invent buyers, prices, market sizes, product strategies, or founder decisions.

### Workflow Rules

- One feature block = one branch.
- Local commit per item.
- Push/PR/merge only at the end of a feature block and only when explicitly requested.
- Windows-native only: PowerShell, native Python venv, VS Code/Codex.
- No WSL/Linux-first assumptions.
- No live LLM/API calls by default.
- Unit tests must not make live network calls.
- Live source runs are allowed only for explicitly scoped controlled comparison items.

> Roadmap status tracks **24 implementation items**. The two controlled live comparison checkpoints, `1.6` and `7.4`, are required validation checkpoints for quality comparison and are tracked in their sections without increasing the implementation-item count.

---

# 1. First Real Run Review & Source Quality Hardening

## 1.1 Founder manual review labels for first real run

### Goal

Create structured founder labels for the 18 first-run candidate signals.

### Scope

- Define a deterministic label artifact for candidate signals.
- Support labels: `useful`, `weak`, `noise`, `duplicate`, `vendor_promo`, `price_false_positive`, `needs_more_evidence`.
- Preserve `candidate_signal_id`, `evidence_id`, `source_url`, founder note, and decision timestamp if existing conventions require one.
- Load the first-run candidate signal artifact as local input only.

### Expected files

- `src/oos/founder_signal_review.py`
- `tests/test_founder_signal_review.py`
- `docs/dev_ledger/02_mini_epics/1.1-founder-manual-review-labels.md`
- `docs/dev_ledger/03_run_reports/1.1-founder-manual-review-labels.md`

### Acceptance criteria

- [ ] **1.1.1** Founder label model exists and serializes.
- [ ] **1.1.2** All seven label values are supported.
- [ ] **1.1.3** Labels preserve candidate/evidence/source traceability.
- [ ] **1.1.4** Duplicate/vendor/price-false-positive labels are representable.
- [ ] **1.1.5** First-run review fixture can be loaded without live network calls.
- [ ] **1.1.6** Full validation passes.

### Validation expectations

- Focused unit tests for label serialization and first-run fixture loading.
- Full unittest discovery.
- `scripts/oos-validate.ps1`.
- `git diff --check`.

---

## 1.2 GitHub vendor-promo / SEO suppressor

### Goal

Reduce false positives from GitHub Issues where SEO/vendor/product-promo text is mistaken for pain.

### Scope

- Add deterministic suppressor rules for vendor-promo, SEO, and product-listing patterns.
- Apply to classifier/scoring/founder-package ordering without blocking real issue requests.
- Address first-run examples:
  - Zoho Books promo;
  - BUSY Software promo;
  - Corporate accounting software SEO text;
  - bookkeeping expert marketing page;
  - QuickBooks MCP submission/product listing.

### Expected files

- `src/oos/evidence_classifier.py`
- `src/oos/candidate_signal_extractor.py`
- `src/oos/signal_scoring.py`
- `tests/test_github_vendor_promo_suppressor.py`
- `docs/dev_ledger/02_mini_epics/1.2-github-vendor-promo-seo-suppressor.md`
- `docs/dev_ledger/03_run_reports/1.2-github-vendor-promo-seo-suppressor.md`

### Acceptance criteria

- [ ] **1.2.1** Known vendor-promo examples are downgraded or marked `needs_human_review`.
- [ ] **1.2.2** Product listing/submission text does not rank as strong pain.
- [ ] **1.2.3** Real feature requests, such as the YNAB balance-sheet need, remain eligible.
- [ ] **1.2.4** Founder package explains suppression when useful.
- [ ] **1.2.5** No live internet/API calls in tests.
- [ ] **1.2.6** Full validation passes.

### Validation expectations

- Fixture tests covering each named first-run false-positive pattern.
- Regression test proving at least one real GitHub finance workflow issue remains above generic vendor copy.
- Full validation.

---

## 1.3 PriceSignal false-positive hardening

### Goal

Avoid treating tax thresholds, deduction limits, receipt thresholds, and random money amounts as current spend or willingness-to-pay.

### Scope

- Harden deterministic price extraction.
- Distinguish spend/budget/price complaint from regulatory thresholds and accounting/tax reference values.
- Address first-run examples:
  - `$75` receipt threshold;
  - `$1.25M` Section 179 deduction limit being parsed as `$1.25`;
  - weak generic `affordable pricing` as low-confidence only.

### Expected files

- `src/oos/price_signal_extractor.py`
- `tests/test_price_signal_extractor.py`
- `tests/test_price_signal_false_positive_hardening.py`
- `docs/dev_ledger/02_mini_epics/1.3-price-signal-false-positive-hardening.md`
- `docs/dev_ledger/03_run_reports/1.3-price-signal-false-positive-hardening.md`

### Acceptance criteria

- [ ] **1.3.1** Receipt thresholds are not extracted as current spend.
- [ ] **1.3.2** Tax/deduction limits are not truncated into fake spend hints.
- [ ] **1.3.3** Generic `affordable pricing` remains low-confidence and does not imply budget.
- [ ] **1.3.4** Explicit spend and price complaints still extract correctly.
- [ ] **1.3.5** Evidence citation remains required.
- [ ] **1.3.6** Full validation passes.

### Validation expectations

- Focused false-positive fixtures.
- Existing price signal extractor tests.
- Full validation.

---

## 1.4 Candidate signal dedup before founder package

### Goal

Prevent duplicate candidate signals from appearing in founder review and inflating weak patterns.

### Scope

- Apply deterministic candidate-level dedup before founder package display.
- Preserve all underlying evidence IDs in a canonical grouped record.
- Avoid inflating weak pattern aggregation with duplicates.
- Address first-run examples:
  - duplicate HN signals for old accounting software / agents;
  - duplicate HN Winstwaker bookkeeping service.

### Expected files

- `src/oos/signal_dedup.py`
- `src/oos/founder_package.py`
- `src/oos/weak_signal_aggregation.py`
- `tests/test_candidate_signal_dedup_founder_package.py`
- `docs/dev_ledger/02_mini_epics/1.4-candidate-signal-dedup-founder-package.md`
- `docs/dev_ledger/03_run_reports/1.4-candidate-signal-dedup-founder-package.md`

### Acceptance criteria

- [ ] **1.4.1** Duplicate candidates collapse in founder package display.
- [ ] **1.4.2** Canonical candidate preserves duplicate evidence IDs.
- [ ] **1.4.3** Dedup does not remove distinct pains from the same source.
- [ ] **1.4.4** Weak pattern aggregation uses canonical signals.
- [ ] **1.4.5** Output ordering is deterministic.
- [ ] **1.4.6** Full validation passes.

### Validation expectations

- Fixture tests for named duplicate examples.
- Founder package snapshot/structure tests.
- Full validation.

---

## 1.5 Mojibake cleanup regression test

### Goal

Prevent `вЂ™`, `вЂў`, and similar encoding garbage from reaching founder-facing summaries.

### Scope

- Add regression fixtures for common mojibake fragments seen in live outputs.
- Ensure cleanup applies before candidate summaries and founder package rendering.
- Keep UTF-8 handling deterministic and narrow.

### Expected files

- `src/oos/evidence_cleaner.py`
- `src/oos/candidate_signal_extractor.py`
- `tests/test_mojibake_cleanup_regression.py`
- `docs/dev_ledger/02_mini_epics/1.5-mojibake-cleanup-regression.md`
- `docs/dev_ledger/03_run_reports/1.5-mojibake-cleanup-regression.md`

### Acceptance criteria

- [ ] **1.5.1** `вЂ™` does not appear in cleaned/founder-facing summaries.
- [ ] **1.5.2** `вЂў` does not appear in cleaned/founder-facing summaries.
- [ ] **1.5.3** Cleanup does not corrupt valid UTF-8 punctuation.
- [ ] **1.5.4** Existing cleaner behavior is preserved.
- [ ] **1.5.5** Full validation passes.

### Validation expectations

- Focused mojibake cleanup tests.
- Existing evidence cleaner/classifier tests.
- Full validation.

---

## 1.6 Second controlled live run comparison

### Goal

Run the same bounded HN + GitHub live collection after hardening and compare quality.

### Scope

- Repeat the first-run command shape with a new run id.
- Keep limits at 10-25 items per source.
- Compare before/after quality against first-run metrics.
- Do not broaden source scope.

### Expected files

- `docs/operations/second_controlled_open_source_signal_run_protocol_v1.md`
- `docs/dev_ledger/02_mini_epics/1.6-second-controlled-live-run-comparison.md`
- `docs/dev_ledger/03_run_reports/1.6-second-controlled-live-run-comparison.md`

### Acceptance criteria

- [ ] **1.6.1** Marketing/vendor promo reduced.
- [ ] **1.6.2** Duplicate top signals reduced.
- [ ] **1.6.3** Price false positives reduced.
- [ ] **1.6.4** At least 2-3 plausible finance/SMB pains still appear.
- [ ] **1.6.5** Tracked git status clean after runtime artifact handling.
- [ ] **1.6.6** No live LLM/API calls.

### Validation expectations

- Manual bounded live run only for this checkpoint.
- Run report with counts and quality comparison.
- Safe validation after runtime artifact handling.

---

# 2. Evidence Pack Layer

## 2.1 Cluster evidence pack contract

### Goal

Define an evidence pack for clusters/opportunity seeds.

### Scope

- Add a serializable evidence pack model.
- Include candidate signals, evidence IDs, source URLs, price signals, weak pattern metadata, kill warnings, confidence/risk notes, and founder labels if available.
- Keep pack construction deterministic and evidence-bound.

### Expected files

- `src/oos/evidence_pack.py`
- `tests/test_evidence_pack_contract.py`
- `docs/dev_ledger/02_mini_epics/2.1-cluster-evidence-pack-contract.md`
- `docs/dev_ledger/03_run_reports/2.1-cluster-evidence-pack-contract.md`

### Acceptance criteria

- [ ] **2.1.1** Evidence pack model exists and serializes.
- [ ] **2.1.2** Evidence IDs and source URLs are required.
- [ ] **2.1.3** Price, weak-pattern, kill-warning, confidence, and risk fields are optional but structured.
- [ ] **2.1.4** Empty or insufficient evidence is represented explicitly.
- [ ] **2.1.5** Full validation passes.

### Validation expectations

- Focused model serialization tests.
- Evidence traceability assertions.
- Full validation.

---

## 2.2 Evidence pack builder

### Goal

Build deterministic evidence packs from signals, clusters, price signals, weak patterns, kill warnings, source URLs, and confidence/risk notes.

### Scope

- Build packs from existing discovery artifacts.
- Select representative evidence deterministically.
- Preserve duplicate evidence relationships from deduped candidates.
- Avoid inventing missing evidence.

### Expected files

- `src/oos/evidence_pack.py`
- `src/oos/discovery_weekly.py`
- `tests/test_evidence_pack_builder.py`
- `docs/dev_ledger/02_mini_epics/2.2-evidence-pack-builder.md`
- `docs/dev_ledger/03_run_reports/2.2-evidence-pack-builder.md`

### Acceptance criteria

- [ ] **2.2.1** Builder reads existing discovery artifacts.
- [ ] **2.2.2** Evidence IDs/source URLs are preserved.
- [ ] **2.2.3** Price signals attach only when evidence-bound.
- [ ] **2.2.4** Kill archive warnings attach without auto-kill.
- [ ] **2.2.5** Builder output is deterministic.
- [ ] **2.2.6** Full validation passes.

### Validation expectations

- Fixture-based builder tests.
- No live network or LLM calls.
- Full validation.

---

## 2.3 Evidence pack display in founder package

### Goal

Founder can see the actual evidence bundle behind each opportunity seed.

### Scope

- Add compact evidence pack sections to founder package outputs.
- Show cited evidence, source URLs, price hints, risk notes, and confidence summaries.
- Keep output readable and deterministic.

### Expected files

- `src/oos/founder_package.py`
- `tests/test_evidence_pack_founder_package.py`
- `docs/dev_ledger/02_mini_epics/2.3-evidence-pack-founder-display.md`
- `docs/dev_ledger/03_run_reports/2.3-evidence-pack-founder-display.md`

### Acceptance criteria

- [ ] **2.3.1** Founder package displays evidence packs when available.
- [ ] **2.3.2** Empty evidence pack state does not crash.
- [ ] **2.3.3** Evidence IDs and source URLs are visible.
- [ ] **2.3.4** Price/weak/kill/risk sections remain compact.
- [ ] **2.3.5** Full validation passes.

### Validation expectations

- Founder package fixture tests.
- Deterministic Markdown/JSON assertions.
- Full validation.

---

# 3. LLM-Assisted Opportunity Formation

## 3.1 Deterministic opportunity sketch baseline

### Goal

Create a no-LLM baseline opportunity sketch from evidence pack.

### Scope

- Generate opportunity sketch fields from evidence pack only.
- Preserve unsupported assumptions as explicit unknowns.
- Provide a control/baseline for future LLM synthesis.

### Expected files

- `src/oos/opportunity_sketch.py`
- `tests/test_opportunity_sketch_baseline.py`
- `docs/dev_ledger/02_mini_epics/3.1-deterministic-opportunity-sketch-baseline.md`
- `docs/dev_ledger/03_run_reports/3.1-deterministic-opportunity-sketch-baseline.md`

### Acceptance criteria

- [ ] **3.1.1** Opportunity sketch model exists and serializes.
- [ ] **3.1.2** Baseline sketch cites evidence IDs.
- [ ] **3.1.3** Missing buyer/price/product assumptions remain unknown.
- [ ] **3.1.4** Output is stable across repeated runs.
- [ ] **3.1.5** Full validation passes.

### Validation expectations

- Fixture-only baseline tests.
- No LLM provider usage.
- Full validation.

---

## 3.2 LLM opportunity synthesis contract

### Goal

Define a future-only LLM contract for opportunity synthesis from evidence pack.

### Scope

- Add prompt/template/schema for evidence-pack opportunity synthesis.
- Prohibit vague prompt-only synthesis.
- Require evidence IDs and unsupported-assumption disclosure.
- Keep provider calls disabled by default.

### Hard rules

- LLM receives evidence pack, not vague prompt.
- LLM cites evidence IDs.
- LLM does not invent buyer, price, market size, product, or strategy.
- LLM marks unsupported assumptions explicitly.
- LLM output is advisory only.
- No live provider call by default.

### Expected files

- `src/oos/opportunity_synthesis_contract.py`
- `src/oos/llm_budget.py`
- `tests/test_opportunity_synthesis_contract.py`
- `docs/dev_ledger/02_mini_epics/3.2-llm-opportunity-synthesis-contract.md`
- `docs/dev_ledger/03_run_reports/3.2-llm-opportunity-synthesis-contract.md`

### Acceptance criteria

- [ ] **3.2.1** Contract model/prompt exists.
- [ ] **3.2.2** Prompt requires evidence pack context.
- [ ] **3.2.3** Prompt forbids invented buyer/price/market/product/strategy claims.
- [ ] **3.2.4** Prompt requires evidence IDs and unsupported assumption fields.
- [ ] **3.2.5** No live provider call is made by default.
- [ ] **3.2.6** Full validation passes.

### Validation expectations

- Prompt contract tests.
- Budget role tests if applicable.
- No provider call tests.
- Full validation.

---

## 3.3 Offline LLM opportunity synthesis dry-run

### Goal

Run synthesis through deterministic/mock provider only.

### Scope

- Use existing mock-provider patterns.
- Read evidence packs and write synthesis dry-run JSON/Markdown.
- Validate schema and citation completeness.
- Do not call live providers.

### Expected files

- `src/oos/opportunity_synthesis_dry_run.py`
- `src/oos/cli.py`
- `tests/test_opportunity_synthesis_dry_run.py`
- `docs/dev_ledger/02_mini_epics/3.3-offline-opportunity-synthesis-dry-run.md`
- `docs/dev_ledger/03_run_reports/3.3-offline-opportunity-synthesis-dry-run.md`

### Acceptance criteria

- [ ] **3.3.1** Dry-run reads local evidence packs.
- [ ] **3.3.2** Dry-run uses deterministic/mock provider only.
- [ ] **3.3.3** Output preserves evidence IDs.
- [ ] **3.3.4** Invalid/unsupported fields fail closed or mark low confidence.
- [ ] **3.3.5** No live LLM/API calls.
- [ ] **3.3.6** Full validation passes.

### Validation expectations

- Fixture dry-run tests.
- No live provider call assertions.
- Full validation.

---

# 4. Opportunity Quality Gate v2

## 4.1 Post-synthesis quality gate

### Goal

Create a deterministic gate after opportunity synthesis.

### Scope

- Gate outputs: `pass`, `park`, `reject`.
- Gate must not auto-promote and must not replace founder decision.
- Use evidence sufficiency, false-positive suppressors, kill archive warnings, and unsupported assumptions.

### Expected files

- `src/oos/opportunity_quality_gate.py`
- `tests/test_opportunity_quality_gate.py`
- `docs/dev_ledger/02_mini_epics/4.1-post-synthesis-quality-gate.md`
- `docs/dev_ledger/03_run_reports/4.1-post-synthesis-quality-gate.md`

### Acceptance criteria

- [ ] **4.1.1** Gate returns pass/park/reject deterministically.
- [ ] **4.1.2** Gate never auto-promotes.
- [ ] **4.1.3** Gate preserves founder-decision authority.
- [ ] **4.1.4** Unsupported assumptions push toward park/reject.
- [ ] **4.1.5** Full validation passes.

### Validation expectations

- Fixture tests for pass/park/reject.
- Founder decision non-overwrite test.
- Full validation.

---

## 4.2 Evidence sufficiency scoring

### Goal

Score how well an opportunity is supported by evidence.

### Scope

Score dimensions:

- pain evidence strength;
- workaround evidence;
- buyer clarity;
- willingness-to-pay evidence;
- recurrence;
- source diversity;
- risk / ambiguity.

### Expected files

- `src/oos/opportunity_quality_gate.py`
- `tests/test_evidence_sufficiency_scoring.py`
- `docs/dev_ledger/02_mini_epics/4.2-evidence-sufficiency-scoring.md`
- `docs/dev_ledger/03_run_reports/4.2-evidence-sufficiency-scoring.md`

### Acceptance criteria

- [ ] **4.2.1** Each score dimension is explicit and serializable.
- [ ] **4.2.2** Missing price evidence does not create fake willingness-to-pay.
- [ ] **4.2.3** Source diversity is measured from evidence, not inferred.
- [ ] **4.2.4** Risk/ambiguity lowers confidence or gate outcome.
- [ ] **4.2.5** Full validation passes.

### Validation expectations

- Dimension-level unit tests.
- Edge cases for missing price/buyer/source evidence.
- Full validation.

---

## 4.3 False-positive opportunity suppressor

### Goal

Suppress generic opportunities, disguised consulting, no-buyer ideas, repeated killed patterns, and marketing-copy-derived opportunities.

### Scope

- Add deterministic opportunity-level suppressor rules.
- Use kill archive feedback without auto-killing.
- Preserve warning details for founder review.

### Expected files

- `src/oos/opportunity_quality_gate.py`
- `src/oos/kill_archive_feedback.py`
- `tests/test_false_positive_opportunity_suppressor.py`
- `docs/dev_ledger/02_mini_epics/4.3-false-positive-opportunity-suppressor.md`
- `docs/dev_ledger/03_run_reports/4.3-false-positive-opportunity-suppressor.md`

### Acceptance criteria

- [ ] **4.3.1** Generic opportunities are downgraded.
- [ ] **4.3.2** Disguised consulting patterns are downgraded.
- [ ] **4.3.3** No-buyer ideas are parked/rejected.
- [ ] **4.3.4** Marketing-copy-derived opportunities are suppressed.
- [ ] **4.3.5** Similar killed patterns create warnings, not auto-kills.
- [ ] **4.3.6** Full validation passes.

### Validation expectations

- Fixture tests for each false-positive class.
- Kill archive warning preservation tests.
- Full validation.

---

# 5. Founder Feedback Learning Loop

## 5.1 Founder decision taxonomy v2

### Goal

Make founder decisions structured and useful for future scoring.

### Scope

Supported decisions:

- `promote`
- `park`
- `kill`
- `revisit_later`
- `needs_more_evidence`

### Expected files

- `src/oos/founder_decision.py`
- `tests/test_founder_decision_taxonomy_v2.py`
- `docs/dev_ledger/02_mini_epics/5.1-founder-decision-taxonomy-v2.md`
- `docs/dev_ledger/03_run_reports/5.1-founder-decision-taxonomy-v2.md`

### Acceptance criteria

- [ ] **5.1.1** Decision taxonomy model exists and serializes.
- [ ] **5.1.2** All five decision values are supported.
- [ ] **5.1.3** Kill decisions require a structured kill reason.
- [ ] **5.1.4** Needs-more-evidence decisions preserve requested evidence type.
- [ ] **5.1.5** Full validation passes.

### Validation expectations

- Decision model tests.
- Required-field tests for kill and needs-more-evidence.
- Full validation.

---

## 5.2 Decision-to-signal feedback mapping

### Goal

Map founder decisions back to opportunity, cluster, signal, and evidence.

### Scope

- Link decisions to evidence packs and source signals.
- Preserve cluster and opportunity seed lineage.
- Produce deterministic feedback records.

### Expected files

- `src/oos/founder_feedback.py`
- `tests/test_decision_to_signal_feedback_mapping.py`
- `docs/dev_ledger/02_mini_epics/5.2-decision-to-signal-feedback-mapping.md`
- `docs/dev_ledger/03_run_reports/5.2-decision-to-signal-feedback-mapping.md`

### Acceptance criteria

- [ ] **5.2.1** Founder decisions map to opportunity IDs.
- [ ] **5.2.2** Founder decisions map to cluster IDs when available.
- [ ] **5.2.3** Founder decisions map to signal/evidence IDs.
- [ ] **5.2.4** Mapping is deterministic and serializable.
- [ ] **5.2.5** Full validation passes.

### Validation expectations

- Lineage mapping tests.
- Missing optional cluster tests.
- Full validation.

---

## 5.3 Founder preference profile draft

### Goal

Create a deterministic advisory profile: preferred pain types, rejected patterns, promoted patterns, recurring kill reasons, and areas needing more evidence.

### Scope

- Aggregate structured founder decisions into advisory pattern memory.
- Feed profile into scoring adjustment and founder package warnings.
- Do not claim ML training.

### Important

This is deterministic feedback memory:

decision taxonomy -> pattern memory -> scoring adjustment -> founder package warnings.

### Expected files

- `src/oos/founder_preference_profile.py`
- `src/oos/signal_scoring.py`
- `src/oos/founder_package.py`
- `tests/test_founder_preference_profile.py`
- `docs/dev_ledger/02_mini_epics/5.3-founder-preference-profile-draft.md`
- `docs/dev_ledger/03_run_reports/5.3-founder-preference-profile-draft.md`

### Acceptance criteria

- [ ] **5.3.1** Profile model exists and serializes.
- [ ] **5.3.2** Promoted/rejected patterns are deterministic summaries.
- [ ] **5.3.3** Recurring kill reasons are surfaced.
- [ ] **5.3.4** Profile creates advisory scoring/founder-package warnings only.
- [ ] **5.3.5** No ML training claims or behavior.
- [ ] **5.3.6** Full validation passes.

### Validation expectations

- Deterministic profile aggregation tests.
- Advisory-only scoring tests.
- Full validation.

---

# 6. Weekly Operating Loop Upgrade

## 6.1 Weekly opportunity review package

### Goal

Weekly output answers: "What should the founder do this week?"

### Scope

Sections:

- top opportunities to review;
- promote candidates;
- park candidates;
- kill candidates;
- needs more evidence;
- suggested customer interviews;
- suggested next queries;
- revisit queue.

### Expected files

- `src/oos/weekly_opportunity_review.py`
- `src/oos/cli.py`
- `tests/test_weekly_opportunity_review_package.py`
- `docs/dev_ledger/02_mini_epics/6.1-weekly-opportunity-review-package.md`
- `docs/dev_ledger/03_run_reports/6.1-weekly-opportunity-review-package.md`

### Acceptance criteria

- [ ] **6.1.1** Weekly review package model exists.
- [ ] **6.1.2** All required sections render deterministically.
- [ ] **6.1.3** Empty sections have clear empty states.
- [ ] **6.1.4** Package cites opportunity/evidence IDs.
- [ ] **6.1.5** Full validation passes.

### Validation expectations

- Fixture-based weekly package tests.
- CLI/output tests if CLI is added.
- Full validation.

---

## 6.2 Next best founder actions

### Goal

Generate deterministic next actions.

### Scope

Actions:

- approve interviews;
- collect more evidence;
- run customer voice queries;
- park;
- kill;
- revisit.

### Expected files

- `src/oos/weekly_opportunity_review.py`
- `tests/test_next_best_founder_actions.py`
- `docs/dev_ledger/02_mini_epics/6.2-next-best-founder-actions.md`
- `docs/dev_ledger/03_run_reports/6.2-next-best-founder-actions.md`

### Acceptance criteria

- [ ] **6.2.1** Action recommendation model exists and serializes.
- [ ] **6.2.2** Actions are deterministic from gate/decision/evidence state.
- [ ] **6.2.3** Actions never bypass founder approval.
- [ ] **6.2.4** Suggested customer interviews include evidence rationale.
- [ ] **6.2.5** Full validation passes.

### Validation expectations

- Action matrix tests.
- Founder approval boundary tests.
- Full validation.

---

## 6.3 Parking lot / revisit logic

### Goal

Keep parked opportunities visible and revisit them when new matching evidence appears.

### Scope

- Store deterministic parked/revisit records.
- Match new evidence using explicit pattern keys or cluster IDs.
- Surface revisit recommendations without auto-promoting.

### Expected files

- `src/oos/revisit_queue.py`
- `src/oos/weekly_opportunity_review.py`
- `tests/test_revisit_queue.py`
- `docs/dev_ledger/02_mini_epics/6.3-parking-lot-revisit-logic.md`
- `docs/dev_ledger/03_run_reports/6.3-parking-lot-revisit-logic.md`

### Acceptance criteria

- [ ] **6.3.1** Parked opportunity record exists and serializes.
- [ ] **6.3.2** New matching evidence can trigger revisit recommendation.
- [ ] **6.3.3** Revisit logic does not auto-promote.
- [ ] **6.3.4** Revisit queue is visible in weekly package.
- [ ] **6.3.5** Full validation passes.

### Validation expectations

- Revisit queue fixture tests.
- Weekly package integration tests.
- Full validation.

---

# 7. Evaluation & Metrics

## 7.1 Opportunity quality evaluation dataset v1

### Goal

Create labeled cases for opportunity formation.

### Scope

Cases:

- strong opportunity;
- weak but interesting;
- generic false positive;
- no buyer;
- no evidence;
- vendor promo false positive;
- price false positive;
- duplicate signal;
- mojibake case;
- killed-pattern repeat;
- strong pain but weak price evidence.

### Expected files

- `tests/fixtures/opportunity_quality_cases_v1.json`
- `tests/test_opportunity_quality_dataset.py`
- `docs/dev_ledger/02_mini_epics/7.1-opportunity-quality-evaluation-dataset-v1.md`
- `docs/dev_ledger/03_run_reports/7.1-opportunity-quality-evaluation-dataset-v1.md`

### Acceptance criteria

- [ ] **7.1.1** Dataset includes all required case types.
- [ ] **7.1.2** Each case includes expected gate outcome and rationale.
- [ ] **7.1.3** Each case includes evidence IDs or explicit no-evidence state.
- [ ] **7.1.4** Dataset is deterministic and fixture-only.
- [ ] **7.1.5** Full validation passes.

### Validation expectations

- Dataset schema tests.
- No live network or LLM calls.
- Full validation.

---

## 7.2 Regression metrics for opportunity quality

### Goal

Create deterministic metrics for opportunity quality.

### Scope

Metrics:

- pass/park/reject accuracy;
- evidence citation completeness;
- unsupported assumptions count;
- generic false-positive rate;
- vendor-promo false-positive rate;
- price false-positive rate;
- duplicate top-signal rate.

### Expected files

- `src/oos/opportunity_quality_metrics.py`
- `tests/test_opportunity_quality_metrics.py`
- `docs/dev_ledger/02_mini_epics/7.2-opportunity-quality-regression-metrics.md`
- `docs/dev_ledger/03_run_reports/7.2-opportunity-quality-regression-metrics.md`

### Acceptance criteria

- [ ] **7.2.1** Metrics model exists and serializes.
- [ ] **7.2.2** Metrics are computed deterministically from fixture outputs.
- [ ] **7.2.3** False-positive and duplicate rates are reported separately.
- [ ] **7.2.4** Unsupported assumptions are counted.
- [ ] **7.2.5** Full validation passes.

### Validation expectations

- Metrics fixture tests.
- Dataset integration tests.
- Full validation.

---

## 7.3 v2.5 end-to-end fixture validation

### Goal

Validate full v2.5 flow on fixtures.

### Scope

- Run source-quality fixtures through evidence packs, opportunity sketch/synthesis dry-run, quality gate, founder feedback, weekly package, and metrics.
- Do not use live network or live LLM/API calls.

### Expected files

- `tests/test_v2_5_end_to_end_fixture.py`
- `docs/dev_ledger/02_mini_epics/7.3-v2-5-end-to-end-fixture-validation.md`
- `docs/dev_ledger/03_run_reports/7.3-v2-5-end-to-end-fixture-validation.md`

### Acceptance criteria

- [ ] **7.3.1** End-to-end fixture flow passes.
- [ ] **7.3.2** Evidence packs feed opportunity sketches/synthesis outputs.
- [ ] **7.3.3** Quality gate outputs pass/park/reject.
- [ ] **7.3.4** Founder feedback maps back to signals/evidence.
- [ ] **7.3.5** Weekly package includes actionable next steps.
- [ ] **7.3.6** Full validation passes.

### Validation expectations

- End-to-end fixture test.
- Full unittest discovery.
- `scripts/oos-validate.ps1`.
- `git diff --check`.

---

## 7.4 Third controlled live run quality comparison

### Goal

Run another bounded live comparison after v2.5 core improvements.

### Scope

- Repeat bounded HN + GitHub collection.
- Compare against first and second controlled runs.
- Evaluate source/query quality, opportunity formation quality, false positives, duplicates, and price false positives.

### Expected files

- `docs/dev_ledger/02_mini_epics/7.4-third-controlled-live-run-quality-comparison.md`
- `docs/dev_ledger/03_run_reports/7.4-third-controlled-live-run-quality-comparison.md`

### Acceptance criteria

- [ ] **7.4.1** Third bounded live run executed only for this checkpoint.
- [ ] **7.4.2** Quality comparison records first/second/third run metrics.
- [ ] **7.4.3** False-positive and duplicate rates are reported.
- [ ] **7.4.4** Opportunity quality remains founder-reviewable.
- [ ] **7.4.5** Runtime artifacts leave no tracked changes.
- [ ] **7.4.6** No live LLM/API calls.

### Validation expectations

- Manual bounded live run report.
- Safe validation after runtime artifact handling.
- `git diff --check`.

---

# 8. Completion Checkpoint

## 8.1 Roadmap v2.5 final validation

### Goal

Close v2.5 cleanly.

### Scope

- Verify all completed v2.5 items.
- Run full validation.
- Update roadmap state.
- Update Dev Ledger final state.
- Do not create release tag unless explicitly approved.

### Expected files

- `docs/dev_ledger/02_mini_epics/8.1-roadmap-v2-5-final-validation.md`
- `docs/dev_ledger/03_run_reports/roadmap-v2-5-final-validation.md`
- `docs/roadmaps/OOS_roadmap_v2_5_opportunity_formation_and_founder_learning_checklist.md`
- `docs/dev_ledger/00_project_state.md`

### Acceptance criteria

- [ ] **8.1.1** Full unittest discovery passes.
- [ ] **8.1.2** `scripts/oos-validate.ps1` passes.
- [ ] **8.1.3** `git diff --check` passes.
- [ ] **8.1.4** Roadmap status is `completed`.
- [ ] **8.1.5** Completed items: `24 / 24`.
- [ ] **8.1.6** Remaining items: `0 / 24`.
- [ ] **8.1.7** Dev Ledger final state updated.
- [ ] **8.1.8** No release tag unless explicitly approved.

### Validation expectations

- Full unittest discovery.
- `scripts/oos-validate.ps1`.
- `git diff --check`.
- `git status --short --untracked-files=no`.
