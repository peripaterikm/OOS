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

### 1. Создать виртуальное окружение

PowerShell, из корня проекта:

```powershell
.\scripts\bootstrap.ps1
```

Если PowerShell ругается на policy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\bootstrap.ps1
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
.\scripts\verify.ps1
```

By default, `scripts\verify.ps1` runs the dry run against a clean temporary project root so existing local `artifacts/` state cannot mask workflow regressions.

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
