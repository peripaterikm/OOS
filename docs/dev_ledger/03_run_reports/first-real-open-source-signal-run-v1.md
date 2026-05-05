# First Real Open-Source Signal Run v1

## Branch

- Actual branch at execution time: `feat/v2-5-roadmap-planning`
- Requested working branch in prompt: `feat/first-real-open-source-signal-run`
- Handling: continued on the actual current branch, per the workflow rule to continue on the current branch.

## Run Id

- `first_real_open_source_signal_run_v1`

## Commands Used

```powershell
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
```

The first live command attempt was blocked by local Windows socket restrictions. The same bounded command was rerun with explicit escalation for the requested live collection only.

## Sources Used

- `hacker_news_algolia`
- `github_issues`

## Limits Used

- Topic: `ai_cfo_smb`
- Maximum scheduled queries: `4`
- Maximum queries per source: `2`
- Maximum results per query: `5`
- Maximum intended raw evidence: `20`

## Artifact Paths

- Run directory: `artifacts/discovery_runs/first_real_open_source_signal_run_v1/`
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

## Counts

- Raw evidence collected: `20`
- Cleaned evidence: `20`
- Evidence classifications: `20`
- Candidate signals: `18`
- Price signals: `8`
- Weak pattern candidates: `0`
- Kill archive warnings: `0`
- Needs human review: `6`
- Noise: `2`
- Query plans generated: `20`
- Scheduled live queries: `4`
- Source counts: `github_issues: 10`, `hacker_news_algolia: 10`
- Candidate counts by source: `github_issues: 8`, `hacker_news_algolia: 10`
- Collectors succeeded: `github_issues`, `hacker_news_algolia`
- Collectors failed: none
- Collection errors: none

## Top Candidate Signal Summary

1. `hacker_news_algolia` pain signal, confidence `0.75`: unpaid invoice follow-up pain from a former small-business operator; plausible real finance/SMB pain.
2. `github_issues` pain signal, confidence `0.74`: scattered/incomplete records impair business tracking; relevant but likely vendor/marketing-adjacent.
3. `github_issues` pain signal, confidence `0.58`: YNAB balance-sheet feature request with current/historical month-end balance need; plausible real finance workflow pain.
4. `github_issues` workaround, confidence `0.58`: BUSY software promotional/accounting management copy; likely marketing false positive.
5. `github_issues` pain signal, confidence `0.49`: bookkeeping/private-company accounting copy with `$75` receipt reference; relevant but marketing-adjacent.
6. `hacker_news_algolia` workaround, confidence `0.45`: bookkeeping service built for Dutch businesses; plausible solution/workaround signal, not pure pain.
7. `github_issues` pain signal, confidence `0.35`: accurate financial records and tax obligations; relevant but generic/vendor-like.
8. `hacker_news_algolia` pain signal, confidence `0.29`: small businesses using bookkeeping workarounds and unable to afford a full-time developer; plausible real SMB pain with explicit affordability complaint.
9. `hacker_news_algolia` workaround, confidence `0.26`: older accounting software and agent-assisted bookkeeping/tax filing; plausible workaround signal.
10. `hacker_news_algolia` workaround, confidence `0.24`: expensive accounting software vs oversimplified calculators for IRS rules; plausible SMB pain/workaround but low confidence.

## Quality Assessment

- Real finance/SMB pains: at least three plausible items appeared in the founder top 10: unpaid invoice follow-up, YNAB month-end balance-sheet reporting, and small-business bookkeeping/custom-software affordability.
- False positives: marketing/generated/vendor-promo content is present, especially in GitHub Issues, but it does not fully dominate the top 10 because HN contributed several real founder/workaround-style items.
- Traceability: `source_url` and `evidence_id` are preserved in candidate signals and founder package rows.
- Founder readability: `founder_discovery_package.md` is readable and includes source coverage, top signals, quality review sections, and recommended founder actions.
- Price hints: `price_signals.json` contains 8 evidence-bound hints, including `can't afford`, `$75`, and low-confidence possible buying/willingness indicators; several are weak/generic and need founder judgment.
- Weak patterns: `weak_pattern_candidates.json` exists with a clear empty state.
- Kill archive warnings: `kill_archive_warnings.json` exists with a clear empty state.
- Human review: `needs_human_review` appears for 6 ambiguous cases, including GitHub items that looked like submissions, generated/project pages, or unclear relevance.

## Success And Failure Criteria Results

- Protocol document exists: pass.
- Bounded real live run executed: pass.
- HN live source succeeded: pass.
- GitHub Issues live source succeeded: pass.
- Founder package generated: pass.
- Source counts summarized: pass.
- Top candidate signals summarized: pass.
- At least 2-3 plausible real finance/SMB pains: pass.
- Marketing/generated/install/tutorial false positives do not dominate top results: warning-pass; false positives are present and should be tuned, but they do not dominate all top results.
- `needs_human_review` used for ambiguity: pass.
- Runtime artifacts do not leave tracked git changes: pass.
- No live LLM/API calls: pass.

## Warnings And Blockers

- The requested branch name differed from the actual current branch. The run continued on `feat/v2-5-roadmap-planning`.
- Initial live collection attempt was blocked by local socket permissions and then completed after explicit network escalation for the same bounded command.
- GitHub Issues yielded several marketing/vendor-promo-like records; future query tuning should reduce generic accounting-service promotion.
- Some price hints are explicit but weakly useful, such as statutory/reference amounts or generic willingness indicators; founder review should not treat them as budgets.
- No blockers remain for using this as a first operational pass.

## Recommended Next Step

Proceed to the v2.5 Evidence Pack Layer, while also carrying a follow-up source/query quality note: GitHub Issues finance queries should be tightened to reduce vendor-promo and generated repository issue noise before increasing live volume.
