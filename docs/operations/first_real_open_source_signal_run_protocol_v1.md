# First Real Open-Source Signal Run Protocol v1

## Purpose

Execute the first controlled real open-source signal run after Roadmap v2.4 using only existing Source Intelligence and founder-package capabilities.

## Scope

- Run a bounded live collection pass against existing open-source sources.
- Prefer Hacker News Algolia and GitHub Issues because both collectors already exist and are explicitly gated by `--allow-live-network`.
- Process collected evidence through the existing weekly discovery pipeline.
- Generate founder-review artifacts for a small batch.
- Record quality, warnings, and repeatability notes.

## Out Of Scope

- No new collectors.
- No source-code feature implementation.
- No Reddit, Facebook, LinkedIn, scraping-heavy sources, or paid APIs.
- No live LLM/API calls.
- No provider calls through `provider.complete()`.
- No dependency changes.
- No push, PR, merge, tag, or release.

## Preconditions

- Repository is checked out locally on the active working branch.
- Native Windows PowerShell is available.
- The project virtual environment exists at `.venv`.
- `PYTHONPATH` is set to `src` for CLI and tests so local source is used.
- Live source access is allowed only for the explicit bounded run command.
- Unit tests and validation commands must remain fixture/local-only and must not perform live network calls.

## Source Selection

- `hacker_news_algolia`: existing Phase B collector, bounded by query and result caps.
- `github_issues`: existing Phase B collector, bounded by query and result caps.
- Stack Exchange was not included because HN and GitHub were sufficient for the first low-volume pass.
- RSS was not included because the run intentionally avoided expanding source surface beyond the two proven collectors.

## Exact Windows PowerShell Commands Used

```powershell
cd C:\MARK\My_projects\OOS

git branch --show-current
git log --oneline -12
git status --short --untracked-files=no

$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m oos.cli run-discovery-weekly `
  --project-root . `
  --topic ai_cfo_smb `
  --run-id first_real_open_source_signal_run_v1 `
  --use-collectors `
  --allow-live-network `
  --source-type hacker_news_algolia `
  --source-type github_issues `
  --max-total-queries 4 `
  --max-queries-per-source 2 `
  --max-results-per-query 5

$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\oos-validate.ps1

git diff --check
git status --short --untracked-files=no
```

## Limits

- Run id: `first_real_open_source_signal_run_v1`.
- Topic id: `ai_cfo_smb`.
- Source types: `hacker_news_algolia`, `github_issues`.
- Total scheduled live queries: `4`.
- Maximum queries per source: `2`.
- Maximum results per query: `5`.
- Expected maximum collected evidence: `20` raw evidence items.

## Output Artifacts

Runtime artifacts are written under:

```text
artifacts/discovery_runs/first_real_open_source_signal_run_v1/
```

Expected artifacts:

- `raw_evidence_index.json`
- `cleaned_evidence.json`
- `evidence_classifications.json`
- `candidate_signals.json`
- `price_signals.json`
- `weak_pattern_candidates.json`
- `kill_archive_warnings.json`
- `founder_discovery_package.json`
- `founder_discovery_package.md`
- `discovery_run_summary.json`
- `discovery_run_summary.md`

Runtime artifacts remain outside tracked source control.

## Manual Founder Review Checklist

- Confirm source traceability for each top candidate via `source_url` and `evidence_id`.
- Review the top 10 candidate signals for real finance/SMB pain.
- Mark marketing, generated, install, tutorial, or vendor-promo items as weak/noise candidates for future tuning.
- Inspect `needs_human_review` items before any opportunity framing.
- Treat price hints as evidence-only; do not infer budgets from vague text.
- Check weak pattern and kill archive sections for clear empty states or actionable warnings.
- Use the founder package as review input, not as an automated promotion decision.

## Success Criteria

- HN and GitHub live collectors complete without collection errors.
- Raw evidence is collected from both sources.
- Candidate signals are generated with evidence traceability.
- Founder package artifacts are generated.
- Top candidates include at least 2-3 plausible real finance/SMB pains.
- Marketing/generated/install/tutorial false positives do not dominate founder review.
- Ambiguous cases are surfaced with `needs_human_review` when appropriate.
- Unit tests and validation pass after the run without live network calls.
- `git diff --check` passes.
- Runtime artifacts leave no tracked git changes.

## Failure Or Warning Criteria

- Any source failure must be recorded as a warning or blocker; do not fake success.
- Zero collected evidence is a failed live-source outcome unless caused by an explicitly recorded source outage/block.
- If marketing/generated/install/tutorial content dominates top candidates, source/query quality should be tuned before scaling volume.
- If founder package artifacts are missing, record the failure path and do not treat the run as review-ready.
- If validation fails, do not call the run operationally complete until the failure is resolved or documented.

## Safety Notes

- Live internet/API calls are limited to the explicit bounded discovery command.
- The command requires both `--use-collectors` and `--allow-live-network`.
- No LLM provider is configured or called.
- Unit tests must not use live collectors.
- Runtime artifacts are generated under `artifacts/` and are not committed.

## How To Repeat The Run

1. Pick a new deterministic run id, for example `first_real_open_source_signal_run_v1_repeat_YYYYMMDD`.
2. Reuse the same command and limits unless intentionally testing a bounded source/query change.
3. Compare `discovery_run_summary.md` and `founder_discovery_package.md` against the previous run.
4. Record source counts, top candidates, false-positive profile, and founder-review recommendation in a new run report.
