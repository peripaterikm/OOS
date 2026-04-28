# OOS Source Intelligence: сбор, классификация, анализ и ранжирование сигналов

**Версия:** v0.5 for Claude review  
**Проект:** OOS — Opportunity Operating System  
**Фокус:** автономная добыча рыночных сигналов из открытых источников, превращение сырья в candidate signals и дальнейший анализ через deterministic layer + optional LLM review.  
**Первый topic:** `ai_cfo_smb` — боли малого и среднего бизнеса вокруг cash flow, accounting, reporting, invoicing, budgeting, forecasting, spreadsheets, reconciliation, payables/receivables.

---

## 0. Что изменено после Claude review v0.3

Claude подтвердил, что изменения v0.3 имплементированы корректно и что архитектура созрела от “фильтра мусора” к активной разведывательной системе. Красных проблем не осталось. В v0.4 исправлены два технических момента и добавлены новые архитектурные улучшения с impact на качество поиска:

1. **Исправлен двойной счёт relevance при отключённых embeddings.** Теперь есть две явные формулы scoring: `embeddings_enabled` и `embeddings_disabled`. При disabled-режиме `semantic_relevance_score` не подменяется keyword score и не считается дважды.
2. **LLM budget разнесён по ролям.** Signal Review, Query Generator, Query Refinement Advisor и Cluster Synthesis получают отдельные лимиты, чтобы не конкурировать за один общий `max_llm_calls_per_run`.
3. **Добавлен `job_postings` source_type** как Phase C источник: вакансии как сигналы ручных workaround и confirmed willingness-to-pay.
4. **Добавлен Kill Archive → scoring feedback.** Сигналы/кластеры, похожие на ранее убитые возможности, получают `kill_pattern_flag` и penalty, но не auto-kill.
5. **Добавлен Weak Signal Aggregation Protocol.** Кластер слабых сигналов из нескольких источников может стать `weak_pattern_candidate`.
6. **Добавлен Founder Interview mode** как first-party evidence input: `source_type=founder_interview`, `collection_method=founder_interview`, `access_policy=private_first_party`.
7. **Добавлен Cross-topic resonance** для будущего multi-topic режима: сигналы, подтверждённые несколькими topic profiles, получают `topic_resonance_score`.
8. **Обновлены implementation phases и acceptance criteria**: job postings, founder interviews, kill feedback и weak aggregation получили места в roadmap.
9. **Уточнены OpenAI references.** В документе используется canonical `platform.openai.com` URL, даже если он редиректит на новую docs-платформу.

---

## 0.1. Что добавлено после Claude review v0.4

Claude подтвердил, что v0.4 закрывает предыдущие технические замечания: scoring больше не даёт двойной счёт, бюджеты LLM разнесены по ролям, `job_postings` и Kill Archive feedback встроены корректно. Единственное техническое замечание — сбой нумерации в Section 12 — исправлено в этой версии.

Главное новое предложение Claude: OOS должен стать не просто фильтром публичных жалоб, а активной разведывательной системой, которая:

```text
- отслеживает динамику боли во времени;
- ищет невысказанное операционное бремя;
- генерирует запросы языком клиента;
- извлекает price / budget signals;
- превращает opportunity в первый experiment blueprint;
- периодически ищет negative space — боли без очевидных решений;
- синтезирует persona из накопленного корпуса.
```

В v0.5 добавлены:

1. **Выводы и приоритезация по Claude creative ideas.** Добавлена отдельная секция `23. Claude creative ideas: выводы, приоритеты и реализация`.
2. **Customer Voice Queries** как самый быстрый и сильный next layer после relevance hardening.
3. **Implied Burden Detection** как новый высокоценный signal type для поиска боли без слов “problem/pain”.
4. **ExperimentBlueprint** как практический выход из opportunity framing: как проверить идею за 7–14 дней без разработки.
5. **Price Signal Extraction** как мост от боли к бюджету и willingness-to-pay.
6. **Temporal Pain Tracking** как более поздняя архитектурная фаза: перейти от снимков рынка к динамике боли.
7. **Negative Space Analysis** и **Persona Synthesis** как periodic corpus-level LLM synthesis после накопления качественного корпуса.
8. **Рекомендованный порядок реализации**, учитывающий эффект, стоимость, токены и текущую зрелость системы.
9. **Исправлена нумерация Section 12**: `12.4 Founder interview` переименован в `12.2 Founder interview`.

---

## 1. Executive summary

OOS должен работать как разведывательная система для поиска бизнес-возможностей:

```text
Internet sources
→ RawEvidence
→ cleaning / normalization / privacy redaction
→ deterministic classification
→ CandidateSignal extraction
→ relevance / quality scoring
→ optional LLM Signal Review
→ founder-readable package
→ meaning-loop / opportunity framing
```

Ключевая идея: **не позволять LLM быть первым и единственным фильтром истины**, но и не ограничивать LLM ролью пассивного “судьи одного сигнала”.

В v0.3 LLM получает четыре более ценные роли:

```text
1. Query Generator — расширяет пространство поиска.
2. Query Refinement Advisor — улучшает запросы на основе yield metrics.
3. Cluster Synthesis — формулирует emerging pain patterns.
4. Structured JTBD / why-now extractor — готовит сырьё для opportunity framing.
```

Сначала система собирает и нормализует evidence, сохраняет traceability до `source_url`, применяет дешёвые deterministic filters, а уже потом — опционально — отдаёт компактные карточки в LLM для смысловой оценки.

Такой подход нужен, чтобы:

- не тратить токены на мусор;
- не давать LLM галлюцинировать “инсайты” без источников;
- сохранять воспроизводимость и аудит;
- оставлять founder-а финальным decision-maker;
- иметь дешёвый baseline, который работает даже без API.

---

## 2. Что показали первые live-запуски

Технически live collection уже доказал работоспособность:

- HN live run: `live_collectors`, `live_network_enabled=True`, 2 scheduled queries, 3 raw evidence, 3 candidate signals.
- GitHub live run: 8 raw evidence, 8 candidate signals.
- Mixed run: 9 raw evidence, 9 candidate signals.
- Meaning loop dry run: `adapter_only`, traceability сохраняется.

Но качество пока сырое:

- HN тянет generic small-business / corporations discussions.
- GitHub Issues тянет маркетинговые тексты, LinkedIn content calendars, product pitches.
- RSS пытается читать search query как URL.
- В summaries есть HTML artifacts: `doesn&#x27;t`, `<p>`.
- В GitHub summaries есть mojibake: `рџљЂ`, `вЂ”`, `рџ“‹`.
- Скоринг слишком плоский: почти всё получает `0.73`.

Вывод: **collector layer работает, но relevance/filtering/scoring нужно усиливать до подключения LLM**.

---

## 3. Принципы архитектуры

### 3.1. Evidence-first, not idea-first

Система не должна начинать с генерации идей. Она должна начинать с evidence:

```text
Кто-то жалуется
Кто-то ищет инструмент
Кто-то описывает workaround
Кто-то сравнивает альтернативы
Кто-то сталкивается с регуляторным/техническим изменением
```

И только потом:

```text
evidence → signal → opportunity → idea / hypothesis / experiment
```

### 3.2. Traceability always

Каждый downstream artifact должен позволять вернуться назад:

```text
CandidateSignal
→ EvidenceClassification
→ CleanedEvidence
→ RawEvidence
→ source_url
```

Минимально сохраняемые поля:

- `evidence_id`
- `source_id`
- `source_type`
- `source_url`
- `topic_id`
- `query_kind`
- `collection_method`
- `content_hash`

### 3.3. Founder remains final decision-maker

LLM и deterministic scoring дают advisory output. Они не принимают финальные решения.

Founder review должен иметь действия:

```text
advance / park / kill / needs_more_evidence / create_experiment
```

### 3.4. Privacy by default

По умолчанию не храним:

- usernames;
- handles;
- GitHub logins;
- Stack Exchange display names / user IDs;
- RSS author identity;
- bulk dumps комментариев.

Храним роль/контекст:

```text
unverified public issue reporter
unverified public commenter
developer
SMB owner
public feed item
official/regulatory feed item
```

### 3.5. Live network is explicit

По умолчанию система работает offline / fixture mode.

Live mode требует явных флагов:

```powershell
--use-collectors
--allow-live-network
--max-total-queries 4
--max-results-per-query 5
```

---

## 4. Источники сигналов

### 4.1. Hacker News / HN Algolia

**Тип сигнала:** founder/workflow pain, Ask HN questions, tool alternatives, complaints, founder discussions.  
**API:** HN Algolia Search API.  
**Reference:** https://hn.algolia.com/api

Плюсы:

- простой публичный API;
- хорошо для founder/workflow pain;
- много обсуждений инструментов;
- полезен для early adopter / dev-adjacent рынков.

Минусы:

- шумный;
- много generic debates;
- query quality критична;
- комментарии часто не содержат buying intent;
- нужны HTML/entity cleanup и relevance gate.

Для `ai_cfo_smb` HN нельзя спрашивать просто `small business`. Нужны finance-specific queries:

```text
"cash flow" "small business"
"bookkeeping" "small business"
"accounting software" "small business"
"spreadsheet" "cash flow"
"invoice" "small business"
"financial reporting" "small business"
"cash flow forecasting"
"SMB accounting"
"QuickBooks" "manual"
"Xero" "spreadsheet"
```

### 4.2. GitHub Issues

**Тип сигнала:** bugs, adoption blockers, feature requests, integration pain, workflow pain, workaround descriptions.  
**API:** GitHub REST API / Search Issues / Issues endpoints.  
**References:**

- https://docs.github.com/en/rest
- https://docs.github.com/rest/issues/issues

Важно: GitHub Issues endpoints могут возвращать pull requests; PR-shaped items нужно фильтровать по `pull_request` key.

Плюсы:

- конкретные проблемы пользователей;
- часто есть workaround;
- полезно для devtools/SaaS/B2B;
- хорошо сохраняется `source_url`.

Минусы:

- search может тащить autogenerated issues;
- много marketing/product planning content;
- много repo-internal task dumps;
- без relevance gate легко принять content calendar за pain.

Для `ai_cfo_smb` лучше искать:

```text
"cash flow" "manual spreadsheet"
"invoice payment" "spreadsheet"
"bookkeeping" "small business"
"accounting software" "manual"
"QuickBooks" "cash flow"
"Xero" "invoice"
"financial reporting" "small business"
"reconciliation" "spreadsheet"
"accounts payable" "small business"
"accounts receivable" "invoice"
```

### 4.3. Stack Exchange / Stack Overflow

**Тип сигнала:** technical adoption blockers, unanswered questions, integration problems.  
**API:** Stack Exchange API v2.3.  
**References:**

- https://api.stackexchange.com/docs
- https://stackapps.com/help/api-authentication

Stack Exchange API поддерживает registered app key / OAuth для повышенной квоты. Без ключа лимиты ниже; app key нужен для production/high-volume use.

Плюсы:

- хорошо для технических барьеров;
- структурированные вопросы;
- tags / answer_count / is_answered помогают scoring.

Минусы:

- может быть мало сигналов для не-dev тем;
- для `ai_cfo_smb` нужен правильный site strategy;
- Stack Overflow может быть не лучшим источником для SMB finance pain.

### 4.4. RSS / regulator / changelog feeds

**Тип сигнала:** regulatory triggers, product changelog changes, API changes, official announcements.  
**Format:** RSS 2.0 / Atom where supported.  
**References:**

- https://www.rssboard.org/rss-specification
- https://validator.w3.org/feed/docs/rss2.html

Плюсы:

- устойчивый источник изменений;
- хорошо для regulatory / compliance triggers;
- мало юридических рисков по сравнению со scraping.

Минусы:

- RSS collector должен получать feed URL, а не search query;
- нужны curated feeds;
- без curated feed registry будет 0 результатов или ошибки.

Правило:

```text
RSS collector fetches only valid feed URLs.
If no feed_url exists → skip with reason rss_feed_url_missing.
Never fetch arbitrary search text as URL.
```

### 4.5. Job postings

**Тип сигнала:** manual workaround, hiring-as-workaround, operational pain, budget-confirmed demand.  
**Source type:** `job_postings`.  
**Phase:** Phase C, after live relevance hardening and before Reddit.

Вакансии конкурентов и потенциальных клиентов — это недооценённый источник сигналов. Если компания нанимает человека для ручной сверки счетов, подготовки management reporting в Excel или monthly close, это означает:

```text
company has pain
→ existing tool/process failed or absent
→ company is already paying for a workaround
→ willingness-to-pay is partially confirmed
```

Query kind:

```yaml
manual_workaround_job:
  examples:
    - "financial analyst" "Excel" "management reporting"
    - "accounts payable" "manual reconciliation"
    - "bookkeeper" "QuickBooks" "spreadsheets"
    - "cash flow forecasting" "Excel"
    - "month-end close" "manual"
```

RawEvidence mapping:

```yaml
source_type: job_postings
collection_method: public_job_feed
access_policy: public_listing
author_or_context: hiring_company_context_only
```

Privacy policy:

- store role/company context, not recruiter personal names;
- no candidate data;
- no scraping behind login;
- prefer RSS/API/public feeds;
- do not treat individual employees as targets.

Scoring impact:

- job posting can increase `workaround_score` and `source_quality_score`;
- job posting alone is not proof of product demand;
- strongest when it includes manual process language + finance anchors + repeated pattern across employers.

Acceptance criteria:

```text
- vacancy describing manual finance process can become manual_workaround_job signal;
- generic finance job without manual workaround does not become high-confidence opportunity;
- source yield analytics excludes private founder interviews but includes job_postings as public source.
```

### 4.6. Missing / future SMB finance sources

Добавить позже, после quality hardening:

- **Indie Hackers** — founder pain + willingness-to-pay.
- **Product Hunt comments** к финансовым SaaS-запускам — alternatives / missing feature / adoption objections.
- **QuickBooks / Xero changelogs** — что они фиксируют = что болит у клиентов.
- **Публичные Telegram-каналы** для русскоязычного SMB-сегмента — только через официально допустимый API/экспорт и privacy policy.

### 4.7. Reddit

Текущий статус: **policy approved, collector not implemented**.

Правила:

- enabled by default only after collector exists;
- no usernames;
- no bulk dumps;
- no third-party redistribution;
- no model training;
- review before external productization.

Reddit лучше подключать не раньше Phase 3, после relevance gate + LLM judge. Иначе он даст 10× больше шума, чем HN/GitHub.

Acceptance criteria before Reddit:

```text
For two consecutive real bounded runs on HN/GitHub:
- top-3 signals contain at least 2 clearly relevant finance pain signals;
- top-3 contains 0 obvious marketing/generated-content false positives;
- obvious noise rate in top-10 < 30%;
- HTML/mojibake absent from summaries;
- source_url/evidence_id traceability complete;
- founder manually confirms at least 50% of top-10 as advance/review, not kill.
```

### 4.8. G2 / Capterra / Trustpilot

Ценный источник competitor weakness / reviews, но:

- G2 Data API обычно enterprise-priced и не реалистичен для solo founder MVP;
- Trustpilot API/access/terms require review;
- scraping review pages без Terms review не делать.

Пока: defer.

---

## 5. Data model

### 5.1. RawEvidence

RawEvidence — минимальная единица доказательства.

```yaml
evidence_id: deterministic id
source_id: hacker_news_algolia | github_issues | stack_exchange | rss_feeds
source_type: hacker_news_algolia | github_issues | stack_exchange | rss_feed
source_name: human-readable source
source_url: exact URL
collected_at: timestamp
language: unknown/en/...
topic_id: ai_cfo_smb
query_kind: pain_query | workaround_query | buying_intent_query | competitor_weakness_query | trend_trigger_query
title: raw title
body: raw body
content_hash: hash over normalized title/body
raw_metadata: safe metadata only
author_or_context: role/context, not username
access_policy: public_api / public_feed / etc.
collection_method: fixture | live_api | rss_feed
```

### 5.2. CleanedEvidence

Purpose: clean text without destroying context.

Allowed MVP cleanup:

- whitespace normalization;
- `html.unescape`;
- simple HTML tag stripping;
- basic markdown softening for summaries;
- explicit UTF-8 decode in live collectors;
- normalized content hash.

Not allowed at this stage:

- aggressive boilerplate removal;
- summarization by LLM;
- deleting source context;
- removing URLs from `source_url`.

### 5.3. PrivacyRedactedEvidenceForLLM

Before LLM calls, create a separate redacted excerpt, not the full CleanedEvidence body.

Redact at minimum:

```text
emails → [REDACTED_EMAIL]
phone numbers → [REDACTED_PHONE]
@handles / u/handles / usernames where detectable → [REDACTED_HANDLE]
obvious personal names only if strongly detected and not essential → [REDACTED_NAME]
```

Store:

```yaml
redacted_excerpt
pii_redaction_applied: true|false
pii_redaction_notes
max_chars
```

Do not send unbounded comments or raw issue dumps to external LLM APIs.

### 5.4. EvidenceClassification

Classification values:

```text
pain_signal_candidate
workaround_signal_candidate
buying_intent_candidate
competitor_weakness_candidate
trend_trigger_candidate
needs_human_review
noise
```

Fields:

```yaml
evidence_id
classification
confidence
matched_rules
reason
requires_human_review
is_noise
relevance_flags
quality_flags
```

### 5.5. CandidateSignal

CandidateSignal — уже не сырьё, а возможный рыночный сигнал.

```yaml
signal_id
evidence_id
source_id
source_type
source_url
topic_id
query_kind
signal_type
pain_summary
target_user
current_workaround
buying_intent_hint
urgency_hint
confidence
measurement_methods
extraction_mode
classification
classification_confidence
traceability
```

### 5.6. FounderInterviewEvidence extension

Founder interviews are first-party evidence, not public source yield. They should enter the same evidence pipeline but keep a different access policy.

Recommended CLI later:

```powershell
oos.cli add-signal --collection-method founder_interview --topic ai_cfo_smb
```

Structured fields:

```yaml
source_type: founder_interview
collection_method: founder_interview
access_policy: private_first_party
pain_statement: string
target_user: string
workaround: string
urgency: low | medium | high | unknown
willing_to_pay_hint: present | possible | not_detected | unknown
interview_context: role/context only, no personal names by default
```

Rules:

- founder interviews can calibrate relevance gate and scoring;
- they must not enter public source yield analytics;
- they can enter opportunity framing as high-quality first-party evidence;
- any PII must be stripped or replaced before LLM review unless explicit consent/policy exists.

### 5.7. Topic resonance extension

For future multi-topic operation, CandidateSignal should support cross-topic resonance:

```yaml
topic_resonance_score:
  resonant_topic_ids: list[string]
  resonance_count: int
  resonance_flag: bool
  method: semantic_or_cluster_match
```

Policy:

- disabled until at least two topic profiles exist;
- same `evidence_id` across topics is a strong resonance signal;
- semantically close signals across topic clusters create weaker resonance;
- resonance boosts founder review priority but does not override relevance/noise filters.


---

## 6. Cleaning strategy

### 6.1. HTML/entity cleanup

До classification/extraction:

```python
html.unescape(text)
strip_simple_html_tags(text)
normalize_whitespace(text)
```

Examples:

```text
doesn&#x27;t work<p>Manual spreadsheet
→ doesn't work Manual spreadsheet

business.<p>Most large businesses
→ business. Most large businesses
```

### 6.2. Mojibake / UTF-8

Live collectors должны читать response bytes явно как UTF-8:

```python
raw = response.read()
text = raw.decode("utf-8", errors="replace")
payload = json.loads(text)
```

Тестовые признаки ошибки:

```text
🚀 should not become рџљЂ
— should not become вЂ”
📋 should not become рџ“‹
```

### 6.3. Markdown softening

Не надо уничтожать markdown полностью, но summaries не должны начинаться с километровых заголовков.

Preferred summary extraction:

1. explicit `JTBD` block;
2. explicit `Current workaround` block;
3. first sentence with finance anchor + pain/workaround term;
4. cleaned title + first meaningful sentence;
5. truncated cleaned body.

---

## 7. Deterministic classification

### 7.1. Rule families

Pain:

```text
problem, pain, struggle, hard to, can't, doesn't work, broken, frustrating, issue, bug
```

Workaround:

```text
workaround, manual, spreadsheet, hack, we use, I built, temporary solution
```

Buying intent:

```text
looking for, recommend, alternative, would pay, need a tool, any tool, pricing
```

Competitor weakness:

```text
too expensive, missing feature, switching from, alternative to, support is bad, doesn't support
```

Trend trigger:

```text
new regulation, law changed, API changed, recently, market changed, compliance deadline
```

### 7.2. Topic relevance gate for `ai_cfo_smb`

Strong finance anchors:

```text
cash flow, cashflow, invoice, invoices, invoicing, billing, accounting, bookkeeping,
financial reporting, management reporting, budget, budgeting, forecast, forecasting,
CFO, controller, reconciliation, accounts payable, accounts receivable,
payables, receivables, payroll, expenses, runway, P&L, profit and loss,
working capital, payment cycles, payment status, due dates, bills,
QuickBooks, Xero, NetSuite
```

Weak/contextual anchors:

```text
finance, financial, reporting, spreadsheet, small business
```

Rules:

- `small business` alone is not enough.
- `spreadsheet` alone is not enough.
- `spreadsheet + finance/cash flow/invoice/budget/accounting` is strong.
- `spreadsheet + LinkedIn/social/content/campaign/calendar` is negative context and should downgrade.
- `manual spreadsheet + invoice payment cycles` is strong.

### 7.3. Anti-marketing / generated-content filter

Use both exact markers and structural patterns.

Exact / phrase markers:

```text
30-Day LinkedIn Content Calendar
Copy-Paste Ready Posts
Copy-Pasteable LinkedIn Posts
Post Topic
Post Type
Content Calendar
Product launch
Product pitch
Campaign variants
Dynamic Creative
Competitive Target
Parent Epic
Priority: P1
Effort:
Market Context & Zone Analysis
Portfolio Position
Landing page
marketing copy
creative personalization engine
```

Structural markers:

```text
many repeated day/post sections: Day 1, Day 2, Day 3...
10+ repeated templated list items
markdown-heavy campaign/template structure
headings like ## Post Type, ## Priority, ## Effort, ## Competitive Target
content dominated by launch-copy/landing-copy language
large “Executive Summary” block without user complaint/workaround
issue body structured as internal product spec rather than user pain
```

Behavior:

- strong marketing/generated markers + weak finance pain → `noise`.
- uncertain marketing-ish content → `needs_human_review`, low confidence.
- must not rank above genuine invoice/cashflow pain.

---

## 8. CandidateSignal extraction

### 8.1. From classification to signal type

```text
pain_signal_candidate → pain_signal
workaround_signal_candidate → workaround
buying_intent_candidate → buying_intent
competitor_weakness_candidate → competitor_weakness
trend_trigger_candidate → trend_trigger
needs_human_review → needs_human_review
noise → no signal by default
```

### 8.2. Summary extraction

Preferred extraction order:

1. explicit `JTBD` block;
2. explicit `Current workaround` block;
3. first sentence with finance anchor + pain/workaround term;
4. cleaned title + first meaningful sentence;
5. truncated cleaned body.

Never invent facts.

### 8.3. Target user

Rule-based default:

```text
GitHub / Stack Exchange → developer, unless text says freelancer, founder, SMB owner
RSS official/regulatory → regulated organization / market participant
HN → founder/developer/unknown depending on context
```

Avoid overclaiming.

---

## 9. Ranking and scoring

### 9.1. Why current scoring is insufficient

Observed issue: marketing text, generic HN comments, real invoice/cashflow pain all got similar confidence around `0.73`.

That makes ranking weak.

### 9.2. Normalized scoring formula

Positive factor weights must sum to `1.0`. There are **two explicit scoring modes** to avoid double-counting keyword relevance when embeddings are disabled.

#### Mode A: embeddings enabled

```yaml
weights_embeddings_enabled:
  classification_score: 0.20
  topic_keyword_relevance_score: 0.14
  semantic_relevance_score: 0.18
  pain_specificity_score: 0.14
  workaround_score: 0.10
  buying_intent_score: 0.08
  urgency_score: 0.05
  source_quality_score: 0.05
  source_cost_commitment_score: 0.03
  weak_pattern_score: 0.03
# sum = 1.00
```

Formula:

```text
positive_score =
  0.20 * classification_score
+ 0.14 * topic_keyword_relevance_score
+ 0.18 * semantic_relevance_score
+ 0.14 * pain_specificity_score
+ 0.10 * workaround_score
+ 0.08 * buying_intent_score
+ 0.05 * urgency_score
+ 0.05 * source_quality_score
+ 0.03 * source_cost_commitment_score
+ 0.03 * weak_pattern_score

adjusted_score = positive_score * signal_type_weight
               - 0.30 * anti_marketing_penalty
               - 0.20 * kill_pattern_penalty
               - 0.15 * duplicate_penalty
               - 0.10 * pii_risk_penalty

confidence = clamp(adjusted_score, 0.0, 1.0)
```

#### Mode B: embeddings disabled

When embeddings are disabled, `semantic_relevance_score` must be set to `0.0` and must not fallback to `topic_keyword_relevance_score`. The semantic weight is redistributed to other deterministic factors.

```yaml
weights_embeddings_disabled:
  classification_score: 0.24
  topic_keyword_relevance_score: 0.24
  pain_specificity_score: 0.16
  workaround_score: 0.12
  buying_intent_score: 0.08
  urgency_score: 0.05
  source_quality_score: 0.05
  source_cost_commitment_score: 0.03
  weak_pattern_score: 0.03
# sum = 1.00
```

Formula:

```text
semantic_relevance_score = 0.0

positive_score =
  0.24 * classification_score
+ 0.24 * topic_keyword_relevance_score
+ 0.16 * pain_specificity_score
+ 0.12 * workaround_score
+ 0.08 * buying_intent_score
+ 0.05 * urgency_score
+ 0.05 * source_quality_score
+ 0.03 * source_cost_commitment_score
+ 0.03 * weak_pattern_score

adjusted_score = positive_score * signal_type_weight
               - 0.30 * anti_marketing_penalty
               - 0.20 * kill_pattern_penalty
               - 0.15 * duplicate_penalty
               - 0.10 * pii_risk_penalty

confidence = clamp(adjusted_score, 0.0, 1.0)
```

Important:

- `classification_score` is only one factor, not the whole score.
- `semantic_relevance_score` is a separate dimension only when embeddings are enabled.
- `semantic_relevance_score` must never equal `topic_keyword_relevance_score` as fallback.
- Penalties are applied after positive score.
- Clamp should be rare, not the main ranking mechanism.
- Store component scores and scoring mode for audit.
- `source_cost_commitment_score` captures sources like job postings where the market is already paying for manual workaround labor.
- `weak_pattern_score` captures weak-signal aggregation at cluster level, not individual signal confidence.

### 9.2.1. Semantic relevance via local embeddings

Keyword anchors are necessary but brittle. A phrase like “our bookkeeper is leaving and I do not know how to close the month” can be a finance pain even without explicit words like `cash flow` or `invoice`.

Recommended optional layer:

```text
topic_definition → local embedding
evidence excerpt → local embedding
cosine_similarity → semantic_relevance_score
```

Implementation policy:

- local-first, no API by default;
- suggested model class: small sentence-transformer style embedding model, e.g. `all-MiniLM-L6-v2`, subject to dependency review;
- embeddings must be disabled by default until dependencies are explicitly approved;
- embeddings do not store or transmit PII externally;
- semantic score is cached by content hash;
- semantic score is auditable as one component in scoring.

Acceptance criteria:

```text
- finance pain without exact finance keywords can rise above needs_human_review if semantic relevance is high;
- generic small-business text without finance meaning remains low relevance;
- semantic_relevance_score never overrides strong anti-marketing/noise penalties.
```

### 9.3. Signal type weight, not hard priority

Do not sort by rigid priority like:

```text
buying_intent > pain_signal > workaround
```

Instead use bounded multipliers:

```yaml
signal_type_weight:
  buying_intent: 1.08
  pain_signal: 1.00
  workaround: 0.95
  competitor_weakness: 0.92
  trend_trigger: 0.90
  needs_human_review: 0.55
```

This prevents weak buying intent from outranking strong pain with explicit workaround.

### 9.4. Final ranking

Sort by:

1. `confidence` descending;
2. `topic_relevance_score` descending;
3. `source_quality_score` descending;
4. `evidence_id` or `signal_id` ascending as deterministic tie-breaker.

No hard signal-type priority.

### 9.5. Expected scoring behavior

```text
strong finance pain + workaround + explicit JTBD → 0.75–0.90
finance relevant but weak pain → 0.45–0.65
needs_human_review → 0.25–0.40
marketing/generated content → 0.0 if noise, max 0.25–0.35 if review
generic small-business text without finance anchors → max 0.30–0.40
```

### 9.6. Kill Archive feedback

OOS already has a Kill Archive. Signals that repeatedly lead to killed opportunities should not keep receiving high scores forever. Add `kill_pattern_penalty` as an advisory downgrade:

```yaml
kill_pattern_penalty:
  method: rule_based_or_embedding_similarity
  check: signal_cluster_matches_kill_archive_pattern
  threshold: 0.75
  penalty_weight: 0.20
  output_flag: kill_pattern_flag
```

Policy:

- no automatic kill;
- founder package must show: “similar opportunity was previously killed — reason: ...”;
- penalty applies at cluster/signal ranking level;
- `kill_pattern_flag=true` routes to review, not deletion.

Acceptance criteria:

```text
- signal matching Kill Archive pattern is downgraded;
- founder package cites matching kill reason;
- unrelated signals are unaffected;
- no auto-kill occurs without founder decision.
```

### 9.7. Weak Signal Aggregation Protocol

`needs_human_review` should not be a dead end. One weak signal may be noise, but repeated weak signals across sources can reveal an emerging pattern.

Cluster upgrade rule:

```yaml
cluster_upgrade_rule:
  if:
    signal_count: ">= 5"
    avg_confidence: ">= 0.30"
    source_diversity: ">= 2"
    max_confidence: "< 0.60"
  then:
    cluster_classification: weak_pattern_candidate
    review_priority: elevated
    weak_pattern_score: 0.6-0.8
```

Policy:

- weak pattern upgrade happens at cluster level, not individual evidence level;
- Cluster Synthesis LLM should prioritize these clusters;
- founder package should include a separate “Weak patterns worth review” section.

### 9.8. Job posting cost-commitment score

Job postings can indicate that a company is already paying for a workaround. Add `source_cost_commitment_score`:

```yaml
source_cost_commitment_score:
  job_posting_with_manual_workaround: 0.7-1.0
  job_posting_generic_role: 0.2-0.4
  public_discussion: 0.0-0.2
```

This score must not overpower relevance. A generic accounting job is not a product opportunity. A job describing manual invoice reconciliation or Excel-based management reporting is stronger evidence.


---

## 10. Where LLM should enter the system

### 10.1. Do not use LLM in collectors

Collectors should only fetch and map source data to RawEvidence.

Bad:

```text
collector fetches HN → asks LLM “is this useful?” → stores only LLM output
```

Good:

```text
collector fetches HN → RawEvidence with source_url → deterministic filters → optional LLM review
```

### 10.2. Proposed LLM layer: AI Signal Review Provider

LLM receives compact candidate cards, not raw unlimited dumps.

Input card:

```yaml
signal_id
evidence_id
source_type
source_url
topic_id
query_kind
cleaned_title
redacted_evidence_excerpt
classification
candidate_signal fields
deterministic scores
quality flags
pii_redaction_applied
```

LLM output:

```yaml
signal_id: string
evidence_id: string
source_url: string
evidence_cited: bool
llm_relevance_score: 0.0-1.0
llm_pain_score: 0.0-1.0
llm_buying_intent_score: 0.0-1.0
llm_workaround_score: 0.0-1.0
icp_guess: string
summary: string
red_flags: list
opportunity_hint: string
recommendation: advance | review | park | kill
confidence: 0.0-1.0
unsupported_claims: list
```

Required validation rule:

```text
If evidence_cited=false OR evidence_id/source_url mismatch → reject LLM review as invalid.
```

### 10.3. LLM system prompt with asymmetric prior

Use an explicit skeptical prior:

```text
You are an evidence-bound market signal analyst.
Your default assumption is that this signal is NOT relevant.
Only upgrade relevance if the provided evidence explicitly and unambiguously supports it.
When uncertain, output red_flags and set recommendation to review, not advance.
You must not invent facts.
Use only the provided evidence.
You must cite the provided evidence_id and source_url in the JSON output.
Return structured JSON only.
```

This protects against sycophancy and over-rationalizing weak evidence.

### 10.4. LLM modes

```yaml
llm_mode:
  disabled: default
  review_top_n: review only top N deterministic candidates
  review_uncertain: review needs_human_review / borderline items
  review_all_bounded: review all candidates within budget
```

Default remains `disabled` until provider/budget is configured.

### 10.5. Provider options

#### Option A: API provider

OpenAI / Anthropic / Google / other API.

For OpenAI:

- API reference: https://platform.openai.com/docs/api-reference
- Token counting guide: https://platform.openai.com/docs/guides/token-counting
- Pricing: https://openai.com/api/pricing/ and https://developers.openai.com/api/docs/pricing

API keys are secrets. Store them in environment variables or secret management, never in code or committed config.

#### Option B: local OpenAI-compatible provider

Ollama / LM Studio / vLLM / local gateway.

Pros:

- no per-token API bill;
- data stays local;
- useful for experiments.

Cons:

- lower quality than frontier models;
- slower;
- hardware dependent;
- more operational maintenance.

#### Option C: hybrid

- deterministic filter first;
- local model for cheap rough review;
- API model for top 10–20 signals only.

This is probably best later.

### 10.6. LLM Query Generator — expand the search space

Current manual `query_templates` create selection bias: OOS searches mostly where the founder already expects pain to be. The highest-leverage LLM use is to generate search hypotheses that surface **latent pain** — people describing a situation, not people already shopping for software.

Proposed flow:

```text
topic_profile + ICP + excluded false positives
→ LLM Query Generator
→ 20–30 candidate query hypotheses
→ deterministic filter: dedup, syntax validation, source compatibility, banned phrases
→ Query Planner chooses bounded top-N
```

Example prompt intent:

```text
Given this topic and ICP, generate search queries that would surface pain from people who do not know they need a solution yet. Avoid queries that only find vendor pages, product marketing, or people already searching for software.
```

Output schema:

```yaml
query_hypotheses:
  - query_text: string
    source_type: hacker_news_algolia | github_issues | stack_exchange | rss_feed | reddit
    query_kind: pain_query | workaround_query | buying_intent_query | competitor_weakness_query | trend_trigger_query
    latent_pain_rationale: string
    expected_false_positives: list[string]
    priority_score: 0.0-1.0
```

Policy:

- run rarely: topic onboarding or every few weeks;
- founder-approved before activation;
- deterministic filter must reject generic queries such as `small business` alone;
- cost is low: one bounded LLM call per topic refresh;
- no automatic query mutation without founder approval.

### 10.7. Query Refinement Advisor — close the query feedback loop

After each run, OOS has source/query yield metrics. LLM should not directly change the registry, but it can recommend updates.

Flow:

```text
source_yield_metrics from last 2–3 runs
+ examples of high-yield and noisy results
→ LLM Query Refinement Advisor
→ suggestions
→ founder approve/reject
```

Output schema:

```yaml
queries_to_retire:
  - query_text: string
    reason: string
queries_to_boost:
  - query_text: string
    reason: string
new_query_hypotheses:
  - query_text: string
    source_type: string
    query_kind: string
    rationale: string
risks:
  - string
```

This closes the feedback loop at the query level, not only at the source level.

### 10.8. Cluster Synthesis LLM — analyze patterns, not isolated items

A signal-by-signal LLM judge is useful but not the highest-value LLM role. Strong opportunities often emerge only when 5–10 weak signals point to the same pain pattern.

Recommended flow:

```text
CandidateSignals
→ deterministic clustering / semantic clustering
→ cluster of 5–10 related signals
→ LLM Cluster Synthesis
→ founder-facing pattern summary
```

Output schema:

```yaml
cluster_id: string
emerging_pain_pattern: string
strongest_evidence_ids: list[string]
icp_synthesis: string
opportunity_sketch: string  # max 2 sentences
why_now_signal: string | null
confidence: 0.0-1.0
red_flags: list[string]
```

Advantages:

- one LLM call per cluster, not per signal;
- model sees a pattern rather than a fragment;
- founder receives “what this cluster means,” not a pile of near-duplicates.

### 10.9. JTBD extraction as structured LLM output

Most real texts do not contain explicit JTBD blocks. LLM review should produce a structured JTBD hypothesis, with confidence and evidence citation.

Add to LLM output:

```yaml
jtbd_extracted:
  when: string | null
  want_to: string | null
  so_that: string | null
  confidence: 0.0-1.0
  evidence_cited: bool
```

Rules:

- null is better than invented JTBD;
- `evidence_cited=true` is required for any non-null field;
- low confidence JTBD goes to review, not opportunity framing.

### 10.10. Synthetic calibration signals

At topic onboarding, use one LLM call to generate calibration examples:

```text
- 10–15 examples of strong pain signals for the topic;
- 10–15 examples of false positives: marketing, generic text, content calendars, vendor copy;
- expected classifications and reasons.
```

These are **not evidence** and must never enter `RawEvidence` or opportunity history. They are used only for:

- golden tests;
- tuning deterministic weights;
- regression acceptance criteria;
- prompt calibration.

---

## 11. Cost and budget control for LLM

LLM must never be an unbounded loop. Budgets are separated by **role**, because OOS now uses LLM for more than one task. Signal Review, Query Generation, Query Refinement and Cluster Synthesis must not silently compete for one unpredictable global limit.

### 11.1. Role-specific budgets

```yaml
llm_budgets:
  query_generator:
    max_calls_per_topic_refresh: 1
    max_input_tokens: 12000
    max_output_tokens: 6000
    cadence: on_topic_profile_update_or_manual_refresh
    fail_closed: true

  synthetic_calibration:
    max_calls_per_topic_onboarding: 1
    max_input_tokens: 8000
    max_output_tokens: 6000
    cadence: on_new_topic_profile
    fail_closed: true

  signal_review:
    max_calls_per_run: 20
    max_input_tokens_per_run: 100000
    max_output_tokens_per_run: 20000
    max_candidates_reviewed: 20
    max_chars_per_candidate: 4000
    provider_timeout_seconds: 60
    fail_closed: true

  cluster_synthesis:
    max_calls_per_run: 5
    max_clusters_reviewed: 5
    max_signals_per_cluster: 10
    max_input_tokens_per_run: 80000
    max_output_tokens_per_run: 12000
    fail_closed: true

  query_refinement_advisor:
    max_calls_per_week: 1
    max_input_tokens: 30000
    max_output_tokens: 6000
    cadence: after_2_or_3_runs
    requires_founder_approval: true
    fail_closed: true

  jtbd_extraction:
    included_in: signal_review
    separate_budget: false
```

### 11.2. Global circuit breaker

```yaml
global_llm_budget_guard:
  max_total_calls_per_run: 30
  max_total_input_tokens_per_run: 220000
  max_total_output_tokens_per_run: 45000
  hard_stop_on_exceed: true
```

If any role budget or global budget is exceeded:

```text
skip remaining LLM calls for that role
record llm_budget_exhausted with role name
continue deterministic package
never block core deterministic run
```

LLM outputs should be stored separately by role:

```text
artifacts/llm_query_hypotheses/<id>.json
artifacts/llm_signal_reviews/<review_id>.json
artifacts/llm_cluster_syntheses/<cluster_id>.json
artifacts/llm_query_refinements/<run_window_id>.json
```

Do not overwrite deterministic classification.

---

## 12. Human / founder review loop

Founder package should show:

```text
Top candidates
Needs human review
Low-confidence / noise summary
Recommended next actions
Source coverage
LLM review status if enabled
```

Founder actions:

```yaml
action: advance | park | kill | request_more_evidence | create_experiment
reason: string
confidence_override: optional
notes: string
```

Founder decisions feed back into source scoring:

```text
source × topic × query_kind → yield analytics
```

Priority updates should be founder-approved, not automatic, at least in early versions.

### 12.1. Why-now / urgency window section

Trend triggers should not be treated as just another low-priority signal type. Some triggers create a temporary market window: regulatory deadline, API deprecation, competitor exit, platform shift.

Add a separate `urgency_window` object:

```yaml
urgency_window:
  detected: bool
  type: regulatory_deadline | api_change | competitor_exit | platform_shift | other
  estimated_window: string | null
  trigger_evidence_id: string | null
  reason: string
```

Weekly package should include a separate section:

```text
Time-sensitive opportunities
```

Rules:

- `urgency_window=true` does not automatically mean “advance”; it means “review separately.”
- The trigger must cite evidence.
- If the system cannot estimate a window, use `estimated_window=null` instead of inventing timing.

### 12.2. Founder interview as first-party evidence

Founder interview mode is not just manual notes. It is a structured first-party evidence source that should enter the same pipeline as public evidence, while staying private and excluded from source yield scoring.

Suggested command:

```powershell
oos.cli add-signal --collection-method founder_interview --topic ai_cfo_smb
```

Why it matters:

- early public-source runs may be sparse or noisy;
- founder interviews provide high-signal calibration examples;
- real conversations help tune relevance gate and false-positive tests;
- first-party evidence can be weighted highly in opportunity framing, but must not distort public source ROI.

Rules:

```text
Founder interview evidence:
- can feed CandidateSignal extraction;
- can feed Opportunity Framing;
- can calibrate scoring/golden tests;
- must be privacy-protected;
- must not enter public source yield analytics;
- must be labelled private_first_party.
```


---

## 13. Source yield analytics

Minimal counters:

```yaml
source_id
source_type
topic_id
query_kind
query_text
scheduled_count
raw_evidence_count
candidate_signal_count
high_confidence_signal_count
needs_human_review_count
noise_count
collection_errors
```

Later:

```yaml
founder_advanced_count
founder_killed_count
opportunity_created_count
experiment_created_count
source_roi_score
suggested_priority_updates
```

This lets the system learn:

```text
HN gives many weak discussions
GitHub gives fewer but more actionable JTBDs
RSS gives regulatory triggers once feed URLs are configured
Stack Exchange may need different topic/site strategy
```

### 13.4. Query feedback from Kill Archive

Source yield should not only measure what produces attractive signals. It should also learn from signals that led to killed opportunities.

```yaml
kill_feedback_metrics:
  query_to_killed_opportunity_count
  source_to_killed_opportunity_count
  recurring_kill_reason_by_query
  recurring_kill_reason_by_source
```

Use:

- lower priority for queries repeatedly leading to killed patterns;
- show warning in Query Refinement Advisor;
- never auto-delete queries without founder approval.

### 13.5. Weak signal source diversity

Track clusters where weak signals repeat across sources:

```yaml
weak_signal_cluster_metrics:
  signal_count
  source_diversity
  avg_confidence
  max_confidence
  elevated_to_weak_pattern_candidate
```

This helps detect hidden patterns that no single evidence item proves.


---

## 14. Proposed end-to-end run modes

### 14.1. Fixture smoke

```powershell
.\.venv\Scripts\python.exe -m oos.cli run-discovery-weekly `
  --topic ai_cfo_smb `
  --project-root . `
  --run-id mvp_smoke_001 `
  --include-meaning-loop-dry-run
```

### 14.2. Live HN smoke

```powershell
.\.venv\Scripts\python.exe -m oos.cli run-discovery-weekly `
  --topic ai_cfo_smb `
  --project-root . `
  --run-id live_hn_002 `
  --use-collectors `
  --allow-live-network `
  --source-type hacker_news_algolia `
  --max-total-queries 2 `
  --max-queries-per-source 2 `
  --max-results-per-query 3 `
  --include-meaning-loop-dry-run
```

### 14.3. Live GitHub smoke

```powershell
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

### 14.4. Mixed bounded run

```powershell
.\.venv\Scripts\python.exe -m oos.cli run-discovery-weekly `
  --topic ai_cfo_smb `
  --project-root . `
  --run-id live_mix_002 `
  --use-collectors `
  --allow-live-network `
  --max-total-queries 6 `
  --max-queries-per-source 2 `
  --max-results-per-query 3 `
  --include-meaning-loop-dry-run
```

---

## 15. Acceptance criteria for useful signal quality

A run is technically successful if:

```text
collection_mode = live_collectors
live_network_enabled = True
scheduled_query_count > 0
raw_evidence_count > 0
artifacts created
meaning_loop_dry_run created
```

A run is product-useful if:

```text
candidate_signal_count > 0
at least one top signal is clearly relevant to ai_cfo_smb
marketing/generated content is not ranked high
HTML/mojibake is absent from summaries
top signals preserve source_url
confidence is not flat across all candidates
```

For `ai_cfo_smb`, good signal examples:

```text
manual spreadsheet workaround for invoice payment timing
cash flow reporting is hard to keep current
bookkeeping/accounting workflow creates repeated manual work
small business wants tool for cash forecasting
reconciliation creates delays or errors
QuickBooks/Xero export/reporting limitation causes workaround
```

Bad signal examples:

```text
LinkedIn content calendar
product launch pitch
generic large corporation debate
MCP link dump
generic “cool job” comment
creative personalization campaign task
```

Live quality hardening acceptance:

```text
live_github_002:
- invoice/cashflow/manual-spreadsheet signal remains top-ranked;
- LinkedIn content calendar and Dynamic Creative issues are noise or low-confidence review;
- mojibake absent;
- confidence distribution has at least 3 distinct values in mixed fixture/live test.

live_hn_002:
- no raw HTML entities/tags in top summaries;
- generic small-business/corporation debates are not high-confidence pain_signal;
- at least one finance-specific query is used.

live_rss_002:
- RSS search-text query is skipped, not fetched;
- no `unknown url type` exception-like error;
- valid feed URL still works via mocked test.
```

---

## 16. Strong sides of this approach

### 16.1. Traceable and auditable

Every signal links back to `source_url`. This prevents “AI invented a market pain” syndrome.

### 16.2. Cheap baseline

Deterministic layer runs without tokens and can process large amounts of evidence cheaply.

### 16.3. LLM cost control

LLM is only applied after filtering and only to bounded candidate cards.

### 16.4. Safety and compliance

No usernames, no bulk dumps, no training, explicit live-network flags.

### 16.5. Works incrementally

Each source can be improved independently:

```text
HN query quality
GitHub issue filtering
RSS feed registry
Stack Exchange site strategy
Reddit collector later
```

### 16.6. Testability

Fixture-first collectors and deterministic classifiers allow stable unit tests.

---

## 17. Weak sides and risks

### 17.1. Rule-based logic is brittle

Rules can miss subtle pain or over-detect keywords.

Example: `spreadsheet` can mean real finance workaround or just marketing copy.

### 17.2. Query quality dominates results

Bad queries produce bad evidence. This is not an LLM problem, it is source intelligence design.

### 17.3. Source bias

HN and GitHub overrepresent technical/developer audiences. SMB owners may be better represented in Reddit, reviews, forums, Telegram, newsletters, Indie Hackers, Product Hunt, etc.

### 17.4. LLM can over-rationalize weak evidence

If given weak evidence, LLM may write a convincing but unsupported opportunity hypothesis.

Mitigation:

```text
asymmetric prior
red_flags required
recommendation=review when uncertain
evidence_cited=true required
founder review remains mandatory
```

### 17.5. API cost and secrets

API use requires:

- API key management;
- token budgeting;
- rate limit handling;
- cost monitoring;
- provider fallback.

### 17.6. PII leakage to LLM provider

Even if usernames are not stored, `cleaned_evidence_excerpt` can contain emails, phone numbers, or personal names.

Mitigation:

```text
PII-strip before prompt
bounded excerpt
no raw comment dumps
LLM review artifact stores redaction status
```

### 17.7. Legal / ToS risk for some sources

Use official APIs and feeds where possible. Avoid scraping without explicit policy review.

---

## 18. Recommended implementation phases

### Phase 1 — deterministic live-quality hardening

Implement now:

- HTML cleanup;
- UTF-8 decode fix;
- `ai_cfo_smb` relevance gate;
- anti-marketing filter;
- better HN/GitHub query templates;
- RSS URL-only handling;
- normalized scoring with explicit embeddings-enabled and embeddings-disabled modes;
- explicit component scores.

Acceptance:

```text
- no double counting when embeddings are disabled;
- top-3 live signals contain at least 2 real finance pains;
- top-3 contains 0 obvious marketing false positives;
- HTML/mojibake absent from summaries.
```

### Phase 2 — founder interview mode + synthetic calibration

Add first-party evidence input and calibration examples.

Deliverables:

- `collection_method=founder_interview`;
- private first-party RawEvidence mapping;
- structured pain/workaround/urgency/willingness-to-pay fields;
- synthetic positive/false-positive calibration examples;
- golden tests based on calibration examples.

Acceptance:

```text
- founder interview can create private RawEvidence and CandidateSignal;
- private evidence does not enter public source yield analytics;
- calibration examples generate tests, not market evidence.
```

### Phase 3 — LLM Query Generator

High priority after deterministic hardening.

Deliverables:

- topic profile → LLM query hypotheses;
- deterministic query filter;
- founder approval workflow for new queries.

Acceptance:

```text
- generated query set contains latent-pain queries, not only software-shopping queries;
- generic queries are rejected by deterministic filter;
- founder can approve/reject query hypotheses before activation;
- role-specific LLM budget is enforced.
```

### Phase 4 — local semantic relevance embeddings

Add optional local embeddings for semantic relevance.

Deliverables:

- dependency review for local embedding package/model;
- embedding cache by content hash;
- scoring mode switch: embeddings_enabled vs embeddings_disabled;
- semantic_relevance_score in component scores only when enabled.

Acceptance:

```text
- finance pain without exact keywords can be recovered;
- keywords are not double-counted when embeddings are disabled;
- semantic relevance never overrides anti-marketing/noise penalties.
```

### Phase 5 — job postings source

Add `job_postings` as a public source for manual workaround / hiring-as-workaround signals.

Deliverables:

- source_type `job_postings`;
- query_kind `manual_workaround_job`;
- job posting RawEvidence mapping;
- cost-commitment component in scoring.

Acceptance:

```text
- manual finance workaround job can produce relevant signal;
- generic finance job does not become high-confidence opportunity;
- no recruiter/candidate PII is stored.
```

### Phase 6 — source yield analytics + Query Refinement Advisor

Track which sources/queries produce useful signals, then let LLM propose query changes.

Rules:

- LLM suggests; founder approves;
- no automatic query mutation;
- preserve audit trail for retired/boosted/new queries;
- role-specific budget is enforced.

### Phase 7 — weak signal aggregation + cluster synthesis

Add cluster-level upgrade protocol and LLM cluster synthesis.

Deliverables:

- weak pattern candidate rule;
- cluster synthesis schema;
- weekly package section for weak patterns worth review;
- `urgency_window` object and time-sensitive section.

Acceptance:

```text
- 5+ weak signals from 2+ sources can elevate a cluster;
- one weak signal alone remains low priority;
- LLM cluster synthesis cites strongest evidence_ids.
```

### Phase 8 — Kill Archive feedback

Connect prior failed ideas to scoring and review routing.

Deliverables:

- `kill_pattern_penalty`;
- `kill_pattern_flag`;
- founder package warning with kill reason;
- Query Refinement Advisor includes recurring kill patterns.

Acceptance:

```text
- similar-to-killed cluster is downgraded and flagged;
- no auto-kill occurs;
- founder sees the prior kill reason.
```

### Phase 9 — Cross-topic resonance

Only after at least two topic profiles exist.

Deliverables:

- `topic_resonance_score`;
- resonant topic IDs;
- founder package section for cross-topic opportunities.

### Phase 10 — Reddit / review sites / niche sources

Only after acceptance criteria from Section 4.7 are met:

```text
- two consecutive real runs with noise_rate < 30%;
- top-3 contains at least 2 true finance pain signals;
- top-3 contains 0 obvious marketing false positives;
- HTML/mojibake cleanup passes;
- founder approves relevance gate quality.
```

---

## 19. Proposed LLM prompt shape

### System

```text
You are an evidence-bound market signal analyst.
Your default assumption is that this signal is NOT relevant.
Only upgrade relevance if the provided evidence explicitly and unambiguously supports it.
When uncertain, output red_flags and set recommendation to review, not advance.
You must not invent facts.
Use only the provided evidence.
You must cite the provided evidence_id and source_url in the JSON output.
Return structured JSON only.
```

### Input

```json
{
  "topic_id": "ai_cfo_smb",
  "candidate_signal": {
    "signal_id": "...",
    "evidence_id": "...",
    "source_type": "github_issues",
    "source_url": "...",
    "pain_summary": "...",
    "current_workaround": "...",
    "buying_intent_hint": "...",
    "deterministic_confidence": 0.73,
    "component_scores": {
      "classification_score": 0.75,
      "topic_keyword_relevance_score": 0.85,
      "semantic_relevance_score": 0.78,
      "anti_marketing_penalty": 0.0
    },
    "urgency_window": {
      "detected": false,
      "type": null,
      "estimated_window": null
    }
  },
  "redacted_evidence_excerpt": "...",
  "pii_redaction_applied": true,
  "topic_definition": "SMB finance, cash flow, reporting, invoicing, accounting, budgeting, forecasting"
}
```

### Output

```json
{
  "signal_id": "...",
  "evidence_id": "...",
  "source_url": "...",
  "evidence_cited": true,
  "llm_relevance_score": 0.0,
  "llm_pain_score": 0.0,
  "llm_buying_intent_score": 0.0,
  "llm_workaround_score": 0.0,
  "icp_guess": "...",
  "summary": "...",
  "red_flags": ["..."],
  "opportunity_hint": "...",
  "jtbd_extracted": {
    "when": null,
    "want_to": null,
    "so_that": null,
    "confidence": 0.0,
    "evidence_cited": true
  },
  "urgency_window": {
    "detected": false,
    "type": null,
    "estimated_window": null,
    "trigger_evidence_id": null,
    "reason": ""
  },
  "recommendation": "advance|review|park|kill",
  "confidence": 0.0,
  "unsupported_claims": []
}
```

Validation rules:

```text
- evidence_cited must be true.
- evidence_id must match input.
- source_url must match input.
- unsupported_claims must be empty for advance.
- recommendation=advance requires relevance_score and pain_score above configured thresholds.
```

---

## 20. Answers to Claude v0.2 review

**Q1. Should OOS use LLM Query Generator?**  
Yes. This is now treated as the highest-leverage LLM role after deterministic quality hardening. It addresses selection bias by generating latent-pain queries beyond what the founder already knows to search for.

**Q2. Should OOS use embeddings instead of keyword relevance?**  
Use embeddings as an additional signal, not a replacement. Keyword anchors remain cheap and auditable; semantic similarity catches relevant pain phrased without the expected keywords. Local embeddings should be optional and dependency-reviewed.

**Q3. Should LLM analyze clusters rather than one signal at a time?**  
Yes. Single-signal review is useful for filtering, but cluster synthesis is more valuable for opportunity discovery. It turns repeated weak evidence into a pattern the founder can reason about.

**Q4. Should queries be refined automatically after each run?**  
No automatic changes early. Use Query Refinement Advisor to propose retire/boost/new query hypotheses. Founder approves or rejects.

**Q5. Should JTBD be extracted by LLM?**  
Yes, but with null-safe fields and confidence. The model should not invent JTBD. `evidence_cited=true` is required for non-null fields.

**Q6. Should trend/why-now signals get special treatment?**  
Yes. `urgency_window` should create a separate “Time-sensitive opportunities” section. This is not a scoring shortcut; it is a review-routing rule.

**Q7. Should synthetic calibration signals be used?**  
Yes, for tests and calibration only. They must never enter evidence store or opportunity history.

**Q8. Should Reddit move earlier?**  
No. Reddit remains later. It should be enabled only after relevance gates and quality thresholds are stable, because Reddit will multiply both signal and noise.

**Q9. What is the next measurable milestone?**  
First real run where:

```text
- top-3 contains at least 2 true finance pain signals;
- top-3 contains 0 obvious marketing false positives;
- source_url/evidence_id traceability preserved;
- summaries contain no HTML/mojibake;
- component scores are non-flat and explainable.
```
### 20.11. Claude v0.3 review incorporated in v0.4

Claude v0.3 review identified no red blockers, but added two technical fixes and five architectural improvements. v0.4 incorporates them as follows:

1. **Scoring double-count fix:** explicit `embeddings_enabled` and `embeddings_disabled` formulas. Semantic relevance is `0.0` when disabled and is not replaced by keyword relevance.
2. **Role-specific LLM budgets:** separate budgets for Query Generator, Synthetic Calibration, Signal Review, Cluster Synthesis and Query Refinement Advisor, plus global circuit breaker.
3. **Job postings source:** added `job_postings` source type and `manual_workaround_job` query kind.
4. **Kill Archive feedback:** added `kill_pattern_penalty` and `kill_pattern_flag`.
5. **Weak signal aggregation:** added cluster upgrade rule for repeated weak signals across sources.
6. **Founder interview mode:** added first-party private evidence mode.
7. **Cross-topic resonance:** added future multi-topic resonance fields.


---


## 23. Claude creative ideas: выводы, приоритеты и реализация

Claude v0.4 review предложил не просто усилить фильтры, а изменить саму природу поиска: OOS должен искать не только уже сформулированные жалобы, но и скрытое бремя, язык клиента, динамику рынка, бюджетные сигналы и первые проверочные эксперименты.

Эти идеи не равнозначны по срочности. Часть можно реализовать почти сразу и с низкими затратами. Часть требует накопленного корпуса и отдельной архитектурной фазы.

### 23.1. Общий вывод

Текущий OOS уже умеет:

```text
RawEvidence
→ CleanedEvidence
→ EvidenceClassification
→ CandidateSignal
→ Founder Discovery Package
→ Meaning-loop dry run
```

После live runs стало ясно: технический контур работает, но качество результата ограничено не collector layer, а тем, **что именно система ищет** и **как она понимает релевантность**.

Следующий качественный скачок не в добавлении ещё десяти источников, а в трёх изменениях:

```text
1. Искать языком клиента, а не языком фаундера.
2. Ловить операционное бремя, даже если человек не жалуется.
3. Превращать найденную возможность в проверяемый эксперимент.
```

### 23.2. Приоритеты: что делать сначала

| Приоритет | Идея | Эффект | Сложность | Токены | Решение |
|---|---|---:|---:|---:|---|
| P0 | Live relevance hardening | высокий | низкая/средняя | 0 | сделать первым |
| P1 | Customer Voice Queries | очень высокий | низкая | низко | сделать сразу после hardening |
| P1 | Implied Burden Detection | очень высокий | низкая/средняя | низко/средне | сделать сразу после query generator |
| P2 | ExperimentBlueprint | высокий | низкая | низко | сделать после первых хороших clusters/opportunities |
| P2 | Price Signal Extraction | высокий | средняя | средне | сделать после relevance hardening и implied burden |
| P3 | Negative Space Analysis | высокий, но позже | низкая | средне/высоко periodic | после 50+ качественных сигналов |
| P3 | Persona Synthesis | средний/высокий | низкая | средне periodic | после нескольких недель корпуса |
| P4 | Temporal Pain Tracking | очень высокий | средняя/высокая | низко | отдельная архитектурная фаза |

Практический порядок:

```text
1. Live relevance hardening
2. Customer Voice Query Generator
3. Implied Burden Detection
4. ExperimentBlueprint
5. Price Signal Extraction
6. Negative Space Analysis / Persona Synthesis
7. Temporal Pain Tracking
```

Почему именно так:

- Без relevance hardening новые источники и LLM-роли будут просто масштабировать шум.
- Customer Voice Queries резко расширяют пространство поиска почти без изменения core model.
- Implied Burden Detection ловит один из самых ценных классов B2B-боли: recurring manual effort.
- ExperimentBlueprint быстро превращает найденную боль в действие founder-а.
- Price Signal Extraction нужен для приоритизации, но требует более чистого входа.
- Temporal tracking мощен, но требует стабильной cluster identity across runs.

### 23.3. P1: Customer Voice Queries

**Проблема:** текущие query templates часто звучат как фаундер или аналитик: `cash flow forecasting`, `bookkeeping software`, `SMB accounting`. Но клиент чаще формулирует боль иначе:

```text
- “не понимаю где деньги в бизнесе”
- “как свести месяц если бухгалтер заболел”
- “excel кассовый разрыв формула”
- “клиенты платят поздно чем платить счета”
- “как понять сколько можно вывести из бизнеса”
```

**Решение:** добавить `customer_voice_mode` в LLM Query Generator.

Flow:

```text
topic_profile
→ LLM customer_voice_query_generator
→ 20–30 customer-language query hypotheses
→ deterministic validation / dedup / safety filter
→ QueryPlanner
→ source-specific search
```

Новый `query_kind`:

```yaml
query_kind: customer_voice_query
query_origin: llm_generated_customer_voice
founder_approved: true | false
```

Пример prompt:

```text
You are a frustrated small business owner who manages finances partly in spreadsheets.
You do not know that better tools exist.
Write 20 things you might type into Google, Reddit, Hacker News, Facebook, Telegram, or a forum when you hit a finance/cash-flow/accounting problem.
Do NOT use product strategist language.
Do NOT say “AI CFO”, “cash flow forecasting software”, or “management reporting platform” unless a real SMB owner would say that.
Focus on concrete situations, frustration, manual work, confusion, and urgent triggers.
Return JSON only.
```

Acceptance criteria:

```text
- generated queries contain customer-language phrases, not only expert terms;
- at least 50% of queries include concrete trigger/context;
- duplicate or near-duplicate queries are removed;
- founder can approve/reject generated queries;
- source yield is tracked separately for customer_voice_query.
```

**Почему это высоко в приоритете:** один редкий LLM-вызов может улучшить все будущие live runs. Это дешёвый рычаг против selection bias.

### 23.4. P1: Implied Burden Detection

**Проблема:** сильная B2B-боль часто не звучит как жалоба. Человек может просто описывать процесс:

```text
“Every month two people spend three days reconciling invoices manually.”
```

В тексте нет слов `problem`, `pain`, `broken`, но есть recurring human effort — а значит, есть потенциальная автоматизируемая стоимость.

Новый signal type:

```yaml
signal_type: implied_burden
```

Suggested output:

```yaml
implied_burden:
  detected: true
  process_name: string
  estimated_effort_hint: string | null
  frequency_hint: daily | weekly | monthly | quarterly | unknown
  people_involved_hint: string | null
  current_tool_or_workaround: string | null
  trigger_for_effort: string | null
  automation_potential: low | medium | high | unknown
  confidence: 0.0-1.0
  evidence_cited: bool
```

Prompt principle:

```text
Do not require complaint language.
Look for recurring human effort, manual coordination, repetitive spreadsheet work, reconciliation, reporting, chasing payments, closing month, checking invoices, preparing management reports.
Never invent hours, people, or frequency. Extract only if explicit or strongly implied.
```

Acceptance criteria:

```text
- catches recurring manual finance/admin effort even without “pain” words;
- does not invent effort estimates;
- outputs null/unknown when burden is not evidenced;
- keeps evidence_id/source_url traceability;
- runs only after deterministic relevance filtering to control token spend.
```

**Почему это перспективно:** для AI-CFO именно recurring burden часто важнее, чем эмоциональная жалоба. Если компания уже платит людьми/часами, это ближе к demand signal.

### 23.5. P2: ExperimentBlueprint

**Проблема:** даже хороший opportunity sketch оставляет founder-а с вопросом: “как проверить это быстро и без разработки?”

Решение: из cluster/opportunity генерировать структурированный `ExperimentBlueprint`.

Schema:

```yaml
experiment_blueprint:
  opportunity_id: string
  value_prop_hypothesis: string
  fake_door_description: string
  fake_door_medium: landing_page | cold_email | forum_post | direct_message | concierge_offer
  target_icp_description: string
  discovery_interview_questions:
    - string
  kill_criterion: string
  success_criterion: string
  effort_estimate: low | medium | high
  evidence_ids: list[string]
  risk_notes: list[string]
```

Generation input:

```text
cluster synthesis
+ strongest evidence_ids
+ JTBD extraction
+ price/implied burden signals if available
+ founder constraints
```

Acceptance criteria:

```text
- every blueprint cites evidence_ids;
- no build-heavy experiment is proposed as first step unless explicitly requested;
- kill/success criteria are measurable;
- output is reviewable, not auto-executed;
- founder can accept/edit/kill blueprint.
```

**Почему не P1:** ExperimentBlueprint становится ценным, когда уже есть нормальные clusters/opportunities. Сейчас важнее качество входных сигналов.

### 23.6. P2: Price Signal Extraction

**Проблема:** боль ≠ рынок. Нужен сигнал бюджета, текущих затрат или willingness-to-pay.

New object:

```yaml
price_signal:
  current_spend_hint: string | null
  effort_cost_hint: string | null
  price_complaint: string | null
  willingness_to_pay_indicator: present | possible | not_detected
  budget_owner_hint: string | null
  confidence: 0.0-1.0
  evidence_cited: bool
```

Examples:

```text
- “paying $3k/mo for fractional CFO”
- “20 hours/month maintaining spreadsheets”
- “consultant charges $150/hour”
- “tool costs $500/mo and is too expensive”
```

Where it enters scoring:

```text
CandidateSignal / Cluster
→ price_signal_extractor
→ demand_strength_score
→ opportunity prioritization
```

Acceptance criteria:

```text
- never invents prices or budgets;
- extracts only explicit or strongly implied cost signals;
- distinguishes spend, effort cost, and price complaint;
- high price signal can lift review priority even if pain language is mild.
```

**Почему это важно:** сигнал с бюджетом сильно ценнее просто “боли”. Для раннего solopreneur business это один из главных приоритетов.

### 23.7. P3: Negative Space Analysis

**Проблема:** обычный анализ показывает, какие боли существуют. Opportunity чаще живёт там, где боль есть, но решения в evidence corpus не всплывают.

Periodic LLM synthesis:

```text
Given these 50+ high-quality SMB finance signals, identify pain dimensions that appear repeatedly but for which no existing tool or workaround is cited as a satisfying solution.
Classify each as:
- unsolved_gap
- partially_solved
- well_served
Cite evidence_ids.
```

Output:

```yaml
negative_space_analysis:
  corpus_window: string
  pain_dimension: string
  solution_mentions: list[string]
  solution_adequacy: unsolved_gap | partially_solved | well_served
  strongest_evidence_ids: list[string]
  confidence: 0.0-1.0
```

Acceptance criteria:

```text
- run only after enough corpus exists, e.g. 50+ relevant signals;
- cites evidence_ids;
- separates “no solution mentioned” from “solution does not exist”; 
- founder review required before opportunity framing.
```

**Почему позже:** до накопления корпуса такой анализ будет гаданием на трёх GitHub issues и одном HN-комментарии. Гадание, конечно, древняя профессия, но нам нужна система.

### 23.8. P3: Persona Synthesis from Corpus

**Проблема:** исходный ICP может быть ошибочным. Корпус сигналов со временем может показать реальный ICP точнее, чем initial assumptions.

Periodic output:

```yaml
persona_synthesis:
  common_roles: list[string]
  common_company_contexts: list[string]
  common_trigger_events: list[string]
  common_existing_tools: list[string]
  common_failure_modes: list[string]
  estimated_company_size_range: string | null
  evidence_ids_used: list[string]
  suggested_icp_update: string | null
  confidence: 0.0-1.0
```

Acceptance criteria:

```text
- run only on high-confidence / founder-approved corpus;
- cites evidence_ids;
- never silently rewrites topic_profile;
- outputs suggested_icp_update for founder approval;
- tracks drift from original ICP.
```

### 23.9. P4: Temporal Pain Tracking

**Проблема:** run-by-run system делает снимки рынка, но не видит изменения. Сигнал, который ускоряется, важнее стабильной жалобы.

New object:

```yaml
pain_trajectory:
  cluster_id: string
  trend: emerging | accelerating | stable | decelerating | unknown
  weekly_mentions: list[int]
  weekly_avg_confidence: list[float]
  source_diversity_by_week: list[int]
  acceleration_score: 0.0-1.0
  first_seen: date
  peak_week: date | null
  maturity_stage: emerging | growing | mature | commoditized | unknown
```

Cluster Synthesis should receive temporal context:

```text
cluster signals
+ weekly trajectory
+ acceleration score
+ maturity stage
→ emerging pain pattern + timing assessment
```

Acceptance criteria:

```text
- stable cluster identity exists across runs;
- weekly aggregation is deterministic;
- acceleration is calculated before LLM synthesis;
- no opportunity is advanced solely because of acceleration;
- founder package separates “accelerating” from “high confidence but mature”.
```

**Почему это P4:** это мощно, но требует persistent cluster identity, enough history, and corpus hygiene. Делать до relevance hardening рано.

### 23.10. What not to implement yet

Не внедрять сразу:

```text
- full Temporal Pain Tracking;
- Negative Space Analysis на маленьком корпусе;
- Persona Synthesis до накопления founder-approved сигналов;
- автоматическое изменение topic_profile без founder approval;
- автоматическое выполнение экспериментов;
- Reddit auto-ingestion до устойчивого relevance gate;
- Facebook group scraping.
```

Reason:

```text
Early system should improve signal quality and query breadth first.
Corpus-level intelligence only works when corpus is not mostly noise.
```

### 23.11. Updated implementation sequence

Recommended next implementation sequence:

```text
Phase A — Quality hardening
- HTML/entity cleanup
- UTF-8/mojibake fix
- ai_cfo_smb relevance gate
- anti-marketing structural filter
- RSS URL-only behavior
- more discriminative scoring

Phase B — Query expansion
- LLM Query Generator
- customer_voice_mode
- query approval workflow
- yield tracking by query_kind

Phase C — Hidden burden layer
- implied_burden signal_type
- LLM burden extractor
- burden-aware ranking

Phase D — Action layer
- ExperimentBlueprint
- founder review/edit flow

Phase E — Demand strength layer
- Price Signal Extraction
- demand_strength_score

Phase F — Corpus synthesis
- Negative Space Analysis
- Persona Synthesis

Phase G — Market dynamics
- Temporal Pain Tracking
- acceleration_score
- maturity_stage
```

### 23.12. Final prioritization

Top 3 highest ROI near-term additions:

```text
1. Customer Voice Queries
2. Implied Burden Detection
3. ExperimentBlueprint
```

But immediate engineering order should be:

```text
1. Live relevance hardening
2. Customer Voice Queries
3. Implied Burden Detection
4. ExperimentBlueprint
```

The difference matters: `Customer Voice Queries` is the best creative idea, but it should not run on top of a classifier that still ranks LinkedIn content calendars as finance pain.


## 21. Source references

- OpenAI API reference: https://platform.openai.com/docs/api-reference
- OpenAI token counting guide: https://platform.openai.com/docs/guides/token-counting
- OpenAI API pricing: https://openai.com/api/pricing/ and https://developers.openai.com/api/docs/pricing
- GitHub REST API documentation: https://docs.github.com/en/rest
- GitHub Issues API note about pull requests appearing as issues: https://docs.github.com/rest/issues/issues
- HN Algolia API: https://hn.algolia.com/api
- Stack Exchange API v2.3: https://api.stackexchange.com/docs
- Stack Exchange API authentication / app keys: https://stackapps.com/help/api-authentication
- RSS 2.0 specification: https://www.rssboard.org/rss-specification
- W3C feed validator RSS docs: https://validator.w3.org/feed/docs/rss2.html

---

## 22. One-sentence conclusion

The recommended approach is to keep deterministic collection/cleanup/relevance/scoring as the cheap auditable backbone, then add LLM where it creates the most leverage: generating latent-pain queries, synthesizing clusters, refining queries from yield data, extracting structured JTBD, and reviewing top candidates only after evidence has been filtered, PII-redacted, and traced.
