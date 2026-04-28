# OOS Roadmap v2.3 - Source Intelligence Layer Checklist

## 0. Current Position

- [x] **0.1.1** Roadmap v2.2 completed: **16 / 16 mini-epics**
- [x] **0.1.2** Roadmap v2.2 final state: **Completed / final milestone state**
- [ ] **0.2.1** Current phase: **Roadmap v2.3 - Autonomous Source Intelligence Layer**
- [ ] **0.2.2** Current item: **8.1**
- [ ] **0.2.3** Total mini-epics in this roadmap: **16**
- [ ] **0.2.4** Completed from this roadmap: **12 / 16**
- [ ] **0.2.5** Remaining: **4 / 16**

---

## 1. Core Product Goal

OOS should autonomously collect public internet evidence from approved sources, extract market pain/buying/workaround signals, score and cluster them, and feed them into the existing OOS meaning loop.

The founder should define topics, approve sources, review shortlisted opportunities, approve or reject suggested priority changes, and make final decisions. The founder should not manually copy posts or format JSONL as the normal workflow.

```text
approved public sources
-> raw evidence
-> cleaning/classification
-> candidate signals
-> source yield analytics
-> weekly discovery package
-> OOS v2.2 meaning loop
-> founder review
```

---

## 2. Operating Rules For Every Mini-Epic

- [ ] No live LLM calls.
- [ ] No secrets committed.
- [ ] No external dependencies without explicit approval.
- [ ] Real public API/RSS collectors are allowed only in the specific collector items.
- [ ] All tests must be fixture/offline-first.
- [ ] Every run must write run reports or validation evidence.
- [ ] Founder remains final decision-maker.
- [ ] Roadmap updates happen only after validation passes.
- [ ] Dev Ledger updates happen only after validation passes.
- [ ] Use targeted `git add`; never use `git add .`.
- [ ] Preserve Windows-native PowerShell and `.venv` workflow.

### Required validation commands for every item

```powershell
$env:PYTHONPATH="src"; .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\scripts\oos-validate.ps1
.\scripts\verify.ps1
```

Every item must also run focused tests, write a run report / validation evidence file, update this roadmap, update the Dev Ledger, and make one local commit with targeted staging only.

### Stop conditions

Stop and ask before continuing if:

- acceptance criteria conflict;
- a new dependency is required;
- a secret, credential, or live external service is required outside the item scope;
- roadmap scope/order must change;
- repeated validation failures cannot be fixed within scope;
- a destructive tracked-file operation is needed;
- push, merge, tag, or release creation is requested or required.

---

## 3. Source And Compliance Rules

- [ ] **3.1** Reddit is Phase C controlled internal research; default standard-discovery source after collector implementation; no executable Reddit `QueryPlan` while `collector_available: false`.
- [ ] **3.2** G2 is disabled; `access_realistic_for_solo_founder: false`; `commercial_review_required: true`; no G2 collector in v2.3.
- [ ] **3.3** Capterra and Trustpilot are later access-review candidates, not guaranteed free sources.
- [ ] **3.4** Stack Exchange is Phase B; `requires_registered_app_key: true` for production/high-volume use; no secrets committed; tests are fixtures/mocks.
- [ ] **3.5** Feedback loop only produces `suggested_priority_updates`; founder approval is required before application.
- [ ] **3.6** `RawEvidence.author_or_context` stores role/context, not username/handle by default.
- [ ] **3.7** `ai_cfo_smb` is the first active topic.
- [ ] **3.8** `insurance_israel` and `life_management_system` may appear only as inactive future topics.
- [ ] **3.9** HN/GitHub ambiguous evidence defaults to `needs_human_review`, not `noise`.
- [ ] **3.10** Evidence cleaner v2.3 performs no boilerplate removal.
- [ ] **3.11** Every scoring dimension defines `measurement_method`: `rule_based`, `llm_stub`, or `founder_manual`.
- [ ] **3.12** Acceptance tests must prove `weekly_discovery_package -> idea/opportunity -> extracted signal -> raw evidence -> source_url`.

### Reddit controlled internal research policy

- [ ] Reddit is a high-value default internal research source once `collector_available: true`.
- [ ] Until a Reddit collector exists, Query Planner must not generate executable Reddit `QueryPlan` records.
- [ ] Standard discovery should include Reddit automatically after collector implementation; no manual per-run enabling should be required.
- [ ] Reddit-derived data must not store usernames by default.
- [ ] Reddit-derived data must not store bulk thread dumps by default.
- [ ] Reddit-derived data must not be distributed to third parties.
- [ ] Reddit-derived data must not be used for model training.
- [ ] External/commercial productization of Reddit-derived data requires a separate review checkpoint.
- [ ] Reddit storage requires `source_url` plus relevant excerpt or summary; selected context is allowed, full thread archive is not the default.
- [ ] Reddit scaling should follow measured yield, and signal quality should not be reduced for abstract caution alone.
- [ ] Reddit collector implementation is a candidate after evidence extraction/scoring item **5.2**, unless the owner explicitly reprioritizes.

---

## 4. Implementation Items

## 1.1. Source Intelligence spec v0.3 and access policy closure
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Phase:** 1

### Goal

Create and record the final v0.3 implementation spec for the Source Intelligence Layer.

### Tasks

- [x] **1.1.1** Create `docs/architecture/source_intelligence_layer_v0_3.md`.
- [x] **1.1.2** Encode G2 disabled with `access_realistic_for_solo_founder: false`.
- [x] **1.1.3** Encode Reddit as Phase C controlled internal research with `collector_available: false` until implemented.
- [x] **1.1.4** Encode Stack Exchange registered app key policy.
- [x] **1.1.5** Mark Trustpilot/Capterra as later access-review candidates.
- [x] **1.1.6** Encode privacy rule for `author_or_context`.
- [x] **1.1.7** Encode founder-approved-only feedback.
- [x] **1.1.8** Set `ai_cfo_smb` as first active topic.
- [x] **1.1.9** Mark undefined/future topics inactive.
- [x] **1.1.10** Add focused validation if useful.

### Acceptance

- [x] v0.3 spec exists.
- [x] Source access policy is explicit.
- [x] No source is treated as available without access/terms status.
- [x] No implementation code yet except tests if necessary.
- [x] Dev Ledger mini-epic record exists.
- [x] Validation evidence is recorded.

---

## 1.2. Run-report and validation-log standardization
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Phase:** 1

### Goal

Prevent manual PowerShell copy/paste validation by making run reports standard.

### Tasks

- [x] **1.2.1** Define validation log location.
- [x] **1.2.2** Define run report naming convention.
- [x] **1.2.3** Define required report fields for Codex/CLI runs.
- [x] **1.2.4** Update `docs/dev_ledger/operations/validation_policy.md`.
- [x] **1.2.5** Add helper script changes only if narrow and compatible.

### Acceptance

- [x] Every future item must record validation evidence in file.
- [x] No manual-only validation gate.
- [x] No `git add .`.
- [x] Windows-native commands documented.

---

## 2.1. RawEvidence model and artifact store
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Phase:** 2

### Goal

Introduce `RawEvidence` as the canonical stored source object before signal extraction.

### Required fields

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

### Acceptance

- [x] `RawEvidence` can round-trip through artifact store.
- [x] `source_url` is preserved.
- [x] `content_hash` is deterministic.
- [x] `author_or_context` stores role/context, not usernames/handles by default.
- [x] No network required in tests.

---

## 2.2. Source Registry and Query Planner
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Phase:** 2

### Goal

Create source registry and topic profile config/contracts.

### Scope

- `SourceRegistry` schema.
- `TopicProfile` schema.
- `ai_cfo_smb` active profile.
- Future inactive stubs for `insurance_israel` and `life_management_system` only if clearly inactive.
- `QueryPlan` schema.
- max queries per source x topic.
- query kind priority.
- URL/content-hash dedup before evidence store.

### Acceptance

- [x] Query Planner prevents combinatorial explosion.
- [x] Default max query cap is explicit.
- [x] Unsupported/disabled sources are skipped.
- [x] No undefined active topics.

---

## 3.1. Collection Scheduler, CollectionLimits, and collector interface
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Phase:** 3

### Goal

Define scheduling and collector contracts before real collectors.

### Scope

- `CollectionLimits`
- `CollectionScheduler`
- `BaseCollector` interface
- `MockCollector` / `FixtureCollector`
- offline test fixtures

### Acceptance

- [x] Deterministic collection queue.
- [x] Disabled sources skipped.
- [x] Limits enforced.
- [x] No live network in tests.

---

## 4.1. Hacker News Algolia collector
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Phase:** 4

### Goal

Implement the first low-friction public collector.

### Scope

- HN Algolia search adapter.
- Public API/RSS-safe assumptions.
- Fixture-first tests.
- Live network optional only if explicitly enabled by flag/config.
- Default test mode offline.
- Collect `RawEvidence`, not signals directly.

### Acceptance

- [x] Offline fixture test passes.
- [x] Raw evidence includes `source_url`.
- [x] `query_kind` and `topic_id` preserved.
- [x] Ambiguous HN evidence is not classified as noise by default later.

---

## 4.2. GitHub Issues collector
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Phase:** 4

### Goal

Collect pain/workaround/feature request evidence from GitHub Issues.

### Scope

- Public GitHub issues/search adapter.
- Fixture-first tests.
- Live network disabled by default.
- No tokens/secrets committed.

### Acceptance

- [x] Issue title/body/comments supported by fixture where useful.
- [x] `source_url` preserved.
- [x] Issue metadata stored in `raw_metadata`.
- [x] Ambiguous GitHub evidence is not classified as noise by default later.

---

## 4.3. Stack Exchange and RSS/regulatory collectors
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Phase:** 4

### Goal

Add the second public API collector and simple RSS collector.

### Stack Exchange policy

- `requires_registered_app_key: true` for production/high-volume use.
- No key committed.
- Offline tests from fixtures.
- API key optional in local env but not required for tests.

### RSS policy

- Generic RSS collector.
- Regulator/changelog/feed sources.
- No scraping beyond feed content.

### Acceptance

- [x] Stack Exchange collector disabled or low-limit-safe without key.
- [x] RSS collector parses fixture feed.
- [x] Raw evidence `source_url` preserved.
- [x] No secrets committed.

---

## 5.1. Evidence cleaner and classifier
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Phase:** 5

### Goal

Normalize raw evidence and classify whether it may contain useful market signals.

### Cleaner v2.3

- whitespace normalization
- URL normalization
- content hash
- no boilerplate removal

### Classifier labels

- `pain_signal_candidate`
- `workaround_signal_candidate`
- `buying_intent_candidate`
- `competitor_weakness_candidate`
- `trend_trigger_candidate`
- `needs_human_review`
- `noise`

### Acceptance

- [x] HN/GitHub ambiguity floor tested.
- [x] Obvious spam/noise still can be noise.
- [x] No source evidence is deleted by classifier.

---

## 5.2. Evidence-to-signal extraction and scoring measurement methods
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Phase:** 5

### Goal

Extract `CandidateSignal` records from `RawEvidence`.

### CandidateSignal fields

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

### Acceptance

- [x] One `RawEvidence` can yield zero, one, or many `CandidateSignal` records.
- [x] Every signal links back to `evidence_id` and `source_url`.
- [x] Scoring dimensions expose `measurement_method`.
- [x] Unsupported dimensions are not silently treated as measured.
- [x] No live LLM calls.

---

## 6.1. Source Yield Analytics and founder-approved feedback suggestions
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [ ] Done  
**Phase:** 6

**MVP overlay note:** Full `6.1` Source Yield Analytics is deferred by the MVP execution overlay. `6.2` is completed as MVP weekly discovery CLI lite; full `6.1` remains incomplete.

### Goal

Measure which source/topic/query-kind combinations produce useful signals.

### Yield key

```text
source_id x topic_id x query_kind
```

### Metrics

- `queries_run`
- `evidence_collected`
- `candidate_signals_extracted`
- `high_quality_signals`
- `opportunities_created`
- `ideas_shortlisted`
- `founder_approved_count`
- `founder_killed_count`

### Acceptance

- [ ] Source-level and source x topic x query-kind metrics exist.
- [ ] `suggested_priority_updates` are generated but not applied.
- [ ] Founder approval gate is explicit.

---

## 6.2. Weekly discovery CLI and run reports
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Phase:** 6

**MVP overlay note:** Completed as MVP weekly discovery CLI lite. Full production hardening and full source yield analytics can be expanded later.

### Goal

Create one command for autonomous discovery up to candidate signals / discovery package.

### Example command

```powershell
python -m oos.cli run-discovery-weekly `
  --topic ai_cfo_smb `
  --since-days 7 `
  --project-root .
```

### Acceptance

- [x] Offline fixture mode works.
- [x] Local fixture/raw-evidence input path runs; live collector queue remains offline/deferred for MVP lite.
- [x] Raw evidence store is written.
- [x] Cleaning/classification runs.
- [x] Signal extraction runs.
- [x] Source yield lite counters are written; full `6.1` analytics remains deferred.
- [x] Run report/log file is written.
- [x] No live network unless explicitly enabled.

---

## 7.1. Founder Discovery Package
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [x] Done
**Phase:** 7

**MVP overlay note:** Completed as Founder Discovery Package lite. Full traceability/compliance hardening remains deferred to `7.2`.

### Goal

Produce a reviewable founder-facing discovery package.

### Package sections

- executive summary
- source coverage
- strongest evidence
- strongest signal candidates
- `needs_human_review` queue
- source yield summary
- suggested priority updates
- next recommended discovery actions

### Acceptance

- [x] Founder package is generated from fixture discovery run.
- [x] Founder decisions are not automated.
- [x] Suggested priority updates require founder approval.

---

## 7.2. Traceability, regression, and compliance hardening
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [ ] Done  
**Phase:** 7

**MVP overlay note:** Full `7.2` Traceability/compliance hardening is deferred by the MVP execution overlay. Next MVP target is `8.1-lite` meaning-loop dry run.

### Goal

Add acceptance tests for source traceability and policy constraints.

### Required traceability test

```text
weekly_discovery_package
-> candidate signal
-> raw evidence
-> source_url
```

### Acceptance

- [ ] Traceability cannot be broken silently.
- [ ] No usernames/handles in `author_or_context` by default.
- [ ] Disabled sources skipped.
- [ ] No secrets required for test suite.
- [ ] No live LLM calls.
- [ ] No unapproved priority auto-update.
- [ ] Progress-tolerant acceptance tests.

---

## 8.1. Existing meaning-loop integration dry run
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [ ] Done  
**Phase:** 8

### Goal

Feed discovered candidate signals into the existing v2.2 meaning loop safely.

### Scope

- Adapter from `CandidateSignal` to existing signal input.
- Fixture-only dry run.
- Preserve source traceability through raw evidence -> candidate signal -> canonical signal -> cluster -> opportunity -> idea/founder package.

### Acceptance

- [ ] End-to-end fixture run completes.
- [ ] `source_url` traceability survives to founder review package or index.
- [ ] No live LLM calls.
- [ ] No founder decision is automated.

---

## 8.2. Roadmap v2.3 completion checkpoint
**Status:** [ ] Not started  [ ] In progress  [ ] Blocked  [ ] Done  
**Phase:** 8

### Goal

Finalize Roadmap v2.3.

### Acceptance

- [ ] Current item: `Completed / final milestone state`.
- [ ] Completed: `16 / 16`.
- [ ] Remaining: `0 / 16`.
- [ ] Full validation evidence recorded.
- [ ] Dev Ledger updated.
- [ ] No push/merge/tag/release unless explicitly approved.

---

## 5. Milestones

- [x] **5.1** Milestone A: Source policy and validation reporting ready after **1.2**
- [x] **5.2** Milestone B: Raw evidence and bounded query planning ready after **2.2**
- [x] **5.3** Milestone C: Collector contracts ready after **3.1**
- [ ] **5.4** Milestone D: First public collectors fixture-safe after **4.3**
- [x] **5.5** Milestone E: Evidence classification and candidate signals ready after **5.2**
- [x] **5.6** Milestone F: Discovery run and yield feedback suggestions ready after **6.2**
- [ ] **5.7** Milestone G: Founder discovery package and compliance hardening ready after **7.2**
- [ ] **5.8** Milestone H: Source Intelligence v2.3 complete after **8.2**

---

## 6. Commit Requirements

Every completed item must use targeted staging only. Example:

```powershell
git add docs\roadmaps\OOS_roadmap_v2_3_source_intelligence_checklist.md
git add docs\dev_ledger\00_project_state.md
git add docs\dev_ledger\02_mini_epics\<item-file>.md
git add docs\dev_ledger\03_run_reports\<run-report>.md
git commit -m "<clear item message>"
```

Never stage `.test-tmp`, `.tmp_tests`, `.venv`, secrets, generated runtime artifacts, or unrelated files.
