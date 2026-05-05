# Founder Manual Labels - First Real Open-Source Signal Run v1

- Run ID: `first_real_open_source_signal_run_v1`
- Review entries: `18`
- Purpose: tracked founder-review ground truth for v2.5 source-quality hardening.

| # | Evidence | Source | Original | Founder Label | Action | Tags | Rationale |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | `raw_github_issue_3565323722` | `github_issues` | `needs_human_review` / `0.2` | `vendor_promo` | `suppress_in_future` | `vendor_promo`, `seo_noise`, `source_quality_issue` | Promotional accounting software copy; no concrete user pain. |
| 2 | `raw_github_issue_1182773055` | `github_issues` | `pain_signal_candidate` / `0.58` | `useful` | `promote_to_opportunity_seed` | `real_smb_pain`, `finance_reporting` | Concrete reporting need; clear evidence of desired balance-sheet functionality. |
| 3 | `raw_github_issue_4369704245` | `github_issues` | `workaround_signal_candidate` / `0.58` | `vendor_promo` | `suppress_in_future` | `vendor_promo`, `seo_noise`, `source_quality_issue` | Vendor marketing copy; not a user pain or organic workaround. |
| 4 | `raw_github_issue_385700413` | `github_issues` | `needs_human_review` / `0.19` | `vendor_promo` | `suppress_in_future` | `vendor_promo`, `seo_noise`, `generic_accounting_copy`, `source_quality_issue` | Generic promotional/SEO content; no concrete user pain. |
| 5 | `raw_github_issue_4072093883` | `github_issues` | `pain_signal_candidate` / `0.74` | `weak` | `park_for_more_evidence` | `weak_buyer_evidence`, `generic_accounting_copy`, `source_quality_issue` | Phrase resembles a real pain, but source/content appears vendor/consulting-adjacent and lacks concrete user context. |
| 6 | `raw_github_issue_194268452` | `github_issues` | `pain_signal_candidate` / `0.49` | `price_false_positive` | `use_for_price_hardening` | `price_false_positive`, `vendor_promo`, `seo_noise`, `mojibake`, `source_quality_issue` | $75 is a receipt threshold, not current spend or willingness-to-pay; content appears marketing-like and includes mojibake. |
| 7 | `raw_github_issue_4058309053` | `github_issues` | `pain_signal_candidate` / `0.35` | `weak` | `suppress_in_future` | `generic_accounting_copy`, `vendor_promo`, `source_quality_issue` | Generic accounting copy; no concrete user problem, buyer, or workaround. |
| 8 | `raw_github_issue_4103786450` | `github_issues` | `needs_human_review` / `0.28` | `vendor_promo` | `suppress_in_future` | `product_submission`, `vendor_promo`, `weak_price_evidence`, `source_quality_issue` | Product listing/submission, not evidence of user pain. |
| 9 | `raw_hn_47844178` | `hacker_news_algolia` | `workaround_signal_candidate` / `0.26` | `weak` | `keep_as_context` | `bookkeeping_workaround`, `weak_buyer_evidence` | Organic workaround context; useful but not strong enough as a standalone opportunity seed. |
| 10 | `raw_hn_47401563` | `hacker_news_algolia` | `workaround_signal_candidate` / `0.45` | `weak` | `keep_as_context` | `bookkeeping_workaround`, `weak_buyer_evidence` | Market/competitor context; less direct pain evidence. |
| 11 | `raw_hn_47082761` | `hacker_news_algolia` | `pain_signal_candidate` / `0.75` | `useful` | `promote_to_opportunity_seed` | `real_smb_pain`, `cash_collection`, `bookkeeping_workaround` | Strongest signal; concrete small-business pain, clear manual workaround, direct finance/cash-collection relevance. |
| 12 | `raw_hn_46725518` | `hacker_news_algolia` | `workaround_signal_candidate` / `0.24` | `price_false_positive` | `use_for_price_hardening` | `price_false_positive`, `affordability_pain`, `bookkeeping_workaround`, `weak_price_evidence` | Useful affordability/workaround context, but $1.25M tax/deduction limit must not be extracted as spend. |
| 13 | `raw_hn_44581530` | `hacker_news_algolia` | `needs_human_review` / `0.1` | `noise` | `suppress_in_future` | `generic_accounting_copy` | Broad macro prediction, not SMB finance pain. |
| 14 | `raw_hn_47844178` | `hacker_news_algolia` | `workaround_signal_candidate` / `0.26` | `duplicate` | `mark_duplicate` | `duplicate_signal`, `bookkeeping_workaround` | Duplicate occurrence of raw_hn_47844178. |
| 15 | `raw_hn_47401563` | `hacker_news_algolia` | `workaround_signal_candidate` / `0.45` | `duplicate` | `mark_duplicate` | `duplicate_signal`, `bookkeeping_workaround` | Duplicate occurrence of raw_hn_47401563. |
| 16 | `raw_hn_47009152` | `hacker_news_algolia` | `pain_signal_candidate` / `0.29` | `useful` | `promote_to_opportunity_seed` | `real_smb_pain`, `bookkeeping_workaround`, `affordability_pain` | Real SMB pain; current workaround and affordability barrier are explicit. Original system score may be too low. |
| 17 | `raw_hn_46864767` | `hacker_news_algolia` | `needs_human_review` / `0.13` | `vendor_promo` | `suppress_in_future` | `vendor_promo`, `generic_accounting_copy` | Solution marketing copy, not user pain. |
| 18 | `raw_hn_46430957` | `hacker_news_algolia` | `needs_human_review` / `0.13` | `needs_more_evidence` | `park_for_more_evidence` | `needs_human_review`, `weak_buyer_evidence` | Interesting discovery meta-signal, but not direct finance/SMB pain. |

## Duplicate Groups

- `dup_raw_hn_47844178`: review entries `09` and `14`.
- `dup_raw_hn_47401563`: review entries `10` and `15`.

## Notes

- These labels are tracked examples/ground-truth artifacts, not runtime artifacts.
- Runtime discovery artifacts under `artifacts/` were read locally but not modified.
- No additional live collection, live internet/API call, or live LLM/API call was performed.
