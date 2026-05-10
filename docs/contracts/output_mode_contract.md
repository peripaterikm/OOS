# Output Mode Contract

**Version:** output_mode.v1
**Roadmap:** v2.9 item 1.1
**Status:** contract / advisory only
**Schema:** defined in this document; implementation deferred to item 1.2

---

## 1. Purpose

### 1.1 Why Output Modes Exist

The OOS CLI writes human-readable Markdown to both terminal output and file-system artifacts. These outputs contain status markers, symbols, and separators that must be readable in two very different environments:

1. **Windows CP1251/CP1252 terminals.** The default code pages on Windows terminals (CP1251 for Cyrillic systems, CP1252 for Western European systems) cannot render many Unicode symbols. Characters beyond the 7-bit ASCII range (ordinal < 128) display as mojibake (garbled characters) or invisible glyphs. Key symbols affected include `✓` (U+2713), `✗` (U+2717), `⚠` (U+26A0), `→` (U+2192), and box-drawing characters (`─`, `├`, `└`, `│`).

2. **UTF-8-capable terminals.** Modern terminals (Windows Terminal with UTF-8 enabled, VS Code integrated terminal with `"terminal.integrated.defaultProfile.windows": "PowerShell"`, Linux/macOS terminals) can render the full Unicode set. For these environments, Unicode symbols improve scan-ability and visual clarity.

The output mode system reconciles these two environments without compromising either.

### 1.2 Why ASCII-Safe Default Is Required

**ASCII-safe is the default because it is the safe default.** On CP1251/CP1252 terminals, Unicode symbols are unreadable. The system must produce correct, readable output out of the box on the widest range of Windows terminals without requiring the user to change code pages or install a different terminal.

### 1.3 Why UTF-8 Is Opt-In, Not Default

**UTF-8 must be opt-in because:**

1. It is impossible for a subprocess to reliably detect terminal encoding on Windows without platform-specific libraries or I/O probing that introduces non-determinism.
2. CP1251/CP1252 terminals cannot render UTF-8 symbols; enabling UTF-8 by default would make the output worse for a significant fraction of users.
3. The founder/operator knows their terminal capabilities better than the program. An explicit `--utf8` flag is unambiguous and idempotent.

**Explicit non-goal for v2.9:** Automatic terminal encoding detection. No `sys.stdout.encoding` probes. No `chcp` checks. No `GetConsoleOutputCP()` calls. These are platform-specific, fragile, and introduce non-deterministic behavior. If encoding detection is ever added, it belongs in v2.10+ and must be justified by concrete user feedback.

---

## 2. Output Modes

### 2.1 `ascii_safe` — Default Mode

**Activation:** No flag (default behavior).

**Behavior:** All terminal-facing output must contain only characters with `ord(char) < 128`. Newlines (`\n`, U+000A) and tabs (`\t`, U+0009) are allowed.

**Symbols used:**
| Semantic | Symbol |
|----------|--------|
| Success / pass | `OK` |
| Failure / fail | `FAIL` |
| Warning | `WARN` |
| None / empty / not present | `NONE` |
| Arrow / direction | `->` |
| Separator / dash | `-` |
| Corrected indicator | `[CORRECTED]` |

All status markers in Markdown tables, section headers, and inline indicators must use these ASCII-safe symbols.

### 2.2 `utf8` — Opt-In Mode

**Activation:** `--utf8` flag passed to CLI subcommand.

**Behavior:** Terminal-facing output may contain Unicode characters, including symbols beyond the ASCII range. The canonical symbol set is defined in Section 4 and implemented in [`src/oos/output_modes.py`](../../src/oos/output_modes.py) `get_output_symbols("utf8")`.

**Symbols used:**
| Semantic | Symbol | Code Point |
|----------|--------|------------|
| Success / pass | `✓` | U+2713 |
| Failure / fail | `✗` | U+2717 |
| Warning | `⚠` | U+26A0 |
| None / empty / not present | `NONE` | ASCII (unchanged) |
| Arrow / direction | `→` | U+2192 |
| Separator / dash (em dash) | `—` | U+2014 |
| Corrected indicator | `[CORRECTED]` | ASCII (unchanged) |

**Rationale for symbol choices:**
- `✓` (U+2713), `✗` (U+2717), `⚠` (U+26A0): These are the most widely recognized Unicode symbols for pass/fail/warn states and are the original symbols that v2.8 item 4.1 (commit `e36a470`) replaced with ASCII-safe alternatives. The utf8 mode restores the visually richer Unicode forms for UTF-8-capable terminals.
- `→` (U+2192): Unicode rightwards arrow, more visually distinct than the ASCII `->` digraph.
- `—` (U+2014): Em dash used for section dividers and horizontal rules, replacing the ASCII hyphen `-`.
- `[CORRECTED]`: This is a semantic label, not a decorative symbol. It remains unchanged in both modes because its purpose is to communicate correction state unambiguously.
- `NONE`: A semantic placeholder for missing/empty data. Remains ASCII because it is a data label, not a visual ornament.

**Note on renderer-level prefixes:** Some caller modules (e.g., [`weekly_cycle_status.py`](../../src/oos/weekly_cycle_status.py), [`weekly_run_reports.py`](../../src/oos/weekly_run_reports.py)) may wrap canonical symbols in Markdown formatting or prefix them with labels like `[PASS]` / `[FAIL]` / `[WARN]` for scannability within rendered tables and section headers. Those prefixes are renderer-level conventions, not part of the canonical output mode symbol set defined in [`output_modes.py`](../../src/oos/output_modes.py). The canonical symbol values are always `✓`/`✗`/`⚠` for utf8 mode and `OK`/`FAIL`/`WARN` for ascii_safe mode.

### 2.3 Unknown Mode Behavior

If an implementation receives an unrecognized output mode value (e.g., from a misconfigured call or future enum extension), it must **fail closed**: raise a `ValueError` with a clear message listing the valid modes (`ascii_safe`, `utf8`). Silent fallback to any mode is prohibited.

```python
# Required fail-closed pattern (for item 1.2 implementation):
_VALID_MODES = frozenset({"ascii_safe", "utf8"})
if mode not in _VALID_MODES:
    raise ValueError(f"Unknown output mode {mode!r}. Expected one of: {', '.join(sorted(_VALID_MODES))}")
```

### 2.4 No Automatic Terminal Encoding Detection

v2.9 does **not** implement automatic terminal encoding detection. The decision tree is:

```
--utf8 present?  → YES → utf8 mode
                 → NO  → ascii_safe mode (default)
```

No other inputs affect output mode selection. This constraint is documented here so that future roadmaps (v2.10+) have an explicit design decision to reconsider if needed.

---

## 3. CLI Policy

### 3.1 Commands That MUST Support `--utf8` in Item 1.2

These commands produce terminal-facing Markdown output where symbols are visually significant:

| Command | Reason | Symbol Impact |
|---------|--------|---------------|
| `weekly-cycle-status-v2` | 12-section Markdown status output rendered to terminal. Uses `[PASS]`/`[FAIL]`/`[WARN]` markers, `[CORRECTED]` indicators, and separator lines. | Status markers, table cell markers, correction indicators |
| `weekly-dashboard-v2` | Cross-run dashboard Markdown with table containing `OK`/`FAIL` markers and `[CORRECTED]` annotations. | Table cell pass/fail markers, correction indicators |
| `build-weekly-run-report-v2` | Per-run report Markdown (11+ sections). Although primarily a file artifact, the CLI prints summary lines to the terminal. | Summary line markers, if any |

### 3.2 Commands That MAY Need `--utf8` (Audit Required During Item 1.2)

| Command | Condition | Audit Question |
|---------|-----------|----------------|
| `import-founder-decisions-v2` | Only if correction summary output printed to terminal contains mode/status symbols | Does the terminal summary print `[PASS]`/`[FAIL]`/`[WARN]` markers or `[CORRECTED]` indicators? |

During item 1.2 implementation, audit the terminal output of `import-founder-decisions-v2` in [`src/oos/cli.py`](../../src/oos/cli.py) lines 1072–1116. If correction summary output contains any status symbols, add `--utf8`. If it only prints raw counts and text labels (no symbols), `--utf8` is not needed.

### 3.3 Commands That Do NOT Need `--utf8`

All other CLI commands are explicitly excluded from `--utf8` scope in v2.9:

| Command | Reason for Exclusion |
|---------|---------------------|
| `smoke-test` | Legacy v1 command; prints only file paths |
| `v1-dry-run` | Legacy v1 command; prints only file paths and keys |
| `run-signal-batch` | Legacy v1 command; prints only file paths and keys |
| `run-weekly-cycle` | Legacy v1 command; prints only file paths and keys |
| `run-discovery-weekly` | Source Intelligence; prints run_id, run_dir, artifact paths |
| `validate-live-quality-smoke` | Prints aggregate_status, counts, file paths |
| `generate-customer-voice-queries` | Prints topic, counts, file paths |
| `preview-customer-voice-query-plans` | Prints topic, counts, file paths |
| `run-llm-signal-review-dry-run` | Prints counts, file paths |
| `weekly-cycle-status` | Legacy v1 command; prints plain text status |
| `evaluate-ai-ideation` | Prints file path only |
| `record-founder-review` | Prints artifact path and boolean |
| `record-ai-stage-rating` | Prints artifact path and advisory-only flag |
| `run-weekly-cycle-v2` | Prints structured summary (only field labels and values; no status symbols in terminal output) |

### 3.4 Expansion Policy

Adding `--utf8` to an excluded command in a future roadmap requires:
1. A documented justification of why the command produces terminal-facing output with visually significant symbols.
2. An update to this contract (Section 3).
3. Tests covering both output modes for the newly enabled command.

---

## 4. Canonical Symbol Mapping Table

This section is the single source of truth for output mode symbols. The canonical symbols are defined in [`src/oos/output_modes.py`](../../src/oos/output_modes.py) `get_output_symbols()` and reproduced here for documentation.

### 4.1 Symbol Mapping Table

| Semantic Key | `ascii_safe` | `utf8` | Code Point (utf8) | Used In |
|-------------|-------------|--------|-------------------|---------|
| `success` | `OK` | `✓` | U+2713 | Artifact completeness, manifest status, table cells |
| `failure` | `FAIL` | `✗` | U+2717 | Artifact completeness, manifest status, table cells |
| `warning` | `WARN` | `⚠` | U+26A0 | Warnings section markers |
| `none` | `NONE` | `NONE` | — | Correction entries, missing data placeholders |
| `arrow` | `->` | `→` | U+2192 | Path references, direction indicators |
| `dash` | `-` | `—` | U+2014 | Section dividers, horizontal rules |
| `corrected` | `[CORRECTED]` | `[CORRECTED]` | — | Run identity, correction summary rows |

### 4.2 Renderer-Level Prefixes vs Canonical Symbols

The **canonical symbol values** are defined by [`output_modes.py`](../../src/oos/output_modes.py) `get_output_symbols()` and are the values in the table above.

Caller modules (e.g., [`weekly_cycle_status.py`](../../src/oos/weekly_cycle_status.py), [`weekly_run_reports.py`](../../src/oos/weekly_run_reports.py)) may wrap these canonical symbols in additional Markdown formatting for scannability — for example, embedding the success/failure/warning symbol inside a `[PASS]` / `[FAIL]` / `[WARN]` label for table cells. These `[PASS]` / `[FAIL]` / `[WARN]` prefixes are **renderer-level conventions**, not part of the canonical output mode symbol set. The canonical symbol for ascii_safe success is always `OK`; the canonical symbol for utf8 success is always `✓`.

When writing output mode tests, assert against the canonical symbol from `get_output_symbols()`, not against renderer-level markup that may embed the symbol in a larger string.

### 4.3 Symbols NOT in the Canonical Set

The following Unicode symbols were previously used in OOS CLI output (before v2.8 item 4.1, commit `e36a470`) and are **NOT part of the canonical symbol set** defined in Section 4.1. They are documented here for completeness only:

- `✅` (U+2705) — previously used for pass/OK; replaced with `OK` for ascii_safe
- `❌` (U+274C) — previously used for fail; replaced with `FAIL` for ascii_safe
- `◉` (U+25C9) — previously used for bullet emphasis; replaced with `[*]` or removed
- `─` (U+2500) — box-drawing horizontal; replaced with `-` for ascii_safe
- `├` (U+251C) — box-drawing branch; replaced with `+` or removed
- `└` (U+2514) — box-drawing corner; replaced with `+` or removed
- `│` (U+2502) — box-drawing vertical; replaced with `|` or removed

**Note on `⚠` (U+26A0):** `⚠` IS mapped in the canonical set as the utf8 warning symbol (see Section 4.1). It was present in earlier versions of this contract in the "NOT mapped" list in error; that error is corrected here. The utf8 mode intentionally uses `⚠` for warning output.

---

## 5. Compatibility Rules

### 5.1 ASCII-Safe Output Guarantee

**Rule:** Default terminal-facing output MUST contain only characters with `ord(char) < 128`, excluding newlines (`\n`, U+000A) and tabs (`\t`, U+0009).

**Enforcement:** Tests for item 1.2 must verify this property on every command that supports `--utf8`. The check must iterate over every character in the output string and assert `ord(c) < 128 or c in {'\n', '\t'}`.

### 5.2 UTF-8 Mode May Contain Unicode

When `--utf8` is passed, output may contain Unicode characters including those beyond ASCII range 32–126. The canonical symbol set is defined in Section 4.1.

### 5.3 JSON Artifacts Are Output-Mode Independent

**Rule:** JSON artifacts written to the file system (`*.json` files under `artifacts/`) MUST NOT depend on the output mode.

JSON artifacts use `"ensure_ascii": false` for human readability (enabling Unicode in file content), but their structure, keys, and values are mode-independent. A JSON artifact generated with `--utf8` is byte-identical to one generated without `--utf8` (modulo non-deterministic timestamps, which are pinned during testing).

### 5.4 Markdown Artifacts: ASCII-Safe by Default

**Rule:** Markdown files written as artifacts (e.g., `run_report.md`, `dashboard.md`, `founder_inbox_v2.md`) should prefer ASCII-safe symbols by default, matching the terminal output mode.

When `--utf8` is passed, Markdown artifacts may contain Unicode symbols. The artifact content reflects the output mode passed at generation time.

### 5.5 No Source URL / Correction Semantics Depend on Output Mode

**Rule:** Output mode MUST NOT affect:
- Source URL traceability (placeholders, missing URLs, malformed URLs).
- Correction semantics (replace, amend, reject-on-reimport).
- Import history / audit trail content.
- Decision values, feedback mappings, preference profiles, or parking lot records.
- Any business logic.

Output mode is a **rendering concern only**. It affects how bytes are formatted for human consumption, never what decisions the system makes.

### 5.6 CP1251/CP1252 Compatibility Through ASCII Default

The ASCII-safe default guarantees correct rendering on CP1251 (Cyrillic) and CP1252 (Western European) Windows terminals because all output characters are in the 7-bit ASCII range, which is a subset of both code pages. No special code-page handling is needed.

---

## 6. Testing Requirements

### 6.1 Tests for ASCII Default: No Non-ASCII Characters

Every command that supports `--utf8` must have a test that:

1. Runs the command without `--utf8`.
2. Captures the terminal output string.
3. Asserts that every character `c` in the output satisfies `ord(c) < 128 or c in {'\n', '\t'}`.

### 6.2 Tests for UTF-8 Mode: Expected Unicode Markers Appear

Every command that supports `--utf8` must have a test that:

1. Runs the command with `--utf8`.
2. Captures the terminal output string.
3. Asserts that expected Unicode markers appear (e.g., `→`, `—`, and/or `✓`/`✗`/`⚠` depending on the output content).

### 6.3 CP1251/CP1252 Compatibility Through ASCII Default

The ASCII-default test (Section 6.1) serves as the CP1251/CP1252 compatibility test. Any output that passes the `ord(c) < 128` check is guaranteed to render correctly on both code pages.

### 6.4 No Regression in Run-Controlled-Smoke

The controlled weekly run smoke test (`scripts/run-controlled-smoke.ps1`) must continue to pass after `--utf8` is implemented. The smoke test runs without `--utf8`, so ASCII-safe output is the expected behavior.

### 6.5 No Live APIs/LLMs

All output mode tests must be deterministic and offline. No live API calls, no LLM invocations, no network access.

### 6.6 Minimum Test Count

Item 1.2 must deliver at least 12 focused tests covering:
1. ASCII-safe default for `weekly-cycle-status-v2`
2. UTF-8 output for `weekly-cycle-status-v2`
3. ASCII-safe default for `weekly-dashboard-v2`
4. UTF-8 output for `weekly-dashboard-v2`
5. ASCII-safe default for `build-weekly-run-report-v2`
6. UTF-8 output for `build-weekly-run-report-v2`
7. CLI `--utf8` flag propagation
8. No-flag default behavior (ASCII-safe)
9. Symbol mapping correctness in both modes
10. No information loss between modes
11. CP1251/CP1252 safety (ASCII-only check)
12. Excluded commands do not accept `--utf8`

---

## 7. Non-Goals

The following are **explicitly excluded** from v2.9 scope:

| Non-Goal | Rationale |
|----------|-----------|
| Live terminal encoding auto-detection | Platform-specific, non-deterministic; deferred to v2.10+ |
| Rich terminal formatting (colors, bold, underline) | Out of scope for all v2.x roadmaps per scope-v1 |
| Color output (ANSI escape codes) | Out of scope; ASCII-safe plain text only |
| Business logic changes | Output mode is rendering-only |
| Correction semantics changes | Output mode does not affect correction workflow |
| Source URL behavior changes | Output mode does not affect traceability |
| `--utf8` on all CLI commands | Only status/dashboard/report commands in v2.9; expansion requires justification (Section 3.4) |
| Per-symbol or per-section `--utf8` granularity | `--utf8` is a single boolean flag; all-or-nothing |
| Unicode normalization or canonicalization | Output mode is about symbol selection, not Unicode processing |

---

## 8. Acceptance Criteria for Item 1.2 (Preview)

This section defines what item 1.2 must satisfy when it references this contract. It is included here so that the contract serves as a self-contained specification.

| # | Criterion | Source Section |
|---|-----------|---------------|
| 1.2.1 | `--utf8` flag on `weekly-cycle-status-v2` | 3.1 |
| 1.2.2 | `--utf8` flag on `weekly-dashboard-v2` | 3.1 |
| 1.2.3 | `--utf8` flag on `build-weekly-run-report-v2` | 3.1 |
| 1.2.4 | Default output is ASCII-safe (no Unicode > ord 126, except `\n`/`\t`) | 2.1, 5.1, 6.1 |
| 1.2.5 | `--utf8` output restores Unicode symbols | 2.2, 4.1, 6.2 |
| 1.2.6 | No information loss between modes | 5.3, 5.5 |
| 1.2.7 | CP1251/CP1252 terminals render default output correctly | 5.6, 6.3 |
| 1.2.8 | Symbol selection centralized in a single helper per module | 2.2 (implied: `_status_symbols(utf8: bool) -> dict`) |
| 1.2.9 | `import-founder-decisions-v2` audited; `--utf8` added only if needed | 3.2 |
| 1.2.10 | Existing tests pass without modification | 6.4 |
| 1.2.11 | >=12 focused tests covering both modes | 6.6 |
| 1.2.12 | No live APIs/LLMs | 6.5 |

---

## 9. Motivation: v2.8 Item 4.1 Implementation Gap

This contract exists because of a documented gap in the v2.8 roadmap:

- **v2.8 item 4.1** (commit `e36a470`, "fix(v2.8): harden Windows CLI output") replaced Unicode symbols with ASCII-safe alternatives in all CLI output. This was the correct safety fix.
- **v2.8 acceptance criterion 4.1.3** stated: "`--utf8` flag forces Unicode output for UTF-8-capable terminals." This criterion was marked `[x]` complete, but a code audit at the start of v2.9 confirmed **zero occurrences of `utf8`** in `src/oos/`. The `--utf8` flag was never implemented.
- **v2.8 final validation** (item 7.1) did not catch this discrepancy.

The v2.8 gap is:

| What Was Delivered | What Was Missing |
|--------------------|------------------|
| ASCII-safe default output (correct) | `--utf8` opt-in flag (not implemented) |
| CP1251/CP1252 compatibility (correct) | Unicode symbol restoration path (not implemented) |
| Symbol replacement in all modules (correct) | Centralized symbol selection per module (not implemented) |
|                                  | Tests for `--utf8` mode (not implemented) |
|                                  | Mini-epic and run report for item 4.1 (not created) |

This contract defines the missing specification so that item 1.2 can implement it correctly.

---

## 10. References

- [`docs/roadmaps/OOS_roadmap_v2_9_output_modes_source_url_strictness_and_correction_recovery_checklist.md`](../roadmaps/OOS_roadmap_v2_9_output_modes_source_url_strictness_and_correction_recovery_checklist.md) — v2.9 roadmap checklist
- [`docs/dev_ledger/00_project_state.md`](../dev_ledger/00_project_state.md) — project state (v2.8 item 4.1 gap documented at line 159)
- [`src/oos/cli.py`](../../src/oos/cli.py) — CLI subcommands (no `--utf8` flag anywhere)
- [`src/oos/weekly_cycle_status.py`](../../src/oos/weekly_cycle_status.py) — status Markdown renderer (uses `OK`/`FAIL`/`NONE`/`[CORRECTED]`)
- [`src/oos/weekly_run_reports.py`](../../src/oos/weekly_run_reports.py) — run report and dashboard Markdown renderers (uses `OK`/`FAIL`/`[CORRECTED]`)
- [`docs/contracts/source_url_traceability_contract.md`](source_url_traceability_contract.md) — source URL traceability (output-mode independent per Section 5.5)
