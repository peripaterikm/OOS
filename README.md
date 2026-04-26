# OOS — Opportunity Operating System

## Что это

Этот репозиторий содержит:

- **OOS (Opportunity Operating System)** — систему для поиска, скрининга, проверки и портфельного управления бизнес-гипотезами.
- **Pain Discovery Layer (PDL)** — слой автономного поиска болей, который собирает и валидирует pain signals до их попадания в основной OOS pipeline.

Проект строится **поэтапно**, через документацию, тесты и маленькие implementation packages.

---

## Текущий принцип работы

Система построена как pipeline, а не как “театр агентов”.

Базовая логика OOS:

`Signal -> Opportunity -> Ideation -> Screen -> Hypothesis -> Council -> Portfolio -> Weekly Review`

Базовая логика PDL:

`Sources -> RawSourceItems -> CandidateSignals -> Validation -> Dedup -> Founder Review -> Clusters -> Promotion into OOS`

---

## Где лежит логика проекта

### Основные документы
Смотри папку `docs/`.

Типично важны:
- `docs/vision.md`
- `docs/scope-v1.md`
- `docs/build-order.md`
- документы по Pain Discovery Layer
- founder review / implementation guide / week-by-week docs

### Конфиги
Смотри папку `config/`.

Типично:
- `config/icp_profiles.json`
- `config/sources.json`
- `config/prompts/...`

### Код
Смотри:
- `src/oos/`
- `tests/`

---

## Как запускать проект

Windows and PowerShell are the primary developer environment for this repository.
Use a native Windows Python virtual environment at `.venv`; do not treat WSL/Linux as the default workflow.

### Unified developer command

Use `scripts\dev.ps1` as the single Windows-native entrypoint for common developer operations:

```powershell
.\scripts\dev.ps1 bootstrap
.\scripts\dev.ps1 verify
.\scripts\dev.ps1 dry-run
.\scripts\dev.ps1 founder-review-help
```

`.\scripts\dev.ps1 dry-run` uses a clean temporary project root by default. To write dry-run artifacts under this repository for founder review:

```powershell
.\scripts\dev.ps1 dry-run -DryRunProjectRoot .
```

### 1. Создать виртуальное окружение

PowerShell, из корня проекта:

```powershell
.\scripts\dev.ps1 bootstrap
```

Если PowerShell ругается на policy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\dev.ps1 bootstrap
```

---

### 2. Установить проект

`scripts\bootstrap.ps1` installs `requirements.txt` when present and then installs OOS in editable mode.
Manual equivalent:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

---

### 3. Прогнать тесты

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

---

### 4. Smoke test

```powershell
.\.venv\Scripts\python.exe -m oos.cli smoke-test --project-root .
```

`oos smoke-test` also works after activation, or when `.venv\Scripts` is on `PATH`:

```powershell
.\.venv\Scripts\Activate.ps1
oos smoke-test --project-root .
```

---

### 5. Dry run v1

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m oos.cli v1-dry-run --project-root .
```

После этого артефакты появляются в `artifacts/`.

---

### Runtime contract

- All v1 dry-run and weekly-review runtime I/O is rooted under the explicit `--project-root`.
- If `<project-root>\artifacts` exists and is non-empty, `v1-dry-run` refuses before mutating anything.
- The current working directory must not affect behavior when `--project-root` is provided.
- Determinism means same input produces the same class of outputs and the same weekly-review schema; timestamped filenames are not byte-identical guarantees.

---

### Real signal batch input

Canonical real signal batches use JSONL: one JSON object per line with `signal_id`, `captured_at`, `source_type`, `title`, `text`, and `source_ref`.

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m oos.cli run-signal-batch --project-root . --input-file examples\real_signal_batch.jsonl
```

Runtime output I/O is rooted under `--project-root`; produced artifacts are written under `<project-root>\artifacts`.

---

### Real founder review package

Real signal batch runs write the preferred founder workflow package to:
- `artifacts\ops\founder_review_inbox.md`
- `artifacts\ops\founder_review_index.json`

Use the inbox review IDs to record decisions without looking up internal artifact IDs:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m oos.cli record-founder-review --project-root . --review-id review-001 --decision pass
```

The review index preserves traceability to input signal IDs and linked artifacts, and the weekly review surfaces recorded founder decisions.

---

### AI-assisted ideation flag

AI assistance is enabled only for ideation. Signal ingestion, screening, council, portfolio, weekly review, and founder decisions remain unchanged.

```powershell
$env:OOS_AI_IDEATION_ENABLED = "1"
$env:OOS_AI_IDEATION_RESPONSE_JSON = '[{"short_concept":"AI-assisted workflow mapper","business_model":"subscription","standardization_focus":"repeatable workflow templates","ai_leverage":"cluster workflow breakdowns","external_execution_needed":"none","rough_monetization_model":"monthly subscription"}]'
.\.venv\Scripts\python.exe -m oos.cli run-weekly-cycle --project-root . --input-file examples\real_signal_batch.jsonl
```

If the flag is off, deterministic ideation is used. If the flag is on but AI output is unavailable, invalid, or fails validation, OOS automatically falls back to deterministic ideation.

---

### AI ideation evaluation and rollback

Evaluate assisted ideation before using it:

```powershell
$env:PYTHONPATH = "src"
$env:OOS_AI_IDEATION_RESPONSE_JSON = '[{"short_concept":"AI-assisted workflow mapper","business_model":"subscription","standardization_focus":"repeatable workflow templates","ai_leverage":"cluster workflow breakdowns","external_execution_needed":"none","rough_monetization_model":"monthly subscription"}]'
.\.venv\Scripts\python.exe -m oos.cli evaluate-ai-ideation --project-root . --input-file examples\real_signal_batch.jsonl
```

The report is written to `artifacts\evaluation\ai_ideation_evaluation.json`. Criteria are schema validity, required field completeness, downstream compatibility, traceability preservation, and non-empty useful idea content.

Rollback rules: invalid schema falls back to deterministic, empty or unusable assisted output falls back to deterministic, and assisted mode is not approved unless it passes all criteria. This evaluation applies only to ideation.

---

### Evaluation dataset v0 and heuristic baseline role

`examples\evaluation_dataset_v0\` is the first repeatable smoke-test fixture for Roadmap v2.2 AI evaluation. It contains at least 15 explicitly labeled synthetic signals, expected cluster notes, expected opportunity notes, and founder/operator quality notes. It is an early calibration fixture only; it does not implement clustering, deduplication, or AI scoring.

Current heuristic ideation is a baseline, fallback, and control group. It is good for placeholder output, fallback behavior, pipeline plumbing tests, and comparison against future AI-assisted meaning layers. It is not the primary ideation engine and should not be treated as strong opportunity discovery.

Idea artifacts now expose `generation_mode` with one of:

- `heuristic_baseline`
- `llm_assisted`
- `heuristic_fallback_after_llm_failure`

This makes later AI evaluation honest: assisted outputs can be compared against a visible control group, and fallback artifacts cannot be confused with primary LLM ideation.

---

### AI artifact contracts and prompt versioning

Future LLM-produced artifacts use common AI metadata so outputs can be compared across prompt and model changes. Required fields are `prompt_name`, `prompt_version`, `model_id`, `input_hash`, `generation_mode`, `created_at`, `linked_input_ids`, `fallback_used`, `stage_confidence`, and `stage_status`.

Prompt identity is explicit. A prompt change creates a new `prompt_version`, such as `signal_extractor_v1` then `signal_extractor_v2`; do not silently reuse the same version for changed behavior.

Input hashing uses deterministic normalized JSON. The cache key convention is:

```text
input_hash + prompt_version + model_id
```

LLM call budgets are tracked by mode:

- `economy`: warn above 12 calls
- `standard`: warn above 25 calls
- `deep`: warn above 40 calls

Future AI stages should batch work where possible. Initial planning assumes 10-20 signals per small batch and 5-10 signals per extraction/scoring chunk, rather than one LLM call per signal.

Each future AI stage must define its own rollback threshold before implementation. Fallbacks and degraded modes must be visible through metadata such as `fallback_used`, `stage_status`, `failure_reason`, `fallback_recommendation`, and `degraded_mode`.

---

### Pre-clustering signal deduplication

Signal batches get deterministic duplicate metadata before any future semantic clustering. OOS normalizes signal text by lowercasing, tokenizing alphanumeric words, and joining tokens with single spaces; the normalized fingerprint is a SHA-256 hash of that normalized text.

Exact duplicates share the same normalized fingerprint. Near duplicates use the explicit roadmap rule:

```text
near_duplicate = cosine similarity >= 0.85
on normalized signal text
```

Duplicate signals are never physically deleted. Each signal artifact carries `duplicate_group_id`, `is_duplicate`, and `canonical_signal_id`, so original signal IDs remain traceable while future clustering can use the canonical signal set to avoid inflated recurrence counts.

---

### Signal meaning extraction contract

`src/oos/signal_understanding.py` defines the Roadmap v2.2 signal-understanding boundary. It accepts a batch of existing `Signal` artifacts and a stubbed provider payload; it does not call a live LLM or API. A future provider can implement the same `SignalUnderstandingProvider.extract(signals)` interface.

Structured meaning records include `actor_user_segment`, `pain`, `context`, `current_workaround`, `urgency`, `cost_signal`, `evidence`, `uncertainty`, and `confidence`. Quality scoring includes `specificity`, `recurrence_potential`, `workaround`, `cost_signal`, `urgency`, `confidence`, and `explanation`.

Every record links back to the original `signal_id` and carries common AI metadata from `ai_contracts.py`, including prompt version, model ID, input hash, generation mode, linked input IDs, fallback status, confidence, and stage status.

Stage-level fallback rule: if fewer than 80% of non-duplicate canonical signals receive valid structured extraction, the batch is marked degraded. Failed signals get `analysis_mode = "analysis_unavailable"`, keep the raw signal ID, and do not replace existing weak/noise routing or founder review behavior.

Duplicate signals do not inflate the denominator when the canonical signal set is used. Original duplicate artifacts remain preserved for traceability.

---

### Semantic clustering contract

`src/oos/semantic_clustering.py` defines the Roadmap v2.2 semantic clustering boundary. It accepts canonical `Signal` artifacts and a stubbed provider payload; it does not call a live LLM or API. A future provider can implement the same `SemanticClusteringProvider.cluster(signals)` interface.

Clusters include `cluster_id`, `title`, `summary`, linked `signal_ids`, linked canonical signal IDs, `reasoning`, `confidence`, `uncertainty`, and common AI metadata from `ai_contracts.py`.

Deduplication happens before clustering because duplicate signals should remain traceable but must not inflate recurrence or cluster membership. The clustering layer uses `canonical_signal_set()` by default and records skipped duplicate IDs separately.

Stage-level fallback rule: if all provider clusters have `confidence < 0.4`, or if provider output is empty or invalid, OOS falls back to simple one-signal groupings and marks `low_confidence_clustering = true`. Fallback clusters preserve signal IDs and are clearly marked with fallback metadata.

This layer is standalone for now. It is not required by `run-signal-batch` yet, so existing real-batch behavior remains stable while the semantic clustering contract matures.

---

### Contradiction detection and merge candidates

`src/oos/contradiction_detection.py` defines the Roadmap v2.2 contradiction-detection boundary. It accepts canonical `Signal` artifacts, optional signal-understanding records, optional semantic clusters, and a stubbed provider payload; it does not call a live LLM or API. A future provider can implement the same `ContradictionDetectionProvider.detect(...)` interface.

A contradiction means two signals describe the same situation or process but give mutually exclusive assessments of pain, workaround, urgency, buyer/user need, or trust in the current solution. Reports include structured `ContradictionRecord` entries with linked signal IDs, canonical signal IDs when available, conflicting fields, evidence, severity (`low`, `medium`, `high`), confidence, recommendation, next action, and traceability fields.

Merge candidates are review suggestions only. `MergeCandidate` entries include source signal IDs, the applicable canonical signal ID, similarity/confidence, a recommendation, and `do_not_auto_merge = true`. The layer never physically deletes signals and never automatically merges source artifacts.

Invalid provider payloads produce a safe fallback report. Invalid individual contradiction or merge records are rejected into `rejected_record_errors` while valid records remain available, so opportunity framing can proceed without silently trusting bad claims.

This layer is standalone for now and is not required by `run-signal-batch`. It prepares opportunity framing by surfacing conflicts and possible duplicates while preserving all source IDs, canonical IDs, skipped duplicate IDs, and common AI metadata for auditability.

---

### Opportunity framing contract

`src/oos/opportunity_framing.py` defines the Roadmap v2.2 opportunity-framing boundary. It accepts semantic clusters, canonical signals, optional signal-understanding records, optional contradiction reports, and a stubbed provider payload; it does not call a live LLM or API. A future provider can implement the same `OpportunityFramingProvider.frame(...)` interface.

Opportunity cards include title, target user, pain, current workaround, why it matters, evidence, urgency, possible wedge, monetization hypothesis, risks, assumptions, a strict `non_obvious_angle`, linked cluster ID, linked signal IDs, linked canonical signal IDs, confidence, status, and common AI metadata.

Evidence and assumptions are separate. Claims that cite source material must be represented as `OpportunityEvidence` and link to valid `signal_ids` plus a valid `cluster_id`. Unsupported but useful claims belong in `OpportunityAssumption`, not evidence.

`non_obvious_angle` is a thesis that either contradicts the first obvious interpretation of the problem or identifies a segment, wedge, or monetization mechanism that does not follow directly from the literal signal wording. For example, the wedge may be restoring owner trust through reconciliation narratives rather than building another reporting dashboard.

Stage-level fallback rule: if an opportunity has no linked evidence, it is marked `evidence_missing = true`, uses `parked_evidence_missing` status, and carries fallback metadata. Source clusters and signals are preserved, and invalid provider records are rejected without deleting valid cards.

This layer is standalone for now and is not required by `run-signal-batch`. It prepares the 4.2 opportunity quality gate by making evidence, assumptions, traceability, and non-obviousness explicit before scoring.

---

### Opportunity quality gate

`src/oos/opportunity_quality_gate.py` defines a deterministic, advisory gate for framed opportunities. It does not call a live LLM or API and is not wired into `run-signal-batch` yet.

Each `OpportunityGateDecision` uses one of three statuses: `pass`, `park`, or `reject`. The gate checks for a clear user, concrete pain, linked evidence, urgency or cost signal, possible product angle, risks or uncertainty, and traceability back to source signals and cluster.

The gate is deliberately conservative. Missing target user, pain, or traceability produces `reject`; missing evidence produces `park`; missing wedge, urgency/cost, or risks/uncertainty produces `park` with warnings. Strong cards with linked evidence and complete fields pass to pattern-guided ideation.

Gate recommendations are advisory only. Founder decisions remain the final authority, and the optional `founder_override_status` field is non-invasive; it does not replace the gate status or the existing founder review flow.

This prepares Roadmap 5.1 by ensuring only sufficiently grounded opportunities move into pattern-guided ideation, while weak or pretty-but-empty opportunities are parked or rejected before idea generation.

---

### Pattern-guided ideation

`src/oos/pattern_guided_ideation.py` defines the Roadmap v2.2 pattern-guided ideation boundary. It accepts framed `OpportunityCard` objects and a stubbed provider payload; it does not call a live LLM or API and is not wired into `run-signal-batch` yet.

The product pattern library currently includes `SaaS / tool`, `service-assisted workflow`, `data product`, `marketplace / brokered workflow`, `internal automation product`, `audit / risk radar`, and `expert-in-the-loop workflow`.

The stage expects 3-5 idea variants per opportunity. Each accepted idea must include title, target user, pain addressed, product concept, wedge, why now, business model options, first experiment, assumptions, risks, selected product pattern, linked opportunity ID, linked signal IDs, generation mode, confidence, and common AI metadata.

Product-shape diversity is explicit. If fewer than two distinct product patterns are produced for an opportunity, the result carries `low_diversity_warning = true` and uses clearly labeled heuristic fallback ideas when needed. Heuristic fallback remains fallback/control only, not the primary intelligence layer.

This prepares Roadmap 5.2 by making ideation outputs structured enough to compare modes by validity, traceability, diversity, usefulness, and commercial realism.

---

### Ideation mode comparison

`src/oos/ideation_mode_comparison.py` compares ideation modes without live LLM/API calls and is not wired into `run-signal-batch` yet. It evaluates `heuristic_baseline`, `pattern_guided`, and `llm_assisted` / `llm_constrained` idea artifacts as standalone comparison inputs.

Schema validity and traceability are hard gates. Weighted criteria are relevance to input pain x2, novelty/diversity x1, commercial usefulness x2, founder fit x2, testability x1, automation potential x1, hallucination risk subtracted x1, plus a deterministic genericness penalty of `0`, `-1`, or `-2`.

Preliminary thresholds are `score >= 12` for `candidate_for_council_review`, `8-11` for `park_low_priority`, and `< 8` for `auto_park`. Generic dashboard, generic assistant, or vague SaaS language is penalized conservatively until Phase 6 adds explicit anti-pattern checks.

Mode summaries report average score, gate pass counts, candidate/park/auto-park counts, diversity signals, and an explainable preferred-mode recommendation. If LLM-constrained outputs fail gates, the recommendation points back to pattern-guided or heuristic fallback.

This prepares Phase 6 by producing a deterministic comparison layer before anti-pattern checks and council critique are allowed to select top ideas.

---

### Deterministic anti-pattern checks

`src/oos/anti_pattern_checks.py` adds a cheap deterministic pre-filter for weak idea patterns before expensive council critique. It is rule-based, contains no live LLM/API calls, and is not wired into `run-signal-batch` yet.

The current rule set detects generic dashboards, generic chatbots, generic AI assistants, "Uber for X", consulting disguised as product, founder-time-heavy services, unclear buyers, non-urgent pain, and missing or vague first experiments.

Each `AntiPatternFinding` includes the idea ID, anti-pattern ID, label, severity, explanation, matched evidence/fields, recommendation, and penalty. Checks do not delete or mutate source ideas.

The genericness penalty is exposed as a deterministic helper and is reused by ideation mode comparison as a small bridge into Phase 6. Full anti-pattern scoring remains separate from council critique.

---

### Isolated AI council critique

`src/oos/ai_council_critique.py` defines the standalone Roadmap 6.2 council boundary for top idea critique. It makes no live LLM/API calls and is not wired into `run-signal-batch` yet.

Council critique only runs on selected top ideas: scored ideas at or above the council threshold (`total_score >= 12`) or the top fallback idea per opportunity when none cross the threshold. Standard mode caps critique at 3 ideas per opportunity.

Each role is represented as an isolated provider boundary: Skeptic, Market Reality Checker, Founder Bottleneck Checker, Commercialization Critic, and Genericness Detector. Role outputs are validated separately before aggregation.

Structured critiques preserve `idea_id`, linked signal IDs, linked opportunity ID, risks, kill candidates, unsupported claims, weakest assumption, recommendation, explanation, confidence, and AI metadata. Missing or invalid role outputs preserve the idea, mark `critique_unavailable`, and require founder manual review.

If no role finds a serious risk or kill candidate, the summary marks `suspiciously_clean = true`. Founder decision authority remains final; council recommendations are advisory and prepare the Phase 7 founder feedback loop.

---

### FounderReviewPackage v2

`src/oos/founder_review_package.py` now writes a fixed FounderReviewPackage v2 structure at `artifacts/founder_review/` while preserving the legacy `artifacts/ops/founder_review_index.json` and `record-founder-review --review-id ...` workflow.

The v2 package includes `inbox.md`, `index.json`, and section files for signals, dedup, clusters, opportunities, ideas, anti-patterns, critiques, decisions, and AI quality. Sections link to source artifact IDs where available and show missing optional AI-stage artifacts without crashing generation.

This keeps founder review readable without artifact hunting and prepares Roadmap 7.2 AI-stage quality ratings.

---

### Founder AI-stage ratings and evaluation dataset v1

`src/oos/founder_ai_stage_rating.py` records advisory founder quality ratings for AI-stage outputs. Allowed ratings are `good`, `okay`, `weak`, and `wrong`; allowed stages are `signal understanding`, `clustering`, `opportunity framing`, `ideation`, and `critique`.

Use `record-ai-stage-rating` to write JSON artifacts under `artifacts/ai_stage_ratings/`. Ratings preserve linked artifact IDs and linked signal IDs, appear in FounderReviewPackage v2's `ai_quality` section when present, and are surfaced in weekly review JSON as recent advisory quality signals. They do not update portfolio state or replace founder decisions.

`examples/evaluation_dataset_v1/` expands the early fixture set to 22 explicitly synthetic signals, expected semantic cluster notes, expected opportunity notes, expected idea-quality notes, and founder quality notes. The dataset is loadable through `load_evaluation_dataset_v1()` and is meant to support repeatable comparison across future prompt/model versions.

---
### Dev Ledger

`docs/dev_ledger/` is the project memory for Roadmap v2.2 development. It records what was built, why decisions were made, rejected alternatives, validation results, known limitations, and stage-by-stage capability boundaries.

Current project state lives in `docs/dev_ledger/00_project_state.md`. Important decisions live in `docs/dev_ledger/01_decisions/` as ADRs. Completed mini-epics are backfilled in `docs/dev_ledger/02_mini_epics/`.

Each future mini-epic should update or add a concise record under `docs/dev_ledger/02_mini_epics/`. Use ADRs when a decision changes source of truth, workflow, architecture, or validation policy.

---

### Autonomous Codex workflow

Autonomous Codex workflow docs live in `docs/dev_ledger/operations/`. They define local-first execution, stop conditions, permissions, validation requirements, and commit policy for approved roadmap scopes.

Use `.\scripts\oos-status.ps1` to inspect branch, recent commits, git status, active roadmap state, and Dev Ledger project state. Use `.\scripts\oos-validate.ps1` to run full unittest discovery followed by `.\scripts\verify.ps1`.

The workflow is local commits first, push later. Codex may create local commits after green validation when approved by the workflow, but must not push or merge unless explicitly requested.

---

### 6. Founder review workflow

После `v1-dry-run` открой:
- `artifacts/readiness/<v1_readiness_...>.json`
- `artifacts/ops/v1_founder_review_checklist.md`
- `artifacts/weekly_reviews/<weekly_review_...>.json`

Checklist содержит готовые PowerShell-compatible команды `record-founder-review` для текущей среды. Запускай их из PowerShell в Windows-native `.venv`. Если передаёшь `--readiness-report-id`, `--weekly-review-id`, `--council-decision-id`, `--hypothesis-id`, `--experiment-id` или `--linked-kill-reason-id`, CLI проверяет, что соответствующий artifact существует. Для `--decision Killed` параметр `--linked-kill-reason-id` обязателен.

---

### 7. Verification commands

PowerShell, from the project root:

```powershell
.\scripts\dev.ps1 verify
```

By default, `scripts\dev.ps1 verify` runs the dry run against a clean temporary project root so existing local `artifacts/` state cannot mask workflow regressions.

Manual equivalent:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest tests.test_cli -v
.\.venv\Scripts\python.exe -m unittest tests.test_week8_end_to_end -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe -m oos.cli v1-dry-run --project-root .
```

---

## Git / GitHub

### Что не коммитить
Убедись, что в `.gitignore` исключены:
- `.venv/`
- `.env`
- `__pycache__/`
- `.pytest_cache/`
- `artifacts/`
- `reports/`

### Базовый workflow
```powershell
git status
git add .
git commit -m "Describe the change"
git push
```

---

## Работа с Codex

Для Codex в репозитории используются:

- `AGENTS.md` — правила работы агента в этом проекте
- `.codex/config.toml` — project-level конфигурация

### Рекомендуемый режим
1. сначала audit / read-only understanding,
2. потом один узкий milestone,
3. потом review,
4. потом tests,
5. потом следующий milestone.

Не проси сразу “реализовать всё”.

---

## Рекомендуемый формат задач для агента

Нормальный prompt должен содержать:
- точный milestone,
- что входит в scope,
- что НЕ входит,
- требование не трогать unrelated files,
- список deliverables:
  1. changed files
  2. commands to run
  3. expected test output
  4. next step

---

## Статус проекта

Проект развивается пакетно:
- OOS v1 core
- PDL v3
- затем интеграция и trial use на реальных сигналах

Сначала доказываем полезность на узком, управляемом контуре.
Потом уже думаем про v2, richer routing, feedback loops и остальную дорогую роскошь.

---

## Для разработчика / агента

Перед началом работы:
1. прочитай `AGENTS.md`
2. прочитай релевантные документы в `docs/`
3. не придумывай новую архитектуру без явного запроса
4. реализуй только один небольшой scope за раз

