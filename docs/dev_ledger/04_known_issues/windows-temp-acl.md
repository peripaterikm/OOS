# Known Issue: Windows Temp ACL Warnings

## Summary

Local `git status` can report permission denied warnings under `.test-tmp/` and `.tmp_tests/`.

## Current Understanding

These are known local ACL artifacts from temporary test directories on Windows. They are not part of Roadmap v2.2 product behavior.

## Handling

- Do not stage or commit `.test-tmp/` or `.tmp_tests/`.
- Ignore these warnings unless a current mini-epic explicitly targets temp cleanup.
- Keep validation focused on source, docs, and tests.

