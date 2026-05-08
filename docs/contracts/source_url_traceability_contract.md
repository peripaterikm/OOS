# Source URL Traceability Contract

**Version:** source_url_traceability.v1
**Roadmap:** v2.7 item 1.1
**Status:** contract / advisory only
**Schema:** `SourceURLTraceabilityReport` in [`src/oos/source_url_traceability.py`](../../src/oos/source_url_traceability.py)

---

## 1. Why Source URL Traceability Matters

Every artifact in the OOS weekly loop originates from upstream signals. Each signal has a `source_url` pointing to a real HN post, GitHub issue, or other source. When the pipeline builds evidence packs, opportunity candidates, quality gates, founder inbox items, founder decisions, and feedback mappings, the source URLs must propagate faithfully through every hop.

If a placeholder URN like `urn:oos:founder_import:placeholder` replaces a real URL, two things break:

1. **Trust.** The founder cannot verify that a decision is grounded in real evidence.
2. **Auditability.** Future runs (and Codex reviewers) cannot trace a claim back to its origin.

Source URL traceability is the backbone of the advisory-only contract: the system recommends, the founder decides, and every recommendation must be traceable to a real, inspectable source.

---

## 2. Current Known v2.6 Gap

The v2.6 founder decision import ([`src/oos/founder_decision_import.py`](../../src/oos/founder_decision_import.py), line 517–518) falls back to `urn:oos:founder_import:placeholder` when no source URLs are collected from the inbox:

```python
if not source_urls:
    source_urls = ["urn:oos:founder_import:placeholder"]
```

This placeholder leaks into:

- `FounderDecisionV2.linked_source_urls`
- `FounderFeedbackMapping.source_urls`
- `FounderFeedbackMapping.target.source_urls`
- All downstream artifacts that read founder decisions or feedback mappings.

**Root cause:** The v2.6 `FounderInboxReviewItem` does not carry `linked_source_urls`, so the decision import cannot collect real URLs from the inbox index. This is a propagation gap, not a data absence — upstream artifacts (evidence packs, opportunity candidates) already carry real source URLs.

**Fix:** v2.7 items 1.2 (add `linked_source_urls` to FounderInboxReviewItem) and 1.3 (remove placeholder fallback in decision import) will close this gap. Item 1.1 defines the contract that items 1.2–1.3 must satisfy.

---

## 3. Canonical Source URL Traceability Path

```
CandidateSignal.source_url
  → EvidencePack.source_urls
    → OpportunityCandidate.source_urls
      → OpportunityGateResult.source_urls
        → FounderInboxReviewItem.linked_source_urls   ← missing in v2.6 (added in 1.2)
          → FounderDecisionV2.linked_source_urls        ← currently gets placeholder (fixed in 1.3)
            → FounderFeedbackMapping.source_urls       ← inherits placeholder (fixed in 1.3)
```

Every arrow represents a propagation step. A URL must survive each hop without being dropped, substituted, or replaced by a placeholder.

---

## 4. Expected Fields by Artifact / Model

| Artifact Key | File | Model | Field | Cardinality |
|---|---|---|---|---|
| `evidence_packs` | `evidence_packs.json` | `EvidencePack` | `.source_urls` | At least 1 real URL unless `created_from = "insufficient_evidence"` |
| `opportunity_candidates` | `opportunity_candidates.json` | `OpportunityCandidate` | `.source_urls` | At least 1 real URL |
| `quality_gate_decisions` | `quality_gate_decisions.json` | `OpportunityGateResult` | `.source_urls` | At least 1 real URL |
| `founder_inbox_v2_index` | `founder_inbox_v2_index.json` | `FounderInboxReviewItem` | `.linked_source_urls` | At least 1 real URL (to be implemented in v2.7 item 1.2) |
| `founder_decisions_v2` | `founder_decisions_v2.json` | `FounderDecisionV2` | `.linked_source_urls` | At least 1 real URL (currently may contain placeholder; to be fixed in v2.7 item 1.3) |
| `founder_feedback_mappings` | `founder_feedback_mappings.json` | `FounderFeedbackMapping` | `.source_urls` | At least 1 real URL (currently may contain placeholder; to be fixed in v2.7 item 1.3) |

---

## 5. Placeholder URN Policy

**Definition:** A placeholder URN is any string matching the regex `^urn:oos:` (case-insensitive).

**Policy:**
- Placeholder URNs are **treated as missing traceability**.
- Every placeholder URN is a **blocker issue** (`severity: error`).
- `validation_passed = false` if any placeholder URN is found.
- Placeholder URNs must be replaced with real source URLs propagated from upstream artifacts.

**Examples of placeholder URNs:**
- `urn:oos:founder_import:placeholder`
- `urn:oos:anything`
- `urn:oos:some.namespace:id`

**Examples of acceptable source URLs:**
- `https://news.ycombinator.com/item?id=12345`
- `https://github.com/owner/repo/issues/42`
- `http://example.com/page`

---

## 6. Missing URL Policy

**Definition:** A missing source URL is an empty `source_urls` / `linked_source_urls` list on an artifact item that is **not** exempt.

**Policy:**
- Items with empty `source_urls` (where URLs are expected) produce a **blocker issue** (`issue_type: missing_source_url`, `severity: error`).
- `validation_passed = false` if any non-exempt item has missing source URLs.
- Synthetic items (e.g., next-best actions with no evidence lineage) should have an explicit note rather than a missing URL error — handled in downstream item logic.

---

## 7. Insufficient-Evidence Exemption

**Definition:** An `EvidencePack` is insufficient evidence when `created_from == "insufficient_evidence"`.

**Policy:**
- Insufficient-evidence evidence packs are **exempt** from the missing-source-URL check.
- They are also **exempt** from placeholder detection (since they legitimately have no source URLs).
- Other artifact types do not currently have an insufficient-evidence exemption. The exemption is scoped strictly to evidence packs.

---

## 8. Malformed URL Policy

**Definition:** A malformed URL is an `http://` or `https://` string with no actual hostname (e.g., `"http://"`, `"https:"`).

**Policy:**
- Malformed URLs produce a **warning** (`issue_type: malformed_source_url`, `severity: warning`).
- Malformed URLs do **not** block `validation_passed`.
- They are advisory only: the founder should review and correct them.

---

## 9. What Items 1.2, 1.3, and 2.1 Will Do Next

| Item | Scope | Depends on |
|---|---|---|
| **1.2** | Add `linked_source_urls` to `FounderInboxReviewItem`; populate from evidence packs and opportunity candidates in inbox builder | 1.1 (this contract) |
| **1.3** | Remove `urn:oos:founder_import:placeholder` fallback; propagate real URLs from inbox index into founder decisions and feedback mappings | 1.2 |
| **2.1** | End-to-end source URL traceability gate in weekly cycle validation; run this contract as part of the standard validation pass | 1.1, 1.2, 1.3 |

---

## 10. Non-Goals for Item 1.1

- This item does **not** modify source URL propagation in any pipeline module.
- This item does **not** add `linked_source_urls` to `FounderInboxReviewItem`.
- This item does **not** change `FounderDecisionImport` behavior.
- This item does **not** change `FounderFeedbackMapping` validation.
- This item does **not** change the weekly cycle builder or E2E validation.
- This item does **not** write artifacts to a real `artifacts/` directory.
- This item does **not** call live APIs or LLMs.
- This item is **contract/advisory only**: it defines the spec and provides a validation scanner, but does not enforce anything autonomously.

---

## 11. Scanner Usage

```python
from oos.source_url_traceability import (
    check_source_url_traceability,
    source_url_traceability_to_json,
)

report = check_source_url_traceability("artifacts/weekly_runs/weekly_run_2026-01-01_abc123")
print(source_url_traceability_to_json(report))
print(f"Issues: {report.issue_count}")
print(f"Placeholders: {report.placeholder_url_count}")
print(f"Passed: {report.validation_passed}")
```

Or from shell:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -c "
from oos.source_url_traceability import check_source_url_traceability, source_url_traceability_to_json
report = check_source_url_traceability('artifacts/weekly_runs/some_run_id')
print(source_url_traceability_to_json(report))
"
```
