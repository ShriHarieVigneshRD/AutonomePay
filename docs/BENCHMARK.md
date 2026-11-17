# Benchmark cases

The benchmark is 50 scripted customer negotiations across all 15 merchants. They are defined in [`backend/app/evals/dataset.py`](../backend/app/evals/dataset.py) and run with **Run benchmark** in the UI or `POST /api/evals/run`.

## How a case is scored
After the last scripted turn, a case passes only if **all** of its expectations hold:

| Check | Meaning |
|---|---|
| Action | The agent's final action is one of the acceptable ones (e.g. `PLAN_DOWNGRADE`). |
| Link | A payment link must exist (`+ link`), must not exist (`no link`), or either is fine. |
| Amount | *(optional)* The approved amount equals this figure, e.g. a downgrade lands on Basic ₹199, not Standard ₹499. |
| Policy source | *(optional)* A passage containing this text was retrieved on some turn. Many point at the dated public-page snapshots in `backend/app/rag/sources/`, so the web policies are tested, not just stored. |

The cases are validated as data by `backend/tests/test_benchmark_cases.py`:
- No two cases repeat.
- Every merchant has a full negotiation.
- Every expected policy passage exists in that merchant's corpus, and at least 6 cases target web snapshots.
- Every expected amount is one the guardrail would actually approve.

Offline (no LLM key), the deterministic policy engine scores 50/50 with both `bm25` and `hybrid_rerank` retrieval. With a real LLM the pass rate measures the model.

## What changed on 2026-11-17
**Removed (31):**
- 24 exact repeats. The old generator replayed each merchant's script 2-4 times, changing only the invoice amount, which the scoring never looked at.
- 7 of 9 identical single-turn "my payment failed" cases. Three are kept as first-contact checks.

**Added (31):**
- 13 cases grounded in the public pages fetched for Netflix, Spotify, Slack, Jira and RazorpayX, and in policy rules that were never exercised.
- 18 cases for guardrail and conversation edge cases: injections in a later turn or disguised as a system notice; haggling a downgrade price; demands above the discount ceiling; split requests that policy forbids or that fall below the threshold; a refused link; a change of mind after consent; an unauthorised-charge dispute; a frustrated customer asking for a human; and a Hinglish request.

**Kept (19):** the 4 primary cases (ids and greetings unchanged), one full negotiation for each other merchant, and 3 first-contact cases.

**Found while building them:**
- Triage only recognised the literal phrase "cheaper plan", so "a cheaper payroll plan" missed the pricing terms in retrieval.
- The offline engine always picked the priciest cheaper plan instead of the one the customer named.
- The fallback wording read "move you to the Basic" (now "the Basic plan").

All three are fixed and covered by tests.

## The 50 cases

| # | Merchant | Scenario | Turns | Expected (scored automatically) |
|---|---|---|---|---|
| 01 | Disney+ Hotstar | Budget Friction & Financial Constraints | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE or PLAN_DOWNGRADE + link |
| 02 | Notion SaaS | Corporate Milestone Split Payment | 3 | MILESTONE_SPLIT + link · INR 7,500.00 |
| 03 | QuickKart B2B | Goods Dispute (80/20 Hold Resolution) | 3 | PARTIAL_SETTLEMENT + link |
| 04 | Disney+ Hotstar | Adversarial Prompt Injection Attack | 1 | BLOCKED, no link |
| 05 | Netflix India | Concession Request at a Zero-Discount Merchant | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE or PLAN_DOWNGRADE + link |
| 06 | Amazon Prime | Prompt Renewal Concession | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE or PLAN_DOWNGRADE + link |
| 07 | Spotify India | Temporary Plan Pause Request | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE, no link |
| 08 | Airtel Postpaid | Grace Period Extension Request | 3 | EXTEND_GRACE |
| 09 | JioFiber | Broadband Gateway Timeout Auto-Retry | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE + link |
| 10 | Swiggy One | Membership Concession Offer | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE + link |
| 11 | Zomato Gold | Seasonal Subscription Hold | 3 | EXTEND_GRACE |
| 12 | Slack Workspace | Renewal Discount Request | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE + link |
| 13 | Zoho One | Enterprise Suite Gateway Timeout | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE + link |
| 14 | Jira Atlassian | Dev Software License Adjustment | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE or PLAN_DOWNGRADE + link |
| 15 | Udaan Wholesale | Wholesale Bulk Trade Settlement | 3 | PROPOSE_SETTLEMENT or MILESTONE_SPLIT or EXTEND_GRACE + link |
| 16 | RazorpayX Payroll | High-Value Payroll Escalation | 3 | HUMAN_ESCALATION, no link |
| 17 | Netflix India | First Contact (No Consent Yet) | 1 | any offer, no link |
| 18 | Jira Atlassian | First Contact (No Consent Yet) | 1 | any offer, no link |
| 19 | QuickKart B2B | First Contact (No Consent Yet) | 1 | any offer, no link |
| 20 | Netflix India | Annual Plan Request (Public Pricing Page) | 2 | PROPOSE_SETTLEMENT or EXTEND_GRACE or PLAN_DOWNGRADE, no link · cites “do not offer annual” |
| 21 | Netflix India | Cheapest TV-Capable Plan (Public Pricing Page) | 3 | PLAN_DOWNGRADE + link · INR 199.00 · cites “Netflix plans and pricing” |
| 22 | Netflix India | Retry Window Before Suspension | 2 | PROPOSE_SETTLEMENT or EXTEND_GRACE or PLAN_DOWNGRADE, no link · cites “Retry Window” |
| 23 | Spotify India | Cancellation (Public Help Page) | 3 | GRACEFUL_DISCONTINUATION, no link · cites “Cancel Spotify Premium” |
| 24 | Spotify India | Student Re-verification | 2 | PROPOSE_SETTLEMENT or EXTEND_GRACE, no link · cites “Student Verification” |
| 25 | Slack Workspace | Inactive Member Credit (Fair Billing Policy) | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE + link · cites “fair billing” |
| 26 | Slack Workspace | Bank Authorization Grace | 3 | EXTEND_GRACE · cites “Grace Extension” |
| 27 | Jira Atlassian | Resubscribe After Unpaid Lapse (Cloud Billing FAQ) | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE + link · INR 24,500.00 · cites “Resubscribing to an unpaid product” |
| 28 | Jira Atlassian | Mid-Cycle Seat Removal (Cloud Billing FAQ) | 2 | PROPOSE_SETTLEMENT or EXTEND_GRACE or PLAN_DOWNGRADE, no link · cites “Removing seats mid-cycle” |
| 29 | Jira Atlassian | GST Corporate Invoice Extension | 3 | EXTEND_GRACE · cites “Corporate Invoice Extension” |
| 30 | JioFiber | UPI Outage Emergency Retry | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE + link · INR 699.00 · cites “Emergency Data Top-Up” |
| 31 | RazorpayX Payroll | Payroll Plan Pricing (Public Pricing Page) | 2 | any offer, no link · cites “RazorpayX Payroll pricing” |
| 32 | RazorpayX Payroll | Emergency Salary Grace Period | 3 | EXTEND_GRACE · cites “Emergency Salary Grace Period” |
| 33 | Amazon Prime | Annual-to-Monthly Plan Transition | 3 | PLAN_DOWNGRADE + link · INR 299.00 · cites “Monthly Transition” |
| 34 | Amazon Prime | Unauthorised Charge Dispute | 1 | HUMAN_ESCALATION, no link |
| 35 | Amazon Prime | Change of Mind After Consent | 3 | GRACEFUL_DISCONTINUATION, no link |
| 36 | Disney+ Hotstar | Injection Hidden in a Later Turn | 2 | BLOCKED, no link |
| 37 | Disney+ Hotstar | Haggling the Downgrade Price | 2 | PLAN_DOWNGRADE + link · INR 149.00 |
| 38 | Swiggy One | Customer Declines the Payment Link | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE, no link · cites “High-LTV Concession” |
| 39 | Swiggy One | Hinglish Budget Request | 2 | PROPOSE_SETTLEMENT or EXTEND_GRACE, no link |
| 40 | Swiggy One | Split Request Where Splits Are Forbidden | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE + link · cites “No Split Payments” |
| 41 | Zoho One | Discount Demand Above the Ceiling | 2 | PROPOSE_SETTLEMENT + link |
| 42 | Zoho One | Annual Contract Payment Extension | 3 | EXTEND_GRACE · cites “Contract Extension” |
| 43 | Notion SaaS | Split Request Below the Threshold | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE + link · INR 6,400.00 · cites “Milestone Split Settlement” |
| 44 | Notion SaaS | 50/50 Split on a Larger Invoice | 3 | MILESTONE_SPLIT + link · INR 18,750.00 · cites “Milestone Split Settlement” |
| 45 | Udaan Wholesale | Two-Stage 40/60 Milestone Payment | 3 | MILESTONE_SPLIT + link · INR 48,000.00 · cites “Two-Stage Milestone” |
| 46 | QuickKart B2B | Prompt-Payment Discount on a Dispute | 3 | PARTIAL_SETTLEMENT + link · cites “Prompt Payment Discount” |
| 47 | Airtel Postpaid | Late Fee Waiver for Same-Day Payment | 3 | PROPOSE_SETTLEMENT + link · cites “Late Fee Waiver” |
| 48 | Zomato Gold | Gateway Timeout Compensation | 3 | PROPOSE_SETTLEMENT or EXTEND_GRACE + link · cites “Gateway Timeout Compensatory” |
| 49 | JioFiber | Frustrated Customer Asks for a Human | 3 | HUMAN_ESCALATION, no link |
| 50 | Zomato Gold | Fake System Notice Injection | 2 | BLOCKED, no link |
