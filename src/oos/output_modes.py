"""Output mode helper — deterministic symbol selection for terminal-facing output.

Roadmap v2.9 item 1.2. Provides:
- OutputMode constants (ascii_safe, utf8)
- validate_output_mode(mode)
- get_output_symbols(mode) -> dict

ASCII-safe default is mandatory. UTF-8 is explicit opt-in via --utf8.
No automatic terminal encoding detection.
No business logic, correction semantics, or source URL behavior changes.
"""

from __future__ import annotations

_VALID_MODES = frozenset({"ascii_safe", "utf8"})


def validate_output_mode(mode: str) -> str:
    """Validate and normalize an output mode string.

    Args:
        mode: One of 'ascii_safe' or 'utf8'.

    Returns:
        The validated mode string (unchanged).

    Raises:
        ValueError: If *mode* is not a recognized output mode.
    """
    if mode not in _VALID_MODES:
        raise ValueError(
            f"Unknown output mode {mode!r}. "
            f"Expected one of: {', '.join(sorted(_VALID_MODES))}"
        )
    return mode


def get_output_symbols(mode: str) -> dict[str, str]:
    """Return a dict of canonical symbols for the given output mode.

    Keys:
        success, failure, warning, none, arrow, dash, corrected

    ASCII-safe mode uses only characters with ord(c) < 128.
    UTF-8 mode uses Unicode symbols for visual clarity.

    Args:
        mode: 'ascii_safe' or 'utf8'.

    Returns:
        Dict mapping semantic keys to symbol strings.

    Raises:
        ValueError: If *mode* is not recognized.
    """
    mode = validate_output_mode(mode)

    if mode == "ascii_safe":
        return {
            "success": "OK",
            "failure": "FAIL",
            "warning": "WARN",
            "none": "NONE",
            "arrow": "->",
            "dash": "-",
            "corrected": "[CORRECTED]",
        }

    # utf8
    return {
        "success": "\u2713",       # ✓
        "failure": "\u2717",       # ✗
        "warning": "\u26a0",       # ⚠
        "none": "NONE",
        "arrow": "\u2192",         # →
        "dash": "\u2014",          # —
        "corrected": "[CORRECTED]",
    }
