# Known Issue: Codex Sandbox TemporaryDirectory Friction

## Summary

Some tests using Python `TemporaryDirectory()` can fail inside the Codex sandbox with Windows permission errors.

## Current Understanding

The same tests pass when rerun with normal Windows filesystem access. This is sandbox friction, not necessarily application failure.

## Handling

- First run tests normally when practical.
- If a failure is clearly sandbox ACL related, rerun the same validation command outside the sandbox with approval.
- Report both the initial friction and the final validation result.

