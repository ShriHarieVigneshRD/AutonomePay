# Test Report

**Branch:** `refactor/restructure-and-improve`
**Date:** 2026-11-17
**Environment:** Windows 11, Python 3.11.15, Node 24.17, Chrome (Playwright `channel: chrome`).

## 1. Summary

| Check | Command | Result |
|---|---|---|
| Backend lint | `ruff check app tests` | ✅ clean |
| Backend format | `ruff format --check app tests` | ✅ 71 files formatted |
| Backend types | `pyright` (basic) | ✅ 0 errors (8 at the start of Phase 4) |
| Backend tests | `pytest` | ✅ **167 passed** (+1 `slow` model test, also passing with `-m slow`) in ~5 s |
| Frontend lint | `npm run lint` (ESLint, `--max-warnings 0`) | ✅ clean (was broken: B24) |
| Frontend format | `npm run format:check` | ✅ clean |
| Frontend unit | `npm test` (Vitest) | ✅ **19 passed** |
| Frontend build | `npm run build` | ✅ 314 kB JS / 97 kB gzip |
| End-to-end | `npm run test:e2e` (Playwright) | ✅ **16 passed** in ~50 s (desktop 1440, tablet 820, mobile 390; light + dark) |
| Retrieval quality | `python -m app.evals.retrieval_eval` | ✅ see §4 |
| Live run | real OpenRouter + Razorpay test keys | ✅ with findings, see §6 |

All automated suites run **offline**:
- Tests override every key from `backend/.env`.
- The e2e backend uses a temp SQLite DB, mock Razorpay, no LLM key and BM25 retrieval.
- LLM calls are stubbed where a test needs a specific model reply.

## 2. Phase 3 baseline (before any change)

| Suite | Result |
|---|---|
| Backend characterisation | 40 passed, 20 known bugs as strict xfails |
| E2E smoke | 5 passed (desktop only; mobile/tablet were known broken) |

Every strict xfail now passes as a regression test (`tests/test_regressions.py`). No characterisation test was deleted. Assertions changed only where behaviour changed on purpose (listed in §5).

## 3. Feature walkthrough (ANALYSIS.md F1–F31)

| # | Feature | Status | Evidence |
|---|---|---|---|
| F1 | Health endpoint | ✅ | `test_f1_root_health` |
| F2 | 50 scenarios with metadata and greeting | ✅ (+ merchant `policy`, real amounts) | `test_f2_scenarios_catalogue`, `test_b4_every_scenario_can_be_chatted`, `test_b7_*` |
| F3 | Chat turn through the graph | ✅ (+ `/api/conversations`) | `test_f3_*`, `test_conversations.py` |
| F4 | Input guard | ✅ (all user turns, broader patterns) | `test_f4_*`, `test_s4_*`, e2e "prompt injection is blocked" |
| F5 | Offer guard: discount / grace / split sum | ✅ (+ plans, splits, partials, over-invoice) | `test_f5_*`, `test_b2_*`, `test_b5_*` |
| F6 | Plan downgrade | ✅ (must match a listed plan) | `test_f6_*`, `test_b2_*` |
| F7 | Link amount matches the message | ✅ changed by design: link = approved amount; mismatched text is replaced | `test_b1_*` |
| F8 | Link deferral | ✅ (explicit consent on every turn) | `test_f8_*`, `test_b26_*` |
| F9 | Human escalation | ✅ (real ticket id) | `test_f9_*`, `test_escalation_quotes_a_real_ticket` |
| F10 | Graceful discontinuation | ✅ | `test_f10_*` |
| F11 | Razorpay payment link | ✅ via MCP (sandbox verified; live failure path verified, §6) | `test_f11_*`, `test_mcp_payments.py`, e2e "consent issues a payment link" |
| F12 | Gateway: fallback chain, cache, budget | ✅ (per-conversation budget, no cached failures) | `test_f12_*`, `test_b6_*`, `test_b8_*` |
| F13 | Heuristic when the LLM is unusable | ✅ (merchant-aware; grace requests) | `test_f13_*`, `test_offline_grace_*` |
| F14 | Markdown clean-up | ✅ (+ LLM-written URLs removed) | `test_f14_*`, `test_b27_*` |
| F15 | Per-merchant RAG | ✅ (all 15 merchants; hybrid + rerank) | `test_f15_*`, `test_b3_*`, `test_retrieval.py` |
| F16 | DB bootstrap and seed | ✅ (catalogue sync, 50 invoices) | `test_f16_seed_data`, `test_b4_*` |
| F17 | Start a benchmark run | ✅ (409 while running; optional admin token) | `test_f17_f18_*`, `test_s1_*` |
| F18 | List runs | ✅ (no hidden auto-run) | `test_f18_*`, `test_b11_*` |
| F19 | Results and KPIs | ✅ (measured, 404 for unknown) | `test_f19_*`, `test_b13_*`, `test_b18_*` |
| F20 | Runner and scoring | ✅ (+ pass/fail per case) | `test_n5_*`, `test_b28_*` |
| F21 | LangSmith dataset sync | ✅ local mode | `test_f21_*` |
| F22 | LangSmith tracing | ⚠️ not exercised (no LangSmith key) | code path unchanged; trace URLs are now real or absent |
| F23 | PostgreSQL support | ⚠️ not exercised | SQLAlchemy models and additive DDL are portable; only SQLite was run |
| F24 | Header and navigation | ✅ (routes `/`, `/benchmark`, `/pay/:id`) | e2e flows; responsive "controls on screen" check |
| F25 | Scenario picker | ✅ (native dialog, keyboard, filters) | e2e "case browser search", `ScenarioPicker.test.js` |
| F26 | Case file | ✅ (every policy bound) | e2e "first case loads" |
| F27 | Chat UI | ✅ (slips, suggestions, retry, persistence) | e2e flows, `useConversation.test.js` |
| F28 | Trace inspector → audit trail | ✅ (real checks, citations) | e2e "policy-bound offer…" |
| F29 | Benchmark dashboard | ✅ (statement strip, ledger, table) | e2e "benchmark runs…", `useBenchmark.test.js` |
| F30 | Trace drawer | ✅ (native dialog, Escape) | e2e "opens a trace" |
| F31 | Deploy config | ✅ build passes; `render.yaml` updated | not deployed from here |

### New features (N1–N7)
| # | Evidence |
|---|---|
| N1 MCP payments | `test_mcp_payments.py`: tool discovery over MCP, create/fetch round trip, error handling, ledger, official-server result normalisation |
| N2 Web-sourced policies | `test_retrieval.py` ingest tests (robots, JS-only pages, injected instructions, snapshot format). A real ingest run saved 9 pages for 6 merchants. |
| N3 Hybrid retrieval and citations | `test_retrieval.py` (chunking, fusion, citations via API), slow test `test_dense_retrieval_beats_keywords` |
| N4 Retrieval eval | 56 labelled queries, BM25 quality floor test (§4) |
| N5 Benchmark scoring | `test_n5_*`; the offline policy engine passes 50/50 |
| N6 Server conversations | `test_conversations.py` (7 tests), hook tests, e2e "survives a page reload" |
| N7 Payment status | `test_payment_status.py`, e2e "paying a sandbox link in another tab shows as paid" |

### Responsive and accessibility checks (automated)
- **Widths:** 390 / 820 / 1440 px in light and dark. No sideways scrolling, and every visible control stays on screen (this check caught a clipped mobile header and an over-wide table, both fixed). Navigation, case picker and composer are always reachable. On phones, the Case and Audit panes are one tap away.
- **Browser console:** no errors during any flow.
- **Contrast:** text tokens computed at ≥ 4.5:1 in both themes. Status colours validated with the dataviz `validate_palette.js` script (CVD separation and lightness) in both modes.
- **Keyboard and screen-reader semantics:** native `<button>`, `<a>`, `<dialog>` and `<details>`; tabs use `role="tablist"` with arrow keys; the chat log has `aria-live`; labels on all inputs.

## 3a. Benchmark cases (rebuilt after the web policy ingest)
- 50 distinct cases ([BENCHMARK.md](BENCHMARK.md)): 19 kept and 31 new; 24 exact repeats and 7 redundant single-turn cases were removed.
- Scoring checks the final action and link, plus (where set) the exact approved amount and a policy passage retrieved on any turn. 23 cases cite a policy passage; 7 of them are public-page snapshots.
- `tests/test_benchmark_cases.py` validates the dataset itself (no repeats, real actions, sources present in the corpus, amounts the guardrail approves).
- Offline (deterministic policy engine): **50/50 with `bm25`** and **50/50 with `hybrid_rerank`**.
  - The first `hybrid_rerank` run scored 49/50. Case 31 exposed a triage gap ("cheaper payroll plan" wasn't seen as a downgrade request, so retrieval missed the pricing page); fixed.
- Not run against the live LLM in this session; that run is what makes the pass rate a measure of the model.

## 4. Retrieval quality (N4)

`python -m app.evals.retrieval_eval`: 56 labelled customer questions across all 15 merchants.

| Mode | hit@1 | hit@3 | MRR@10 |
|---|---|---|---|
| bm25 | 0.804 | 0.929 | 0.879 |
| hybrid (BM25 + bge-small embeddings, RRF) | 0.893 | 0.946 | 0.927 |
| **hybrid_rerank** (+ MiniLM-L-6 cross-encoder) | **0.893** | **0.946** | **0.931** |

**Reranker comparison:**

| Reranker | hit@1 | hit@3 | MRR@10 |
|---|---|---|---|
| MiniLM-L-6 (chosen) | 0.893 | 0.946 | 0.931 |
| MiniLM-L-12 | 0.893 | 0.964 | 0.936 |
| jina-tiny | 0.821 | 0.946 | 0.894 |

Dense embeddings deliver most of the gain. The reranker adds little on a corpus this small; L-12 is marginally better at twice the compute.

The original retriever matched only 1 of 15 merchants (B3), so its effective quality on this set was far lower than any row above.

## 5. Intentional behaviour changes
- **Payment-link amount** is always the guardrail-approved amount. A message stating any other amount is replaced (F7, B1).
- **Links need explicit customer consent** on every turn, matched on whole words ("payment" no longer counts as "pay").
- **Unknown or mismatched merchant/customer/invoice ids** return 404 instead of a phantom ₹299 bill (B4).
- **`/api/chat`** rejects `system` roles and histories that don't end with the customer (S3). `/api/conversations` is the recommended API.
- **`GET /api/evals/batches`** never starts a run (B11). Starting a run while one is running returns 409.
- **With no LLM key** the gateway makes no network calls and the merchant-aware policy heuristic answers. The old canned "5% concession" reply is gone.
- **Sandbox payment links** point at the app's own `/pay/<id>` checkout instead of fake `rzp.io` URLs (B9).
- **The 46 generated benchmark cases** use real plan prices instead of `150 + 200·i`, and the single-turn cases are spread across merchants (B28).
- **Merchant names and limits** come from `backend/app/data/merchants.json`, synced to the DB on startup.

## 6. Live run (real OpenRouter key and Razorpay test keys, temp DB)
- **Real LLM path works end to end.** Netflix: 2-day grace offer, then a downgrade to Basic ₹199. Notion: 50/50 split at ₹7,500. QuickKart: undisputed 80% at ₹68,000. RazorpayX: escalated with a ticket. Injection: blocked before the LLM. Every verdict was within bounds.
- **Found and fixed:** Nemotron 3 Ultra (free) sometimes returns JSON with raw newlines and an unclosed final string. These replies previously fell back to the heuristic; the parser now tolerates them (`tests/test_llm_parsing.py`). After the fix, 0 unparseable replies.
- **Found:** `minimax/minimax-m3:free` and `minimax-m2.7:free` (the first two models in the configured chain) are no longer free on OpenRouter (HTTP 404). Defaults are updated. **Your `backend/.env` still lists them**; see the README to update.
- **Found:** the Razorpay test account has hit its **30 payment-link test-mode limit**. Live link creation therefore failed, and the app correctly reported `LINK_FAILED` with no fake link and a restated offer. A successful live link was *not* verified in this session.

## 7. Memory (server working set, Windows)

| RAG_MODE | Memory | Retrieval cost per turn |
|---|---|---|
| bm25 | ~290 MB | ~10 ms |
| hybrid | ~555 MB | small |
| hybrid_rerank | ~700 MB | ~200 ms |

- **B29:** embedding the corpus in fastembed's default batch of 256 inflated ONNX Runtime's memory arena to ~2 GB. Batches of 8 keep it bounded.
- **Render free (512 MB):** use `RAG_MODE=bm25` (set in `render.yaml`). The hybrid modes need roughly 1 GB.

## 8. Known limitations
1. **Live Razorpay success path** is not verified (test-mode link limit). The remote and stdio MCP modes against Razorpay's official server are unit-tested for result shapes only, not connected to.
2. **The live 50-case benchmark** with a real LLM was not run; it would create ~36 test links and hit free-model rate limits. Offline it scores 100% by construction (deterministic policy engine).
3. **Coverage:** 7 of 15 merchants have no web snapshot. Notion, Zoho, Swiggy and Zomato disallow crawling in robots.txt; Hotstar, Amazon and Airtel render with JavaScript.
4. **Stale config to review:** Spotify's live pricing page (₹139 Standard, ₹299 Platinum) differs from the plan prices in `merchants.json`. Spotify's policy text says "no flat discounts" while its limit allows ₹15. Neither was changed automatically.
5. **Independent labels:** the retrieval labels were written alongside the system, not by an independent annotator.
6. **Single instance only:** rate limiting and the token-budget/cache state are in-process.
7. **Persistence on Render:** SQLite on Render's disk is reset on redeploy. Set `DATABASE_URL` to PostgreSQL for persistence (not exercised here).
8. **Accessibility** checks are automated (roles, labels, contrast, keyboard paths). No manual screen-reader session was run.
9. **No CI workflow** is configured; all commands above were run locally.
