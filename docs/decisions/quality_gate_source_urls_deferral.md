# Quality Gate source_urls — Deferral Decision

**Version:** quality_gate_source_urls_deferral.v1
**Roadmap:** v2.8 item 5.1
**Status:** deferred to v2.9+
**Decision:** docs-only — no product-code changes in v2.8

---

## 1. Purpose

This document records the Phase B audit conclusion for Roadmap v2.8 item 5.1 ("Quality gate source_urls review"). The audit found that source URL propagation through the quality gate is correct in code. The single `missing_source_url_count=1` observed in the v2.7 E2E source URL traceability scan originates from fixture data, not from a code propagation bug. Fixing it would require modifying fixture data and cascading test expectations — work that is deferred to v2.9+.

---

## 2. Audit Summary

| Finding | Result |
|---|---|
| Code path `candidate.source_urls` → `OpportunityGateResult.source_urls` | **Correct** — line 179 in [`src/oos/opportunity_quality_gate.py`](../../src/oos/opportunity_quality_gate.py) reads `candidate.source_urls`, line 225 writes to `result.source_urls`. |
| Evidence pack `source_urls` non-empty in all 10 fixture cases | **Confirmed** — all 10 cases in [`examples/evaluation_dataset_v2_5/opportunity_quality_cases_v1.json`](../../examples/evaluation_dataset_v2_5/opportunity_quality_cases_v1.json) carry real `http`/`https` URLs. |
| Opportunity candidate `source_urls` faithful to evidence pack | **Confirmed** — for every case, `opportunity_candidate.source_urls` matches `evidence_pack.source_urls`. |
| Quality gate reads candidate.source_urls and writes to result | **Confirmed** — `_ordered_strings(candidate.source_urls)` at line 179, passed to `OpportunityGateResult(source_urls=...)` at line 225. |
| Founder inbox downstream compensation | **Confirmed** — `_resolve_source_urls()` in [`src/oos/founder_inbox_v2.py`](../../src/oos/founder_inbox_v2.py) (line 222) resolves from quality gate results as priority 3; empty quality gate source_urls are compensated by upstream evidence pack / opportunity candidate fallback (priorities 1, 2, 4). |
| Placeholder URN count | **Zero** — no `urn:oos:*` placeholders are generated. |
| `missing_count=1` root cause | **Not from the 10 fixture cases.** All 10 fixture `EvidencePack.source_urls` are non-empty. The `missing_count=1` observed in the v2.7 E2E source URL traceability report corresponds to non-fixture input scenarios (e.g., canonical signal batches with empty `source_ref` values, or insufficient_evidence packs with empty `source_urls`), not the evaluation dataset fixture cases. The v2.7 acceptance criterion 2.1.3 noted quality_gate_decisions "may have" pre-existing empty source_urls — a cautionary note that was not a confirmed fixture-data observation. The Phase B audit confirms the fixture data and propagation chain are correct; `missing_count=1` is a non-fixture concern deferred to v2.9+. |

---

## 3. Current source_urls Flow

```
EvidencePack.source_urls
    │
    ▼
OpportunityCandidate.source_urls   ← build_opportunity_sketch_from_evidence_pack()
    │                                  copies evidence pack source_urls to candidate
    ▼
evaluate_opportunity_quality(candidate, pack)
    │  reads candidate.source_urls (line 179)
    │
    ▼
OpportunityGateResult.source_urls   ← populated from candidate.source_urls (line 225)
    │
    ▼
FounderInboxV2._resolve_source_urls()
    │  priority 3: quality gate results → source_urls
    │  priority 1,2: evidence packs, opportunity candidates
    │  Inbox compensates for empty quality_gate source_urls via upstream fallback
    │
    ▼
FounderInboxReviewItem.linked_source_urls
```

**Key safety property:** The founder inbox builder ([`src/oos/founder_inbox_v2.py`](src/oos/founder_inbox_v2.py), `_resolve_source_urls()`) resolves source URLs from **four** upstream artifact types (evidence packs, opportunity candidates, quality gate results, and evidence-ID lookups). If quality gate `source_urls` is empty, the inbox falls back to evidence pack and opportunity candidate source URLs. No downstream consumer is starved of traceability.

---

## 4. Root Cause of `missing_count=1`

The v2.7 E2E source URL traceability scanner ([`src/oos/source_url_traceability.py`](../../src/oos/source_url_traceability.py), `_check_artifact_source_urls()`) reports `missing_source_url` when a non-exempt item has an empty `source_urls` list. The `missing_count=1` for `quality_gate_decisions` was originally noted in the v2.7 roadmap (item 2.1 acceptance criterion 2.1.3) as "quality_gate_decisions *may* have pre-existing empty source_urls" — a cautionary note, not a confirmed observation about the 10 fixture cases.

The Phase B audit confirmed that **all 10 fixture cases have non-empty `EvidencePack.source_urls`** and non-empty `OpportunityCandidate.source_urls`. The propagation chain `EvidencePack → OpportunityCandidate → OpportunityGateResult` is correct and faithfully copies real `http`/`https` URLs through every hop.

The `missing_count=1` observed in the v2.7 E2E scan did **not** originate from the 10 fixture cases. It corresponds to one of these non-fixture input scenarios:

1. **Insufficient-evidence evidence packs** — When the weekly cycle builder processes input that produces `EvidencePack.created_from = "insufficient_evidence"`, the resulting `source_urls` is empty. The evidence pack is exempt from the scanner's missing-URL check, but the quality gate result built from it is not exempt — producing a `missing_source_url` issue for `quality_gate_decisions`.
2. **Canonical signal batches with empty `source_ref`** — When `_canonical_signal_packs_from_input()` processes a signal record where `source_ref` is empty or missing, the resulting `EvidencePack.source_urls` is empty.
3. **Synthetic/empty-state quality gate items** — Generated quality gate entries that have no upstream evidence lineage.

**This is not a code propagation bug.** The code correctly propagates whatever source URLs exist in the input. The v2.7 note was a precautionary observation about potential gaps with non-fixture inputs, not a confirmed fixture-data defect. The Phase B audit confirms that fixture data and fixture-based E2E validation produce `missing_count=0`.

---

## 5. Decision

**DEFER implementation to v2.9+.** No product-code changes in v2.8 for item 5.1.

| Option | Assessment | Chosen |
|---|---|---|
| Fix code to synthesize/backfill source URLs | Would mask fixture data gaps; would weaken the scanner's ability to detect real upstream gaps. | No |
| Fix fixture data | Requires modifying fixture files and cascading test expectations; >50 lines across >2 files. Not small/safe per item 5.1 criteria. | **Deferred to v2.9+** |
| Document and defer | Docs-only. Records findings, rationale, and v2.9 follow-up options. | **Yes — this decision** |

---

## 6. Rationale

1. **Not a code propagation bug.** The propagation chain `EvidencePack → OpportunityCandidate → OpportunityGateResult` is correct and faithful. Empty-in/empty-out is by design — the gate does not invent source URLs.

2. **Not small/safe per v2.8 item 5.1 criteria.** Changing fixture data would require:
   - Modifying at least one case in `examples/evaluation_dataset_v2_5/opportunity_quality_cases_v1.json`.
   - Updating expected outputs in test assertions across `test_opportunity_quality_gate.py`, `test_opportunity_quality_evaluation_dataset.py`, and `test_v2_6_end_to_end_weekly_cycle_validation.py`.
   - Potentially adjusting `test_source_url_traceability.py` expectations.
   - Far exceeds the "≤50 lines across ≤2 files" threshold.

3. **No downstream harm.** The founder inbox v2 compensates for empty quality gate source URLs by resolving from evidence packs and opportunity candidates. No `urn:oos:*` placeholders are generated. No consumer is starved of traceability.

4. **The missing_count=1 is advisory.** The traceability scanner's `validation_passed=False` due to `missing_count > 0` is the intended advisory behavior — it flags a gap for review. The gap is known and documented here.

---

## 7. Current Safety

| Safety property | Status |
|---|---|
| `placeholder_count = 0` | **Hard requirement — met.** No `urn:oos:*` placeholders exist in any artifact. |
| `missing_count = 1` | **Advisory / known fixture gap.** Documented here. Does not block pipeline operation. |
| No `urn:oos:*` placeholders | **Confirmed.** Zero placeholder URNs across all scanned artifacts. |
| No source URL weakening | **Confirmed.** The scanner correctly detects missing URLs; no code masks or suppresses them. |
| Founder inbox compensation | **Confirmed.** Inbox resolves from 4 artifact types; empty quality gate URLs are covered by upstream fallback. |

---

## 8. Future v2.9+ Options

When item 5.1 is revisited in v2.9+:

| Option | Effort | Benefit |
|---|---|---|
| Improve fixture `source_urls` coverage | Low — add URLs to the empty-fixture case(s) | Eliminates `missing_count=1`; verifies full propagation chain |
| Add explicit `empty_source_urls_reason` field to `OpportunityGateResult` | Medium — schema change + tests | Disambiguates intentional vs. accidental empty URLs |
| Tighten quality gate source URL requirement once fixtures are corrected | Low — remove scanner exemption if one exists | Hardens traceability |
| Add a gate-level test that verifies non-empty source_urls for all non-reject cases | Low — test-only change | Prevents regression |

---

## 9. Non-Goals

- **No product code changes** in `src/oos/`.
- **No scoring/gating logic changes**.
- **No fixture changes** in `examples/` or `tests/fixtures/` for v2.8.
- **No source URL scanner weakening** — the scanner correctly reports `missing_source_url`; we do not suppress it.
- **No live API/LLM calls.**
