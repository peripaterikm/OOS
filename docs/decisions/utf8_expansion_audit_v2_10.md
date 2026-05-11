# UTF-8 Expansion Audit v2.10

**Roadmap:** v2.10
**Item:** 7.1 — Optional `--utf8` Expansion Audit
**Status:** Audit complete; implementation deferred unless separately approved
**Date:** 2026-05-11
**Scope:** Docs-only. No source code, test, or script changes. No runtime behavior change.

---

## 1. Context

### 1.1 v2.9 introduced explicit `--utf8` opt-in for selected commands

Roadmap v2.9 item 1.2 implemented explicit `--utf8` support on three commands that produce terminal-facing Markdown with visually significant status markers:

| Command | Reason |
|---------|--------|
| `weekly-cycle-status-v2` | 12-section Markdown status output with `[PASS]`/`[FAIL]`/`[WARN]` markers and `[CORRECTED]` indicators |
| `weekly-dashboard-v2` | Cross-run dashboard Markdown with table pass/fail markers and `[CORRECTED]` annotations |
| `build-weekly-run-report-v2` | Per-run report Markdown (11+ sections); CLI prints summary lines to terminal |

Additionally, v2.10 item 2.1 added `--utf8` to `import-founder-decisions-v2` because the undo-last contract ([`docs/contracts/undo_last_contract.md`](../contracts/undo_last_contract.md) Sections 9.3–9.4) explicitly requires `--utf8` support for the undo-result CLI output, which contains status markers (`OK` → `✓`, `FAIL` → `✗`).

### 1.2 v2.10 item 6.1 decided against automatic terminal encoding detection

The terminal encoding auto-detection policy ([`docs/decisions/terminal_encoding_auto_detection_policy.md`](terminal_encoding_auto_detection_policy.md)) confirmed:

- **ASCII-safe default remains mandatory.** All terminal-facing output without `--utf8` must contain only characters with `ord(c) < 128`.
- **`--utf8` remains explicit opt-in.** No automatic detection, no environment variable overrides, no `sys.stdout.encoding` probes.
- **Output mode decision tree unchanged:** `--utf8 present? → YES → utf8 mode | NO → ascii_safe mode`.

### 1.3 This item audits expansion only; it does not change runtime behavior

Per the v2.10 roadmap item 7.1 description:

> This is an audit-first task. Do not implement `--utf8` expansion in this pass.

The audit identifies candidate commands and produces recommendations. Implementation, if any, belongs in a future roadmap item (v2.11+) with separate approval.

---

## 2. Current Known `--utf8` Support

### 2.1 Commands already supporting `--utf8`

| # | Command | `--utf8` Flag | Source Location | Added In |
|---|---------|:---:|---|---|
| 1 | `import-founder-decisions-v2` | Yes | [`src/oos/cli.py:939-943`](../../src/oos/cli.py:939) | v2.10 item 2.1 (undo-last) |
| 2 | `weekly-cycle-status-v2` | Yes | [`src/oos/cli.py:995-999`](../../src/oos/cli.py:995) | v2.9 item 1.2 |
| 3 | `build-weekly-run-report-v2` | Yes | [`src/oos/cli.py:1017-1021`](../../src/oos/cli.py:1017) | v2.9 item 1.2 |
| 4 | `weekly-dashboard-v2` | Yes | [`src/oos/cli.py:1039-1044`](../../src/oos/cli.py:1039) | v2.9 item 1.2 |

All four commands route the `--utf8` boolean through [`src/oos/output_modes.py`](../../src/oos/output_modes.py) which provides `get_output_symbols(mode)` returning ASCII-safe or UTF-8 symbol dicts. The decision tree is:

```
--utf8 present? → output_mode = "utf8" → get_output_symbols("utf8")
               → output_mode = "ascii_safe" → get_output_symbols("ascii_safe")
```

### 2.2 Why `import-founder-decisions-v2` supports `--utf8`

The undo-last contract ([`docs/contracts/undo_last_contract.md`](../contracts/undo_last_contract.md) Section 9.3–9.4) defines both ASCII-safe and UTF-8 success output formats. The undo-last path in [`src/oos/cli.py:1116-1138`](../../src/oos/cli.py:1116) uses `format_undo_result_output(undo_result, use_utf8=use_utf8)` from [`src/oos/correction_undo.py`](../../src/oos/correction_undo.py). The normal import path (non-undo, lines 1140–1175) produces field-label/value output without status symbols and does not use the `--utf8` flag.

### 2.3 Commands NOT supporting `--utf8` — candidates for expansion audit

All remaining 14 CLI commands (see Section 3 inventory) are candidates for this expansion audit.

---

## 3. CLI Command Inventory

The following table covers every CLI command defined in [`src/oos/cli.py`](../../src/oos/cli.py), as of commit `45bee1c`.

| # | Command | `--utf8`? | Terminal Output | Symbols/Arrows/Separators? | Human‑ or Machine‑Readable? | ASCII‑Safe Already? | Recommendation |
|---|---------|:---:|---|---|---|---|---|
| 1 | `smoke-test` | No | `"OOS smoke test completed."` + artifact path | None | Human | Yes | No `--utf8` needed |
| 2 | `v1-dry-run` | No | `"OOS v1 dry run completed."` + `{key}: {path}` pairs | `:` separator only | Human | Yes | No `--utf8` needed |
| 3 | `run-signal-batch` | No | `"OOS signal batch run completed."` + `{key}: {path}` pairs | `:` separator only | Human | Yes | No `--utf8` needed |
| 4 | `run-weekly-cycle` | No | `"OOS weekly cycle completed."` + `{key}: {path}` pairs | `:` separator only | Human | Yes | No `--utf8` needed |
| 5 | `run-discovery-weekly` | No | `run_id`, `run_dir`, artifact paths | None | Human | Yes | No `--utf8` needed |
| 6 | `validate-live-quality-smoke` | No | `aggregate_status`, `runs_checked`, report paths | None | Human + machine (status string) | Yes | No `--utf8` needed |
| 7 | `generate-customer-voice-queries` | No | `topic`, `query_count`, file paths | None | Human | Yes | No `--utf8` needed |
| 8 | `preview-customer-voice-query-plans` | No | `topic`, counts, file paths | None | Human | Yes | No `--utf8` needed |
| 9 | `run-llm-signal-review-dry-run` | No | `review_run_id`, counts, `llm_calls_made`, file paths | None | Human | Yes | No `--utf8` needed |
| 10 | `weekly-cycle-status` (v1 legacy) | No | Plain text: project_root, inbox path, reviewable items with `-` bullets, founder decisions, portfolio summary | `-` (ASCII bullet) | Human | Yes | No `--utf8` needed |
| 11 | `evaluate-ai-ideation` | No | `"OOS AI ideation evaluation completed."` + `evaluation_report: {path}` | `:` separator only | Human | Yes | No `--utf8` needed |
| 12 | `record-founder-review` | No | `"Founder review decision recorded."` + `decision_artifact: {path}`, `portfolio_updated: {bool}` | `:` separator only | Human | Yes | No `--utf8` needed |
| 13 | `record-ai-stage-rating` | No | `"Founder AI-stage rating recorded."` + `"advisory_only: true"`, `rating_artifact: {path}` | `:` separator only | Human | Yes | No `--utf8` needed |
| 14 | `run-weekly-cycle-v2` | No | 20+ field-label/value lines: `run_id`, `run_dir`, `manifest_path`, `artifact_count`, `validation_passed`, `warnings_count`, counts, pipeline summary, safety flags, "Next step: ..." | `:` separator only; `-` for error/warning bullets | Human + structured | Yes | No `--utf8` needed |
| 15 | `import-founder-decisions-v2` | **Yes** | Undo-last path uses `format_undo_result_output()` with status markers. Normal import path prints field labels/values only. | Undo: `OK`/`FAIL`/`✓`/`✗`. Normal: `:` separator only. | Human | Yes (normal path) | Already supported |
| 16 | `weekly-cycle-status-v2` | **Yes** | 12-section Markdown with `[PASS]`/`[FAIL]`/`[WARN]` markers | Status markers, table cells, `[CORRECTED]` | Human | Yes (default) | Already supported |
| 17 | `build-weekly-run-report-v2` | **Yes** | Summary lines with field labels; Markdown artifact with status markers | Status markers in Markdown artifact | Human | Yes (default) | Already supported |
| 18 | `weekly-dashboard-v2` | **Yes** | Summary lines with field labels; cross-run Markdown table with `OK`/`FAIL` markers | Table cell pass/fail markers, `[CORRECTED]` | Human | Yes (default) | Already supported |

---

## 4. Candidate Assessment

### 4.1 Assessment of every command not currently supporting `--utf8`

For each of the 14 commands without `--utf8`:

| # | Command | Visual Benefit | Implementation Complexity | Test Complexity | ASCII‑Safe Risk | Overlap with Existing Utilities | Renderer Exists? | Output Stable? | Verdict |
|---|---------|---|---|---|---|---|---|---|---|
| 1 | `smoke-test` | None — prints one status line and a path | N/A | N/A | N/A | None | N/A | Yes | No benefit |
| 2 | `v1-dry-run` | None — prints a header and key:path pairs | N/A | N/A | N/A | None | N/A | Yes | No benefit |
| 3 | `run-signal-batch` | None — same pattern as v1-dry-run | N/A | N/A | N/A | None | N/A | Yes | No benefit |
| 4 | `run-weekly-cycle` | None — same pattern | N/A | N/A | N/A | None | N/A | Yes | No benefit |
| 5 | `run-discovery-weekly` | None — prints run metadata and paths | N/A | N/A | N/A | None | N/A | Yes | No benefit |
| 6 | `validate-live-quality-smoke` | None — prints aggregate_status string, counts, paths | N/A | N/A | N/A | None | N/A | Yes | No benefit |
| 7 | `generate-customer-voice-queries` | None — prints topic, count, paths | N/A | N/A | N/A | None | N/A | Yes | No benefit |
| 8 | `preview-customer-voice-query-plans` | None — prints topic, counts, paths | N/A | N/A | N/A | None | N/A | Yes | No benefit |
| 9 | `run-llm-signal-review-dry-run` | None — prints metadata and file paths | N/A | N/A | N/A | None | N/A | Yes | No benefit |
| 10 | `weekly-cycle-status` (v1) | None — prints plain text with ASCII `-` bullets | N/A | N/A | N/A | None | N/A | Yes | No benefit; legacy command |
| 11 | `evaluate-ai-ideation` | None — prints one status line and path | N/A | N/A | N/A | None | N/A | Yes | No benefit |
| 12 | `record-founder-review` | None — prints path and boolean | N/A | N/A | N/A | None | N/A | Yes | No benefit |
| 13 | `record-ai-stage-rating` | None — prints path and advisory flag | N/A | N/A | N/A | None | N/A | Yes | No benefit |
| 14 | `run-weekly-cycle-v2` | Minimal — prints 20+ field:value pairs with `:` separators. No status symbols. | Trivial (~10 lines) to add `--utf8` flag plumbing, but zero visual benefit | ~2 tests for flag acceptance and ASCII‑safe default | Low — output is already ASCII‑safe | Output contains no symbols that `get_output_symbols()` would replace | No markdown renderer; output is `print()` lines | Yes | Defer — no visual benefit |

### 4.2 Key finding

**None of the 14 unaudited commands produce terminal-facing output containing status markers (`[PASS]`, `[FAIL]`, `[WARN]`, `OK`, `FAIL`), arrows (`->`), or Unicode symbols.** Every command prints only:

- Plain text labels (`"OOS weekly cycle completed."`, `"Founder review decision recorded."`)
- Field-value pairs (`"run_id: ..."`, `"artifact_count: 5"`)
- File paths
- Boolean values (`"true"`, `"false"`)
- ASCII bullets (`"-"`) in the v1 `weekly-cycle-status` command

There are no status markers to upgrade, no arrows to convert to `→`, no dashes used as visual separators that would benefit from `—`. The entire set of remaining commands is already ASCII-safe and gains zero visual benefit from `--utf8`.

### 4.3 `run-weekly-cycle-v2` — the closest candidate

`run-weekly-cycle-v2` produces the most structured terminal output of the unaudited commands (20+ lines). However:
- Every line is a `{field_label}: {value}` pair.
- No status marker symbols appear. `validation_passed` is `"true"` or `"false"` (lowercase string), not a `✓`/`✗` marker.
- Warnings and errors use ASCII `-` prefix or `"warning: {text}"` format.
- The output is already scannable and unambiguous in ASCII.
- Adding `--utf8` would require inventing new visual conventions (e.g., turning `validation_passed: true` into `validation_passed: ✓`) that do not exist today. This is not "expansion" — it is new design.

---

## 5. Recommendation Categories

### 5.1 Category assignments

| Category | Commands | Count |
|----------|----------|:---:|
| **Already supported** | `import-founder-decisions-v2`, `weekly-cycle-status-v2`, `build-weekly-run-report-v2`, `weekly-dashboard-v2` | 4 |
| **Strong candidate for future `--utf8`** | *(none)* | 0 |
| **Weak candidate / defer** | `run-weekly-cycle-v2` | 1 |
| **No `--utf8` needed** | `smoke-test`, `v1-dry-run`, `run-signal-batch`, `run-weekly-cycle`, `run-discovery-weekly`, `validate-live-quality-smoke`, `generate-customer-voice-queries`, `preview-customer-voice-query-plans`, `run-llm-signal-review-dry-run`, `weekly-cycle-status` (v1), `evaluate-ai-ideation`, `record-founder-review`, `record-ai-stage-rating` | 13 |
| **Do not add `--utf8`** | *(none — no command is harmful to add it to, but none benefits)* | 0 |

### 5.2 `run-weekly-cycle-v2` — why "weak candidate / defer"

`run-weekly-cycle-v2` is classified as "weak candidate / defer" rather than "no `--utf8` needed" because:

- It has the most terminal output of any unaudited command (20+ lines).
- A future roadmap *could* decide to add status symbols to its output (e.g., a `✓` next to `validation_passed: true`).
- Adding `--utf8` plumbing now (~10 lines) would be trivial, but with zero benefit today.

However, this would be a new visual design decision, not an expansion of existing `--utf8` conventions. It is deferred to v2.11+ if a design proposal justifies it.

---

## 6. Triviality Threshold

### 6.1 Roadmap threshold

The v2.10 roadmap item 7.1 states:

> Implementation only if evidence supports it and change is trivial (≤30 lines per command, ≤2 files total).

### 6.2 Assessment against threshold

| Candidate | Lines per command | Files | Within threshold? | Recommended? |
|-----------|:---:|:---:|:---:|---|
| `run-weekly-cycle-v2` | ~10 | 2 (cli.py + tests) | **Yes** | **No** — zero visual benefit; no status symbols in output |
| Any other command | <10 | 1–2 | **Yes** | **No** — zero visual benefit |
| None qualify | — | — | — | **No expansion recommended** |

### 6.3 Why no command qualifies even if trivial

The triviality threshold is a necessary but not sufficient condition. Even if adding `--utf8` plumbing costs ≤30 lines, the command must *benefit* from it. None of the unaudited commands produce visually significant symbols that `--utf8` would upgrade. Adding a flag that does nothing visually is interface clutter.

---

## 7. ASCII-Safe Default Preservation

### 7.1 Confirmed unchanged

| Property | Status |
|----------|--------|
| Default output is ASCII-only (`ord(c) < 128`) | **Confirmed** — all 14 unaudited commands produce only ASCII-safe terminal output |
| `--utf8` remains explicit opt-in | **Confirmed** — no new `--utf8` flags added in this audit |
| No automatic encoding detection | **Confirmed** — per item 6.1 policy, no detection code exists or is planned |
| No output mode changes in tests unless explicitly requested | **Confirmed** — no test modifications |
| `get_output_symbols()` is the single source of truth for symbol mapping | **Confirmed** — [`src/oos/output_modes.py`](../../src/oos/output_modes.py) unchanged |

### 7.2 Verification

All existing commands that already support `--utf8` (4 commands) continue to default to ASCII-safe output. All 14 unaudited commands produce ASCII-safe output by construction (no Unicode symbols in their terminal output strings). The ASCII-safe default guarantee is preserved across all 18 CLI commands.

---

## 8. Risks

### 8.1 Scope creep

Adding `--utf8` to commands that have no visual symbols to upgrade would create a flag that does nothing. Users would rightfully ask "what does `--utf8` change?" and the answer would be "nothing." This degrades trust in the CLI interface.

### 8.2 Snapshot churn

If `--utf8` were added to `run-weekly-cycle-v2`, every existing test that invokes the command would need updating to either pass the flag or accept that the flag is a no-op. Snapshot-based tests that capture CLI output would need regeneration. This churn is unjustified without visual benefit.

### 8.3 Inconsistent CLI output patterns

Having `--utf8` on some commands where it does nothing visually, while it produces visible changes on 4 other commands, creates an inconsistent user experience. The current state — 4 commands where `--utf8` has a visible effect — is consistent and well-documented.

### 8.4 Adding `--utf8` to commands with machine-readable output

Commands like `validate-live-quality-smoke` and `run-weekly-cycle-v2` produce output that could be parsed by scripts (field:value format). Adding Unicode symbols to this output would break script-based parsing. These commands currently produce clean ASCII output suitable for both human reading and machine parsing.

### 8.5 Hidden dependency on terminal capabilities

This risk is already mitigated by the v2.10 item 6.1 policy decision (no auto-detection). It is restated here because any `--utf8` expansion must not accidentally introduce encoding probes.

---

## 9. Final Recommendation

### 9.1 Primary recommendation

**No `--utf8` expansion is recommended in v2.10.**

The audit finds that:

1. **All 4 commands that benefit from `--utf8` already support it.** The v2.9 commands (`weekly-cycle-status-v2`, `weekly-dashboard-v2`, `build-weekly-run-report-v2`) and the v2.10 undo-last command (`import-founder-decisions-v2`) cover every command that produces terminal-facing output with visually significant status markers.

2. **All 14 remaining commands produce ASCII-safe output with no status symbols.** Their terminal output consists of plain text labels, field:value pairs, file paths, and boolean values. There are no status markers, arrows, separators, or Unicode symbols to upgrade.

3. **`run-weekly-cycle-v2` is the closest candidate but has zero visual benefit today.** Its output is 20+ lines of `{label}: {value}` pairs. Adding `--utf8` would require inventing new visual conventions, which is design work, not expansion.

4. **The triviality threshold (≤30 lines, ≤2 files) is met for several commands but is irrelevant because there is no visual benefit.** Adding a flag that changes nothing is worse than not adding it.

### 9.2 Specific recommendation

| Action | Recommendation |
|--------|---------------|
| Expand `--utf8` to any additional command in v2.10 | **No** |
| Defer expansion to v2.11+ | **Yes** — if a design proposal justifies adding status symbols to `run-weekly-cycle-v2` or other commands |
| Close item 7.1 with audit document only | **Yes** — this document is the sole deliverable |
| Create a separate implementation item for expansion | **Not needed now** — if future work is desired, it belongs in a v2.11+ roadmap item with its own audit and design |

### 9.3 Conservative outcome

This is the preferred conservative outcome stated in the roadmap task:

> - No source changes in item 7.1.
> - Document candidates, if any.
> - Defer implementation unless there is a strong, trivial, low-risk case and explicit approval.

**No strong, trivial, low-risk case exists.** All candidates are either (a) commands with no visual symbols to upgrade, or (b) `run-weekly-cycle-v2` which would require new design work to benefit from `--utf8`. The audit documents this finding and closes the item without source changes.

---

## 10. Validation

### 10.1 Expected validation for this item

| Check | Expected Result |
|-------|----------------|
| Docs-only change | Only `docs/decisions/utf8_expansion_audit_v2_10.md` (new) and `docs/roadmaps/OOS_roadmap_v2_10_recovery_correction_checklist.md` (update) modified |
| No source/test/script changes | `git diff --stat` shows zero changes to `src/`, `tests/`, `scripts/` |
| `.\scripts\dev-git-check.ps1` | 6/6 checks pass |
| `git status --short` after commit | Clean working tree |

### 10.2 ASCII-safe default verification

The ASCII-safe default is unchanged by this audit document. All existing commands continue to produce ASCII-safe output by default. No new `--utf8` flags are added. No encoding detection is introduced.

### 10.3 Sub-item satisfaction

| Sub-item | Description | Status |
|----------|-------------|:---:|
| 7.1.1 | Audit document created at `docs/decisions/utf8_expansion_audit_v2_10.md` | Satisfied |
| 7.1.2 | All CLI commands not currently supporting `--utf8` are reviewed | Satisfied — 14 commands audited |
| 7.1.3 | Per-command assessment: does terminal output contain status symbols, arrows, separators, or other visually significant markers? | Satisfied — none do |
| 7.1.4 | Explicit recommendation for each command: add `--utf8` / do not add `--utf8`, with rationale | Satisfied — See Section 3 |
| 7.1.5 | If any command qualifies: implementation is trivial | N/A — no command qualifies; no implementation |
| 7.1.6 | If implemented: each added `--utf8` has tests covering ASCII-safe default and UTF-8 mode | N/A — not implemented |
| 7.1.7 | ASCII-safe default is confirmed unchanged | Satisfied — See Section 7 |
| 7.1.8 | No live APIs/LLMs | Satisfied — docs-only |

---

## 11. References

- [`docs/contracts/output_mode_contract.md`](../contracts/output_mode_contract.md) — Output mode contract (v2.9 item 1.1)
- [`docs/contracts/undo_last_contract.md`](../contracts/undo_last_contract.md) — Undo-last contract (v2.10 item 1.1), Sections 9.3–9.4 define UTF-8 output
- [`docs/decisions/terminal_encoding_auto_detection_policy.md`](terminal_encoding_auto_detection_policy.md) — Encoding auto-detection policy (v2.10 item 6.1)
- [`src/oos/cli.py`](../../src/oos/cli.py) — All 18 CLI subcommand definitions
- [`src/oos/output_modes.py`](../../src/oos/output_modes.py) — `get_output_symbols()` and `validate_output_mode()`
- [`docs/roadmaps/OOS_roadmap_v2_10_recovery_correction_checklist.md`](../roadmaps/OOS_roadmap_v2_10_recovery_correction_checklist.md) — Roadmap item 7.1 definition of done
