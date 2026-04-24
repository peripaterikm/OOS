# Evaluation Dataset v0 - Expected Clusters

Dataset v0 is a smoke-test fixture, not a clustering implementation contract.

Expected semantic directions:

1. Workflow exception handling
   - Signals: `eval_v0_sig_001`, `eval_v0_sig_002`, `eval_v0_sig_003`, `eval_v0_sig_004`, `eval_v0_sig_005`, `eval_v0_sig_014`
   - Pattern: operational owners maintain side spreadsheets or checklists when normal systems fail on edge cases.

2. Compliance and evidence collection
   - Signals: `eval_v0_sig_006`, `eval_v0_sig_007`, `eval_v0_sig_015`
   - Pattern: coordinators chase recurring proof, answers, or documents across email and portals.

Additional direction to watch:

- External portal monitoring: `eval_v0_sig_008`, `eval_v0_sig_009`, `eval_v0_sig_010`

Edge cases:

- Ambiguous: `eval_v0_sig_011`, `eval_v0_sig_012`
- Near duplicate: `eval_v0_sig_002` near-duplicates `eval_v0_sig_001`
- Weak/noisy: `eval_v0_sig_013`
- Unclear buyer or pain: `eval_v0_sig_011`, `eval_v0_sig_012`
