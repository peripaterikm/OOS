# Terminal Encoding Auto-Detection Policy

**Roadmap:** v2.10 item 6.1 — Encoding Auto-Detection Audit/Policy
**Date:** 2026-05-11
**Status:** Policy/audit complete; implementation deferred unless explicitly approved
**Decision:** Do not implement automatic terminal encoding detection in v2.10

---

## 1. Title and Status

- **Title:** Terminal Encoding Auto-Detection Policy
- **Roadmap:** v2.10
- **Item:** 6.1
- **Status:** Policy/audit complete; implementation deferred unless explicitly approved
- **Scope:** Docs-only. No source code, test, or script changes. No runtime behavior change.

---

## 2. Context

### 2.1 v2.9 established the ASCII-safe default with explicit `--utf8` opt-in

Roadmap v2.9 item 1.2 implemented the two-mode output system:

- **ASCII-safe (default):** All terminal-facing output uses only characters with `ord(c) < 128`.
- **UTF-8 (opt-in):** Pass `--utf8` to enable Unicode symbols (`✓`, `✗`, `⚠`, `→`, `—`) for visual clarity.

The [`output_mode_contract.md`](../contracts/output_mode_contract.md) Section 1.3 explicitly deferred automatic terminal encoding detection:

> **Explicit non-goal for v2.9:** Automatic terminal encoding detection. No `sys.stdout.encoding` probes. No `chcp` checks. No `GetConsoleOutputCP()` calls. These are platform-specific, fragile, and introduce non-deterministic behavior. If encoding detection is ever added, it belongs in v2.10+ and must be justified by concrete user feedback.

### 2.2 v2.10 item 6.1 is audit/policy only

The v2.10 roadmap scoped item 6.1 as:

> **Intent:** The output mode contract (v2.9 item 1.1, Section 1.3) explicitly deferred automatic terminal encoding detection to v2.10+. This item audits the feasibility on Windows (CP1251/CP1252 detection, `sys.stdout.encoding`, `chcp`, `GetConsoleOutputCP()`) and defines a policy document. The audit must answer: is reliable detection possible without platform-specific hacks? Can it be deterministic? What are the false-positive/false-negative risks? The policy must state whether auto-detection is recommended, and if so, under what constraints it could be implemented in a future roadmap (v2.11+). **This item does NOT implement auto-detection.** It produces an audit/policy document only.

### 2.3 No runtime behavior change is allowed in this item

Safety Gate D in the v2.10 roadmap checklist enforces:

> **Condition:** Item 6 produces an audit/policy document only. No `sys.stdout.encoding` probes, no `chcp` checks, no `GetConsoleOutputCP()` calls are introduced. The output mode decision tree remains: `--utf8 present? → YES → utf8 mode | NO → ascii_safe mode`.

---

## 3. Current Output Mode Policy

### 3.1 Decision tree

The current output mode selection logic (from [`output_mode_contract.md`](../contracts/output_mode_contract.md) Section 2.4) is:

```
--utf8 present?  → YES → utf8 mode
                 → NO  → ascii_safe mode (default)
```

No other inputs affect output mode selection. The [`output_modes.py`](../../src/oos/output_modes.py) module exposes exactly two modes (`ascii_safe`, `utf8`) through [`validate_output_mode()`](../../src/oos/output_modes.py:18) and [`get_output_symbols()`](../../src/oos/output_modes.py:38). Unknown mode values cause a fail-closed `ValueError`.

### 3.2 ASCII-safe default remains unchanged

The ASCII-safe default is non-negotiable for v2.10. It is enforced by Safety Gate C in the v2.10 roadmap:

> **Condition:** Default terminal-facing output (no `--utf8` flag) must contain only characters with `ord(c) < 128`, excluding newlines and tabs.

The ASCII-safe default guarantees correct rendering on CP1251 (Cyrillic) and CP1252 (Western European) Windows terminals because all output characters are in the 7-bit ASCII range, which is a subset of both code pages. No special code-page handling is needed.

### 3.3 `--utf8` remains explicit opt-in

UTF-8 output mode requires the founder to pass `--utf8` explicitly. This is unambiguous, idempotent, and puts the founder in control. The founder knows their terminal capabilities better than the program.

---

## 4. Windows Terminal Encoding Landscape

### 4.1 CP1251 (Windows-1251, Cyrillic)

- **Prevalence:** Default code page on Russian, Ukrainian, Bulgarian, Serbian (Cyrillic), and other Cyrillic-script Windows installations.
- **Glyph range:** 256 code points. The lower 128 are identical to ASCII. The upper 128 contain Cyrillic characters.
- **Unicode compatibility:** Characters beyond the 7-bit ASCII range that are not in the CP1251 upper-128 table render as garbage (`?`, empty boxes, or different glyphs). Unicode symbols like `✓` (U+2713), `✗` (U+2717), `⚠` (U+26A0), `→` (U+2192) are NOT in CP1251 and will display as mojibake.
- **Detection challenges:** `sys.stdout.encoding` may report `'cp1251'` in interactive terminals, but `None` or `'utf-8'` when stdout is redirected. `locale.getpreferredencoding()` may report `'cp1251'` regardless of terminal state. `chcp` output reflects the active console code page, which can differ from the actual terminal rendering capability.

### 4.2 CP1252 (Windows-1252, Western European)

- **Prevalence:** Default code page on English, German, French, Spanish, Italian, and other Western European Windows installations.
- **Glyph range:** 256 code points. Lower 128 identical to ASCII. Upper 128 contain Latin-1 supplement characters (accented letters, currency symbols, punctuation).
- **Unicode compatibility:** Same limitation as CP1251: Unicode symbols outside the CP1252 repertoire cannot render. `✓`, `✗`, `⚠`, `→`, `—` are all outside CP1252 and will display as mojibake.
- **Detection challenges:** Identical structural issues to CP1251. `sys.stdout.encoding` may report `'cp1252'`, but this does not mean the terminal can render arbitrary Unicode. It only means the terminal uses CP1252 as its code page.

### 4.3 CP65001 (UTF-8 code page)

- **What it is:** Windows code page 65001 is UTF-8. Setting `chcp 65001` in a console window tells Windows to interpret output as UTF-8. However, the legacy console host (`conhost.exe`) has a long history of bugs with CP65001, including dropped output, incorrect cursor positioning, and crashes with certain character sequences.
- **Where it works well:** Windows Terminal (the modern terminal app) with UTF-8 enabled, VS Code integrated terminal, and PowerShell Core (`pwsh.exe`) with UTF-8 settings all handle UTF-8 correctly. In these environments, `sys.stdout.encoding` typically reports `'utf-8'` or `'UTF-8'`.
- **Where it fails silently:** Legacy `cmd.exe` with `chcp 65001` may report UTF-8 capability but still fail to render certain Unicode glyphs due to font limitations (the terminal font must include glyphs for the code points being rendered).
- **Detection challenges:** `chcp` output may say `65001`, but the actual rendering depends on the terminal emulator AND the configured font. A terminal with a font lacking Unicode glyph coverage will still show mojibake even with CP65001 active.

### 4.4 Windows Terminal

- **Behavior:** The modern Windows Terminal app supports UTF-8 natively. It bundles fonts with good Unicode coverage (Cascadia Code, Cascadia Mono). `sys.stdout.encoding` typically reports `'utf-8'`.
- **Detection:** Relatively reliable — `sys.stdout.encoding == 'utf-8'` combined with the `WT_SESSION` environment variable (which Windows Terminal sets) is a strong signal that the terminal can render UTF-8.
- **Caveat:** Even in Windows Terminal, the user may have configured a legacy font that lacks Unicode glyphs. Detection can never be 100% certain.

### 4.5 VS Code Integrated Terminal

- **Behavior:** The VS Code integrated terminal runs a shell (typically PowerShell or cmd.exe) inside VS Code's terminal emulator. The terminal emulator supports UTF-8 rendering. `sys.stdout.encoding` typically reports `'utf-8'`.
- **Detection:** `sys.stdout.encoding == 'utf-8'` is reliable in this environment. Additionally, the `TERM_PROGRAM` environment variable is set to `'vscode'`, providing another signal.
- **Caveat:** On some Windows configurations, VS Code may inherit the system code page setting. If the system locale is CP1251 and VS Code is configured to use the legacy console, encoding may report as `'cp1251'` even though VS Code's terminal emulator can render UTF-8. This is a false-negative risk.

### 4.6 PowerShell

- **PowerShell 5.x (Windows PowerShell):** Uses the legacy console host. `sys.stdout.encoding` typically reports the system code page (e.g., `'cp1252'`). UTF-8 rendering depends on the console host, not PowerShell itself.
- **PowerShell 7+ (PowerShell Core):** Supports UTF-8 natively. `sys.stdout.encoding` typically reports `'utf-8'`. Much more reliable than PowerShell 5.x for Unicode output.
- **Detection challenge:** PowerShell version and encoding behavior are not trivially correlated. Checking `$PSVersionTable` requires spawning a subprocess or reading environment variables — both of which introduce overhead and fragility.

### 4.7 Legacy cmd.exe

- **Behavior:** The classic Windows command prompt (`cmd.exe`) uses the system code page (CP1251, CP1252, etc.) by default. Unicode rendering is limited to the code page's repertoire. `sys.stdout.encoding` reports the active code page.
- **Detection:** `sys.stdout.encoding` reliably reports the legacy code page. This is the one case where detection is unambiguous — but it tells you the terminal CANNOT render UTF-8, not that it can.
- **Caveat:** A user who has run `chcp 65001` in their cmd.exe session may have `sys.stdout.encoding` report `'utf-8'` or `'cp65001'`, but this does not guarantee that the console host + font can actually render all Unicode glyphs. The legacy console host has known CP65001 bugs.

### 4.8 Redirected stdout / CI logs

- **Behavior:** When stdout is redirected to a file or pipe, `sys.stdout.encoding` typically reports `None` (Python falls back to `locale.getpreferredencoding()`) or `'ANSI_X3.4-1968'` (ASCII). In CI environments (GitHub Actions, Azure Pipelines), encoding is usually `'utf-8'` but can vary.
- **Detection challenge:** Redirected output has no "terminal" to detect. Any auto-detection based on stdout encoding would produce different results depending on whether output is going to a terminal or a file — a reproducibility hazard.
- **Impact on tests:** Tests that capture CLI output via subprocess often see `sys.stdout.encoding = None` or `'utf-8'` in the subprocess, regardless of the parent terminal's actual rendering capability. This makes test-based validation of auto-detection unreliable.

---

## 5. Detection Methods Evaluated

### 5.1 `sys.stdout.encoding`

- **What it reports:** Python's best guess at the encoding of the stdout stream. This is determined by the Python runtime at startup, based on the environment it detects.
- **Values observed on Windows:**
  - `'cp1251'` — CP1251 code page (Cyrillic systems)
  - `'cp1252'` — CP1252 code page (Western European systems)
  - `'utf-8'` — UTF-8 terminal (Windows Terminal, VS Code, PowerShell Core)
  - `'cp65001'` — UTF-8 code page set via `chcp 65001`
  - `None` — stdout is redirected (pipe or file)
  - `'ANSI_X3.4-1968'` — ASCII fallback in some CI environments
- **Reliability assessment:** Low. `sys.stdout.encoding` tells you what Python THINKS the encoding is, not what the terminal CAN RENDER. A `'utf-8'` report does not guarantee glyph coverage in the terminal font. A `'cp1251'` report does not mean the user hasn't configured their terminal to handle UTF-8 (e.g., running a Python script inside VS Code on a CP1251 system locale).
- **Determinism:** Non-deterministic across environments. Same code, same OOS run, different `sys.stdout.encoding` depending on terminal, redirection state, and system locale.

### 5.2 `locale.getpreferredencoding()`

- **What it reports:** The encoding derived from the system locale settings (Control Panel → Region → Administrative → Language for non-Unicode programs). This is a system-wide setting, not a per-terminal setting.
- **Values observed on Windows:**
  - `'cp1251'` — Cyrillic system locale
  - `'cp1252'` — Western European system locale
  - `'cp65001'` — UTF-8 system locale (Windows 10 1903+ with "Beta: Use Unicode UTF-8 for worldwide language support" enabled)
- **Reliability assessment:** Very low for terminal detection. This tells you the SYSTEM LOCALE, not the TERMINAL'S capability. On a CP1251 system, the user may be using Windows Terminal with full UTF-8 support. On a CP65001 system, the user may be using legacy cmd.exe with a font that lacks Unicode glyphs.
- **Determinism:** Deterministic for a given machine, but varies across machines. Tests on different developer machines would see different values.

### 5.3 `chcp`

- **What it does:** The Windows `chcp.com` command reports the active console code page number. Running `chcp` as a subprocess returns output like `Active code page: 437` or `Active code page: 65001`.
- **Values observed:**
  - `437` — OEM United States
  - `850` — OEM Multilingual Latin 1
  - `866` — OEM Cyrillic
  - `1251` — ANSI Cyrillic
  - `1252` — ANSI Latin 1
  - `65001` — UTF-8
- **Reliability assessment:** Low to medium. `chcp` reports the active code page of the console, which is more specific than `locale.getpreferredencoding()`. However:
  - Spawning a subprocess for every CLI invocation is expensive and fragile.
  - `chcp` output format varies by Windows language (the text "Active code page:" is localized).
  - `chcp 65001` does not guarantee font glyph coverage.
  - `chcp` is only meaningful in a console context. When stdout is redirected, there is no console, and `chcp` may return meaningless or error output.
- **Determinism:** Non-deterministic across environments. Changes when the user runs `chcp` manually.

### 5.4 Windows `GetConsoleOutputCP()`

- **What it does:** The Win32 API function `GetConsoleOutputCP()` returns the output code page of the console attached to the calling process. Accessible via `ctypes.windll.kernel32.GetConsoleOutputCP()` or `pywin32`.
- **Reliability assessment:** Medium. More reliable than parsing `chcp` output because it is a direct API call. However:
  - Requires `ctypes` or `pywin32` — a new dependency surface.
  - Returns the code page, not rendering capability.
  - Fails or returns meaningless values when no console is attached (redirected stdout, CI, background process).
  - Requires error handling for the no-console case, introducing control flow complexity.
- **Determinism:** Deterministic for a given console session, but varies across environments.

### 5.5 Environment variables

- **Candidates:**
  - `WT_SESSION` — Set by Windows Terminal. Presence strongly suggests UTF-8 capability.
  - `TERM_PROGRAM` — Set to `'vscode'` by VS Code integrated terminal. Suggests UTF-8 capability.
  - `TERM` — May be set by terminal emulators; values like `'xterm-256color'` suggest UTF-8.
  - `PYTHONIOENCODING` — Can be manually set by the user to override Python's encoding detection.
  - `LANG`, `LC_ALL`, `LC_CTYPE` — Typically not set on Windows by default, but can be manually configured.
- **Reliability assessment:** Medium for UTF-8-positive signals (WT_SESSION, TERM_PROGRAM). Low for UTF-8-negative signals (absence of these variables does not mean UTF-8 is unavailable). Environment variables can be spoofed, unset, or inherited from parent processes.
- **Determinism:** Deterministic for a given session, but varies across environments.

### 5.6 Terminal capability probing

- **What it means:** Writing a test Unicode character to the terminal and asking the user to confirm whether it rendered correctly. Or using terminal escape sequences to query terminal capabilities.
- **Reliability assessment:** Very low to impractical.
  - Escape sequence queries require terminal support (DECRQSS, etc.) that is not universal.
  - User-confirmation probing ("Did you see a checkmark? [y/N]") breaks non-interactive usage, CI, and automated scripts.
  - Probing changes the terminal output, which is unacceptable for a general-purpose CLI tool.
- **Determinism:** Inherently non-deterministic (requires human input or assumes terminal capability).

### 5.7 Explicit user flag only (current approach)

- **What it does:** The user passes `--utf8` or does not. No detection. No probing. No environment checks.
- **Reliability assessment:** Perfect. The user knows their terminal. The flag is unambiguous and idempotent.
- **Determinism:** Fully deterministic. Same flag → same mode, every time, everywhere.

---

## 6. Determinism Assessment

### 6.1 Can detection be deterministic across supported Windows configurations?

**No.** Terminal encoding detection on Windows cannot be made fully deterministic across the supported OOS configurations. The fundamental problem is that **encoding capability and rendering capability are decoupled**:

- The system code page (CP1251/CP1252) affects what `sys.stdout.encoding` reports.
- The terminal emulator (Windows Terminal, VS Code, legacy conhost) affects what glyphs can actually render.
- The terminal font affects whether specific Unicode code points have glyph coverage.
- The user's manual `chcp` override changes the active code page independently of the system locale.
- Stdout redirection changes encoding reporting completely, regardless of the actual terminal.

No single detection method captures all of these dimensions. Combining multiple methods increases complexity but does not eliminate the gap between "encoding reported" and "glyphs rendered."

### 6.2 What changes between interactive terminal, redirected output, CI, VS Code terminal, and legacy console?

| Environment | `sys.stdout.encoding` | `chcp` output | `GetConsoleOutputCP()` | `locale.getpreferredencoding()` | `WT_SESSION` | Reliable? |
|---|---|---|---|---|---|---|
| Interactive cmd.exe (CP1251) | `'cp1251'` | `1251` | `1251` | `'cp1251'` | absent | No — code page ≠ glyph capability |
| Interactive cmd.exe (CP65001) | `'cp65001'` or `'utf-8'` | `65001` | `65001` | varies | absent | No — legacy conhost CP65001 bugs |
| Windows Terminal | `'utf-8'` | `65001` | `65001` | varies | present | Yes — strong signal |
| VS Code integrated terminal | `'utf-8'` | `65001` | `65001` | varies | absent (has `TERM_PROGRAM`) | Yes — strong signal |
| PowerShell 5.x | system code page | system code page | system code page | varies | absent | No — same as cmd.exe |
| PowerShell 7+ | `'utf-8'` | `65001` | `65001` | varies | absent | Moderate |
| Redirected stdout (pipe/file) | `None` | N/A (no console) | error | `'cp1251'` or `'cp1252'` | absent | No — no terminal to detect |
| CI (GitHub Actions) | `'utf-8'` | N/A | error | `'utf-8'` or `'ANSI_X3.4-1968'` | absent | No — CI has no human reading output |
| VS Code on CP1251 locale | `'cp1251'` | `1251` | `1251` | `'cp1251'` | absent | No — false negative (VS Code CAN render UTF-8) |

### 6.3 What are the reproducibility risks?

1. **Same code, different output modes on different machines.** A developer on a CP1252 system would get ASCII-safe output; a developer in Windows Terminal would get UTF-8 output. This makes CLI output snapshots non-reproducible.
2. **Tests passing locally but failing in CI.** If auto-detection is unit-testable, the test must mock the detection result. If the mock doesn't perfectly replicate CI behavior, tests diverge.
3. **Bug reports tied to terminal configuration, not code.** A bug report saying "the symbols are garbled" becomes a terminal debugging exercise, not a code fix.
4. **Git bisect and regression testing unreliable.** If output mode depends on environment, a git bisect across versions may produce different output for the same commit depending on which terminal is used.

---

## 7. False-Positive / False-Negative Risks

### 7.1 False positive: detecting UTF-8 when glyph rendering still fails

**Scenario:** A user has `chcp 65001` active in legacy `cmd.exe` with the "Consolas" font that lacks glyphs for `✓` (U+2713) and `✗` (U+2717).

- Detection says: `sys.stdout.encoding == 'utf-8'`, `chcp` says `65001`, `GetConsoleOutputCP()` says `65001` → switch to UTF-8 mode.
- Actual result: `✓` and `✗` render as empty boxes or `?`. Output is WORSE than ASCII-safe default.
- **Severity:** High. The whole point of ASCII-safe default is to prevent exactly this.
- **Mitigation:** None available without font probing, which is impractical.

**Scenario (variant):** VS Code on a CP1251 system locale where Python reports `sys.stdout.encoding = 'cp1251'` but the VS Code terminal emulator can actually render UTF-8 perfectly.

- Detection says: `sys.stdout.encoding == 'cp1251'` → stay in ASCII-safe mode.
- This is a **false negative** (Section 7.2), but it is the SAFE failure mode. ASCII-safe output is always readable.

### 7.2 False negative: detecting non-UTF-8 when output could have worked

**Scenario:** A user is in Windows Terminal with full UTF-8 support, but `sys.stdout.encoding` reports `'cp1252'` because the system locale is Western European and Python was launched from a script that didn't propagate UTF-8 settings.

- Detection says: `sys.stdout.encoding == 'cp1252'` → stay in ASCII-safe mode.
- Actual capability: Terminal can render UTF-8. The user misses out on Unicode symbols.
- **Severity:** Low. ASCII-safe output is functional, just less visually polished. The user can always pass `--utf8` explicitly.
- **Mitigation:** Not needed — the safe failure mode is acceptable.

### 7.3 Redirected logs

**Scenario:** A user runs `oos weekly-cycle-status-v2 > status.txt` to capture output. With auto-detection, `sys.stdout.encoding` is `None` (redirected). What mode should the system choose?

- If ASCII-safe: The log file matches what the user would see on a legacy terminal.
- If UTF-8: The log file contains Unicode that may not render in the user's text editor (Notepad on CP1251/CP1252 cannot display `✓`).
- **Severity:** Medium. Redirected output is stored for later review; mojibake in stored files is harder to notice.
- **Mitigation:** Complicated — would need to detect redirection and choose differently, adding more non-determinism.

### 7.4 Tests passing locally but failing in another shell

**Scenario:** A developer writes a test that asserts output contains `→` (U+2192). On their Windows Terminal, auto-detection switches to UTF-8 and the test passes. On a teammate's legacy cmd.exe, auto-detection stays ASCII-safe and the test fails because the output contains `->` instead of `→`.

- **Severity:** High for developer productivity. Non-reproducible test failures erode trust in the test suite.
- **Mitigation:** All tests would need to explicitly set the output mode (as they do today with `--utf8` or the default). But if auto-detection is the default behavior, every test must opt out of it, adding boilerplate and mental overhead.

---

## 8. Compatibility Risks

### 8.1 Breaking the ASCII-safe default

Any form of auto-detection that switches to UTF-8 mode based on environment signals breaks the ASCII-safe default guarantee. The default is "safe on all Windows terminals." A detection that occasionally chooses UTF-8 means the default is no longer safe on all terminals — it is "safe on most terminals, except when detection is wrong."

This is a **regression from v2.9 behavior.** The ASCII-safe default is a guarantee; replacing it with a probabilistic heuristic is a step backward.

### 8.2 Inconsistent CLI output snapshots

The OOS CLI output is documented, tested, and relied upon by automated tooling. If the same command produces different output depending on which terminal it runs in, all documentation, test fixtures, and automation scripts that capture output become environment-dependent. This violates the OOS principle of deterministic-first behavior.

### 8.3 Confusing test expectations

If auto-detection exists, every test must either:
- Mock the detection function (adding boilerplate and hiding the detection from test coverage), or
- Accept environment-dependent output (making tests non-deterministic).

Neither option is desirable. The current system — explicit `--utf8` flag — makes test expectations trivial: without `--utf8`, output is ASCII; with `--utf8`, output contains Unicode markers. No mocking, no environment dependency.

### 8.4 Non-deterministic behavior across environments

This is the core reproducibility risk. Two developers running the same OOS commit on different machines would see different output. Two CI runs on different agents could produce different artifacts. Bug reports become "what terminal are you using?" instead of "what version of the code?"

### 8.5 Accidental Unicode output in CP1251/CP1252 terminals

If auto-detection incorrectly identifies a CP1251/CP1252 terminal as UTF-8-capable, the user sees garbled characters where readable ASCII should be. For status markers like `✓ [PASS]`, the Unicode checkmark becomes mojibake, making the output less informative than the ASCII `OK` or `[PASS]` would have been. This is strictly worse than staying in ASCII-safe mode.

---

## 9. Options Considered

### 9.1 Option A: Keep explicit `--utf8` only (current approach)

- **Description:** No auto-detection. The user controls output mode via `--utf8`. Default is always ASCII-safe.
- **Pros:**
  - Fully deterministic.
  - Safe on all Windows terminals.
  - Test expectations are trivial.
  - No platform-specific code.
  - No new dependencies.
  - No reproducibility risks.
  - No false positives, no false negatives.
- **Cons:**
  - User must remember to type `--utf8`.
  - New users on UTF-8-capable terminals see ASCII symbols by default (minor cosmetic issue).
  - Power users may find the extra flag annoying if they always want UTF-8.
- **Configurability:** The flag can be placed in a shell alias or wrapper script.

### 9.2 Option B: Auto-detect and switch to UTF-8

- **Description:** On startup (or per-command), probe the environment and switch to UTF-8 mode if the terminal appears capable.
- **Pros:**
  - Zero-config UTF-8 for users on modern terminals.
  - "It just works" experience for Windows Terminal and VS Code users.
- **Cons:**
  - Non-deterministic.
  - False positives cause mojibake (worse than ASCII default).
  - False negatives deny UTF-8 where it could work (acceptable, but confusing).
  - Introduces platform-specific code (`ctypes`, subprocess, env var parsing).
  - Tests need mocking or become environment-dependent.
  - Breaks the ASCII-safe default guarantee.
  - Redirected stdout and CI environments need special handling.
- **Verdict:** NOT recommended for v2.10.

### 9.3 Option C: Auto-detect only as advisory warning

- **Description:** Detect encoding but do NOT switch output mode. Instead, print an advisory message: "Your terminal appears to support UTF-8. Use --utf8 for Unicode symbols." or "Your terminal may not render Unicode. Output is ASCII-safe. Use --utf8 to try UTF-8 mode."
- **Pros:**
  - Does not change output mode (ASCII-safe default preserved).
  - Helps users discover `--utf8`.
  - Zero risk of mojibake from wrong detection.
  - Can be implemented as a non-blocking warning without affecting test expectations.
- **Cons:**
  - Still introduces platform-specific detection code.
  - Advisory messages clutter output.
  - Detection code needs maintenance.
  - Redirected stdout and CI need special handling.
- **Verdict:** NOT recommended for v2.10. This is a potential v2.11+ feature if founder feedback indicates users are unaware of `--utf8`.

### 9.4 Option D: Add explicit `--ascii` override

- **Description:** Keep current `--utf8` flag. Add an explicit `--ascii` flag that forces ASCII-safe mode even if some future auto-detection would choose UTF-8. This is a forward-compatibility flag that prepares for potential auto-detection in v2.11+.
- **Pros:**
  - No behavior change in v2.10 (both flags are explicit).
  - Provides an escape hatch if auto-detection is added later.
  - Clarifies the CLI interface: `--ascii` and `--utf8` are symmetric.
  - Backward-compatible (default remains ASCII-safe).
- **Cons:**
  - Adds a flag that does nothing new in v2.10.
  - Slight CLI surface bloat.
  - `--ascii` is already the default, so the flag is redundant unless auto-detection exists.
- **Verdict:** Consider for v2.11+ only if auto-detection is implemented. Not needed in v2.10.

### 9.5 Option E: Environment variable override

- **Description:** Support an `OOS_OUTPUT_MODE` environment variable that can be set to `ascii_safe` or `utf8`. If set, it overrides the CLI flag. If not set, behavior is unchanged.
- **Pros:**
  - Persistent configuration without typing `--utf8` every time.
  - Works in CI and automated scripts.
  - Deterministic (env var is explicit, not detected).
  - Low implementation cost.
- **Cons:**
  - Introduces a second input channel for output mode (env var + CLI flag).
  - Priority rules must be documented and tested.
  - Environment variables are easy to forget about (silent override).
  - Not needed in v2.10 if auto-detection is not implemented.
- **Verdict:** Consider for v2.11+ as a separate roadmap item. Not needed in v2.10.

---

## 10. Recommendation

**Recommendation: Do not implement automatic encoding-based switching in v2.10.**

The audit finds that:

1. **No detection method is reliable and deterministic across all supported Windows configurations.** The gap between "encoding reported" and "glyphs rendered" cannot be closed without font probing, which is impractical.

2. **The ASCII-safe default is guaranteed safe on all terminals.** Auto-detection would replace this guarantee with a probabilistic heuristic. The risk of false positives (detecting UTF-8 when the terminal cannot render it) produces output that is WORSE than ASCII-safe output — mojibake instead of readable text.

3. **The `--utf8` flag is unambiguous, idempotent, and puts the founder in control.** It requires no detection code, no platform-specific dependencies, no mocking in tests, and no environment-dependent behavior.

4. **Concrete user feedback requesting auto-detection has not been received.** The v2.9 output mode contract deferred detection to v2.10+ "justified by concrete user feedback." No such feedback has been documented.

**Specific recommendation:**
- Keep ASCII-safe default and explicit `--utf8` opt-in unchanged for v2.10.
- Optionally allow future advisory-only diagnostics or explicit environment override (`OOS_OUTPUT_MODE`) in v2.11+, but only after separate approval in a new roadmap item.
- If `OOS_OUTPUT_MODE` is ever implemented, it must be explicit (the user sets it) and not auto-detected.

---

## 11. Future Implementation Constraints, If Ever Approved

If automatic terminal encoding detection is ever implemented in a future roadmap (v2.11+), the following constraints must be satisfied:

### 11.1 Fail closed to ASCII-safe on uncertainty

Any detection heuristic that is not 100% certain must default to ASCII-safe mode. The detection logic must have a three-state output:
- **Known-UTF-8:** Detection is confident the terminal can render UTF-8 (e.g., `WT_SESSION` is set AND `sys.stdout.encoding == 'utf-8'`).
- **Known-legacy:** Detection is confident the terminal is legacy CP1251/CP1252 (e.g., `sys.stdout.encoding in ('cp1251', 'cp1252')` AND no `WT_SESSION`, no `TERM_PROGRAM`).
- **Uncertain:** Any other case. **Default: ASCII-safe.**

The "uncertain" path must be the default; detection must only switch to UTF-8 when there is strong, positive evidence.

### 11.2 Never silently switch output mode in tests unless explicitly requested

Test fixtures must not be affected by environment auto-detection. All tests that assert on output content must explicitly control the output mode. This means either:
- Tests pass `--utf8` or omit it (as today), and auto-detection is disabled during testing, OR
- Tests set an environment variable (`OOS_TEST_OUTPUT_MODE=ascii_safe` or similar) that overrides detection.

### 11.3 Keep `--utf8` as explicit override

`--utf8` must always force UTF-8 mode, regardless of detection result. The founder's explicit flag always wins.

### 11.4 Consider `--ascii` override

If auto-detection exists, there must be a way to force ASCII-safe mode without relying on detection. An `--ascii` flag (or the absence of `--utf8` when detection is uncertain) fulfills this.

### 11.5 Document behavior for redirected stdout

When stdout is redirected (pipe or file), auto-detection must produce the same output mode as interactive use, or document the difference. If redirected output is always ASCII-safe, this must be explicitly stated in the CLI help text ("Output is ASCII-safe when redirected. Use --utf8 to force Unicode symbols in file output.")

### 11.6 Test CP1251/CP1252/CP65001 scenarios using deterministic mocks, not live shell mutation

Unit tests for auto-detection must not modify the test runner's console code page. Detection functions must accept injectable encoding sources (e.g., a `get_encoding` callable) so tests can supply known values. Live `chcp` or `SetConsoleOutputCP()` calls in tests are prohibited.

### 11.7 No dependency on `chcp` in unit tests

Parsing `chcp` output requires spawning a subprocess and handling localized output strings. Unit tests must not depend on `chcp` being available or producing English output. Use `GetConsoleOutputCP()` via `ctypes` if console code page detection is needed at all.

### 11.8 Detection logic must be a standalone module

Auto-detection logic must live in its own module (e.g., `src/oos/terminal_encoding.py`) with a single public function: `detect_output_mode(override: str | None = None) -> str`. This function returns `'ascii_safe'` or `'utf8'`. The `override` parameter allows tests to inject a specific mode. No other module may contain encoding detection logic.

---

## 12. Non-Goals

This policy document explicitly does NOT:

- Modify any source code (`src/`).
- Implement automatic terminal encoding behavior.
- Change the default output mode (remains ASCII-safe).
- Expand `--utf8` to more CLI commands (that is item 7.1).
- Change existing CLI output snapshots.
- Modify tests (`tests/`) or scripts (`scripts/`).
- Make live API or LLM calls.
- Authorize any future implementation — future work requires a separate roadmap item and explicit approval.

---

## 13. Decision

**v2.10 does not implement terminal encoding auto-detection.**

The decision is:

1. **Default remains ASCII-safe.** The output mode decision tree is unchanged: `--utf8 present? → utf8 | otherwise → ascii_safe`.

2. **UTF-8 remains explicit opt-in through `--utf8`.** No environment variable, configuration file, or auto-detection changes output mode.

3. **No detection code is introduced.** No `sys.stdout.encoding` probes, no `chcp` calls, no `GetConsoleOutputCP()` calls, no environment variable parsing for encoding detection.

4. **Future work requires a separate roadmap item and explicit approval.** Any form of auto-detection, advisory warning, or environment variable override must be proposed as a distinct roadmap item with its own audit, risk analysis, and approval process.

---

## 14. Validation

### 14.1 Expected validation for this item

- **Docs-only change.** Only `docs/decisions/terminal_encoding_auto_detection_policy.md` (new file) and `docs/roadmaps/OOS_roadmap_v2_10_recovery_correction_checklist.md` (update) are modified.
- **No source/test/script changes.** `git diff --stat` must show zero changes to `src/`, `tests/`, `scripts/`.
- **`.\scripts\dev-git-check.ps1` passes.** All 6/6 checks.
- **`git status --short` clean after commit.** Working tree clean.

### 14.2 ASCII-safe default verification

The ASCII-safe default is unchanged by this policy document. All existing tests that verify ASCII-safe output (Section 6.1 of the output mode contract) continue to pass unchanged. No new ASCII-safety regressions are introduced.

### 14.3 Safety Gate D conformance

This policy document satisfies Safety Gate D:

| Condition | Status |
|---|---|
| Item 6 produces an audit/policy document only | **Satisfied** — This document is the deliverable |
| No `sys.stdout.encoding` probes introduced | **Satisfied** — No source code changes |
| No `chcp` checks introduced | **Satisfied** — No source code changes |
| No `GetConsoleOutputCP()` calls introduced | **Satisfied** — No source code changes |
| Output mode decision tree unchanged | **Satisfied** — `--utf8 present? → utf8 | NO → ascii_safe` remains |
