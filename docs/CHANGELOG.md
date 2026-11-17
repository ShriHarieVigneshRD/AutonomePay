# Changelog

All changes on branch `refactor/restructure-and-improve` (from `457f2fb`, 2026-11-17). Bug and security ids (B…, S…) refer to [ANALYSIS.md](ANALYSIS.md); features (F…, N…) to [ANALYSIS.md](ANALYSIS.md) and [PLAN.md](PLAN.md).

## Benchmark rebuilt (2026-11-17, after the web policy ingest)
- **Removed 31 cases:** 24 exact repeats (same merchant and script, only the invoice amount changed), and 7 of 9 identical single-turn "payment failed" cases.
- **Added 31 cases:** 13 grounded in the fetched public pages (Netflix, Spotify, Slack, Jira, RazorpayX) and in unexercised policy rules, plus 18 guardrail and conversation edge cases. The full catalogue is in [BENCHMARK.md](BENCHMARK.md).
- **Scoring:** cases can now also pin the approved amount and a policy passage that must be retrieved on some turn. Each turn's sources are recorded in the trace and shown in the trace drawer.
- **Data validation:** `tests/test_benchmark_cases.py` rejects repeats, invalid actions, missing policy sources and amounts the guardrail wouldn't approve.
- **Fixed while building the cases:** triage missed "a cheaper *payroll* plan"; the offline engine ignored the plan the customer named; downgrade wording ("the Basic plan"); the case browser's Adversarial filter missed new injection types.
- **Renamed** two scenario types whose titles didn't match their dialogues: `NETFLIX_CONCESSION_REQUEST`, `SLACK_RENEWAL_DISCOUNT`.
- **PostgreSQL:** `evaluation_runs.expected_action` widened from VARCHAR(40) to 255. On PostgreSQL, 33 of the 50 labels would have failed to save; SQLite doesn't enforce lengths. The upgrade from the original schema is verified on PostgreSQL, and a test now checks case values against column lengths.
- **Token budget:** the default per-conversation budget is now 20,000 (live turns use ~1–2k tokens). `render.yaml` takes `DATABASE_URL` from a dashboard secret instead of a hard-coded SQLite path.
- **Existing databases:** new cases use new customer/invoice ids (`…_cNN`), which are seeded automatically. Rows from the old cases stay in the database but are no longer used.

## Added
- **N1. Real MCP payments.** `app/payments/mcp_server.py` exposes `create_payment_link` and `fetch_payment_link` (Razorpay-shaped results). It uses the live Razorpay API with real keys, or a DB-backed sandbox. The agent calls it through an MCP client: `embedded` in-process, `remote` (Razorpay's hosted server with Basic auth) or `stdio`.
- **N2. Web-sourced policies.** `python -m app.rag.ingest` fetches each merchant's public pages, respecting robots.txt. It extracts the main text, screens it for prompt injection, and saves dated snapshots with the source URL. 9 pages for 6 merchants are committed.
- **N3. Retrieval v2.** Heading-aware chunking with metadata; BM25 + `bge-small-en-v1.5` embeddings fused with reciprocal-rank fusion; `ms-marco-MiniLM-L-6-v2` reranker (fastembed/ONNX, no PyTorch); citations (`retrieved_sources`) shown under replies and in the audit trail. A generated "enforced limits" chunk per merchant keeps retrieved text in sync with the guardrail.
- **N4. Retrieval evaluation.** 56 labelled queries and `python -m app.evals.retrieval_eval` (hit@1/3, MRR). hybrid_rerank: hit@1 0.893, MRR 0.931, versus 0.804 / 0.879 for BM25.
- **N5. Benchmark scoring.** Each case has an expected outcome (acceptable actions, link or no link); runs store `passed`; there is a pass-rate KPI; LangSmith URLs are real or absent.
- **N6. Server-side conversations.** `/api/conversations` endpoints. The server owns the history, the token budget is per conversation, failed turns are never stored, and conversations restore from the URL.
- **N7. Payment status loop.** `GET /api/payments/{id}` (status over MCP) and sandbox `simulate-payment`. Invoices become recovered or partially recovered. There is a `/pay/:id` sandbox checkout, and slips have "Check status" with refresh on tab focus.
- **Merchant catalogue.** `data/merchants.json` is the single source of merchant limits, plans, split/partial rules, demo invoices and public sources. New `merchant_plans` table and split/partial columns; `payment_links`, `conversations` and `conversation_messages` tables; measured-result columns on `evaluation_runs`. All additive, applied automatically on startup.
- **Offline policy engine.** Merchant-aware replies when no LLM is configured or a reply is unusable: discounts, grace (capped at the requested days), downgrades to listed plans, instalments, undisputed portions, escalation, cancellation.
- **UI.** Settlement slip, bounds meters, verdict stamps, numbered audit trail, case browser dialog, suggested replies, shareable case/conversation URLs, statement strip, case ledger, light/dark themes, and phone/tablet/desktop layouts.
- **Tooling.**
  - Backend: pytest suites (129 tests), ruff, pyright.
  - Frontend: ESLint 9, Prettier, Vitest + Testing Library (18 tests), Playwright (16 e2e tests across three widths and two themes).
  - Pinned `requirements*.txt`, `.gitattributes` (LF), `CLAUDE.md`, and `.interface-design/system.md`.

## Changed
- **Structure.** The backend is split into `api/`, `agents/settlement/`, `guardrails/`, `payments/`, `rag/`, `evals/`, `core/` and `data/`. The frontend uses `features/`, `hooks/`, `components/ui/` and `lib/`. Old → new mapping is in PLAN.md §1.
- **Config.** pydantic-settings only; new settings for CORS, admin token, rate limit, MCP mode, RAG mode, model cache and customer notifications.
- **Default LLM chain:** Nemotron 3 Ultra → Gemma 4 31B → Nemotron 3.5 Super → `openrouter/free`. MiniMax M3/M2.7 are no longer free on OpenRouter.
- **Benchmark data.** Generated cases use real plan prices; single-turn cases are spread across merchants.
- **Visual design.** The neon dark dashboard became a "settlement desk ledger" system: paper/ink tokens, one ink-blue accent, status colours validated for colour-vision deficiency.
- **`render.yaml`.** Uses `runtime:`, `RAG_MODE=bm25` for the 512 MB free tier, and the new env vars.
- **Intentional behaviour changes** (see TEST_REPORT §5): the link amount is always the approved amount; every link needs explicit consent; unknown ids return 404; `GET /evals/batches` never starts a run; with no LLM key, no network call is made.

## Fixed
- **B1** The payment link could be issued for any amount written in the LLM's message, bypassing the guardrail.
- **B2** "Plan downgrade" let any price through (e.g. ₹1).
- **B3** RAG returned nothing for 14 of 15 merchants (merchant-id regex).
- **B4** 47 of 50 scenarios negotiated against a phantom ₹299 invoice.
- **B5** Policy-approved splits and partial settlements were flagged as breaches.
- **B6** The token budget was shared per scenario across all users and never reset.
- **B7** UI limits disagreed with enforced limits for 8 merchants.
- **B8** The response cache never hit (random ticket id in the prompt) and stored failures.
- **B9** Live Razorpay failures returned a fake link; sandbox links had about 2 random characters.
- **B10** Malformed LLM offers caused 500s.
- **B11** A GET request ran the full benchmark synchronously.
- **B12** Final step missing for offers; "Outcome" always showed `RAG_RETRIEVED`.
- **B13** Invented KPIs (latency constant, invoiced = recovered × 1.05, "(0 Breaches)").
- **B14 / B15** Benchmark polling didn't resume, followed the wrong run, and never stopped on errors.
- **B16** Error text was added to the conversation history.
- **B17** Guardrail checklist always showed "Passed".
- **B18** Unknown batch returned 200.
- **B19** Constant token spend; latency measured only one node.
- **B20** Token budget default 4000 vs 6000.
- **B21** Missing favicon (404 on every load).
- **B22** Non-existent Tailwind classes.
- **B23** Rotating placeholder with stale effect dependencies.
- **B24** `npm run lint` was broken.
- **B25** Triage labelled any "failed" message as a gateway failure.
- **B26** "My payment failed" counted as consent to pay ("pay" matched inside "payment").
- **B27** URLs written by the LLM reached customers and suppressed the real link.
- **B28** Airtel, Slack and RazorpayX benchmark cases were always single-turn, so escalation was never exercised.
- **B29** Embedding the corpus in one large batch grew ONNX Runtime memory to ~2 GB.
- **Found in the live run:**
  - Free-model JSON with raw newlines or an unclosed string fell back to the heuristic; the parser now tolerates it.
  - When link creation failed, the reply contradicted an LLM message that promised the link.
- **Regression vs the original:** leaving the sandbox for the benchmark lost the conversation.
- **Mobile:** the header overflowed and the panels were clipped. Tablet: the results table was too wide.

## Security
- **S1** Benchmark runs are guarded: one at a time (409), optional `ADMIN_TOKEN`. Per-IP chat rate limit.
- **S2** CORS origins come from config; no credentials.
- **S3** Request schema allows only `user`/`assistant` roles, length limits, and a last message from the customer. Server-side conversations remove client-supplied history entirely.
- **S4** Broader injection patterns, screened over every customer turn. Web snapshots are screened at ingest; retrieved text is wrapped as reference data in the prompt.
- **S5** Customers are never notified unless `RAZORPAY_NOTIFY_CUSTOMERS=true`. The seeded demo phone numbers could belong to real people.
- **S6** Internal errors return a reference id instead of exception text.

## Removed
- `agents/customer_proxy_agent.py`: dead code, never imported. The dataset's scripted dialogues do this job.
- `run_all_50_evaluations()`: never called.
- `RazorpayMCPClient.razorpay_fetch_subscription_status` / `razorpay_fetch_payment_status`: never called, and they returned hard-coded mock data. Payment-link status is now available through the MCP `fetch_payment_link` tool (N7).
- Hard-coded `MERCHANT_METADATA` and `MERCHANT_HUMAN_NAMES`, replaced by `merchants.json`.
- The canned "5% concession, ₹279" fallback reply for every merchant, replaced by the merchant-aware policy engine.
- Unused npm packages `framer-motion`, `lucide-react`, `clsx` and `tailwind-merge`; the unused `Outfit` font; the unused `langchain-core` pin (comes with langgraph).
- `artifacts/` and `.agents/SKILLS.md`, moved (not deleted) to `docs/archive/`.

## Known limitations
See [TEST_REPORT.md §8](TEST_REPORT.md#8-known-limitations). The headline items:
- A successful live Razorpay link wasn't verified, because the test account hit the 30-link limit.
- Only `bm25` fits Render's 512 MB free tier.
- 7 merchants have no fetchable public policy pages.
- Spotify's live prices differ from the curated plan prices and need a human review.
