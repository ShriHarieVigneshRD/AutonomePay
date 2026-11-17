# AutonomePay: Phase 2 Plan

*Based on [ANALYSIS.md](ANALYSIS.md). Bug ids (B1…), security ids (S1…) and feature ids (F1…) refer to that document. New-feature ids are N1…*

**Decisions already made (2026-11-17)**
- `artifacts/` and `.agents/SKILLS.md` move to `docs/archive/`.
- The Razorpay integration becomes a real MCP integration (N1).
- The UI is redesigned using the design direction in §3.
- The project is extended with web-sourced policies, better retrieval and a reranker (N2–N4).

**Needs your OK (plain-English versions are in the chat reply)**
- **D1. Seed data:** add the 47 missing scenario bills and customers so every scenario uses its real amount, and show merchant limits from the database. This only adds rows.
- **D2. New tables/columns:** to store each merchant's plans, prices and split rules so the safety check stops letting ₹1 "downgrades" through and stops blocking real 50/50 splits (B2, B5). Existing data is untouched and the app upgrades the DB automatically on start.
- **D3. New dependencies:** listed with reasons in §2.6.

---

## 1. Target folder structure

```
AutonomePay/
├── README.md, CLAUDE.md, render.yaml
├── docs/
│   ├── ANALYSIS.md, PLAN.md, TEST_REPORT.md, CHANGELOG.md
│   └── archive/                     # previous agent's prompt/plan/task/walkthrough + SKILLS.md
├── backend/
│   ├── pyproject.toml               # ruff, pytest, pyright config
│   ├── requirements.in / requirements.txt (pinned) / requirements-dev.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py                  # app factory, lifespan, CORS from env, logging
│   │   ├── api/
│   │   │   ├── chat.py  scenarios.py  evals.py  conversations.py (N6)
│   │   │   ├── schemas.py           # request/response models
│   │   │   └── deps.py              # db session, admin-token check
│   │   ├── core/
│   │   │   ├── config.py            # pydantic-settings only
│   │   │   ├── database.py          # engine, session, models
│   │   │   ├── migrations.py        # explicit "add missing column/table" checks (no silent excepts)
│   │   │   ├── seed.py              # loads data/merchants.json into DB
│   │   │   └── llm_gateway.py
│   │   ├── data/
│   │   │   └── merchants.json       # single source of truth: merchant, limits, plans, split rules, policy source URLs, demo customer + invoice
│   │   ├── agents/
│   │   │   ├── graph.py  state.py  triage.py  retrieval.py
│   │   │   └── settlement/
│   │   │       ├── node.py          # orchestration only
│   │   │       ├── prompt.py
│   │   │       └── offer.py         # parse LLM JSON → validated offer, heuristic fallback, message/amount reconciliation
│   │   ├── guardrails/
│   │   │   ├── input_guard.py       # was pre_guardrails.py
│   │   │   └── offer_guard.py       # was post_guardrails.py
│   │   ├── payments/                # N1: real MCP
│   │   │   ├── mcp_server.py        # our MCP server: Razorpay tools (live SDK or sandbox simulator)
│   │   │   └── mcp_client.py        # agent-side MCP client: in-process / stdio / remote Razorpay MCP
│   │   ├── rag/
│   │   │   ├── chunking.py  retriever.py  reranker.py
│   │   │   ├── ingest.py            # N2: CLI to fetch + snapshot public policy pages
│   │   │   ├── policies/            # curated internal settlement rules (was documents/)
│   │   │   └── sources/             # web snapshots: <merchant>/<page>.md with url + fetched_at header
│   │   └── evals/
│   │       ├── dataset.py  runner.py  judge.py  langsmith_sync.py
│   │       └── retrieval_eval.py    # N4
│   └── tests/
│       ├── conftest.py              # temp DB, stubbed LLM, sandbox MCP
│       ├── unit/  integration/
│       └── fixtures/retrieval_qrels.json
└── frontend/
    ├── eslint.config.js, .prettierrc, vitest.config.js, playwright.config.js
    ├── public/favicon.svg
    ├── e2e/                         # Playwright: flows + 390/820/1440 screenshots
    └── src/
        ├── main.jsx  App.jsx
        ├── styles/tokens.css        # design tokens (light + dark)
        ├── lib/api.js  lib/format.js  lib/theme.js
        ├── hooks/useScenarios.js  useConversation.js  useEvalRuns.js
        ├── components/ui/           # Button, Stamp, Panel, Disclosure, Dialog, Skeleton, EmptyState, ErrorState, Segmented, Amount
        └── features/
            ├── sandbox/             # ScenarioPicker, CaseFile, ChatPanel, SettlementSlip, BoundsMeter, AuditRail
            └── benchmark/           # StatementStrip, CaseLedger, ResultsTable, TraceDrawer, RunControls
```

### Old → new mapping

| Old | New | Note |
|---|---|---|
| `artifacts/*`, `.agents/SKILLS.md` | `docs/archive/` | |
| `backend/app/api/routes_chat.py` / `routes_scenarios.py` / `routes_evals.py` | `api/chat.py` / `scenarios.py` / `evals.py` | Pydantic models move to `api/schemas.py` |
| `core/gateway.py` | `core/llm_gateway.py` | |
| `core/database.py` (seed + migrations) | `core/database.py`, `core/seed.py`, `core/migrations.py`, `data/merchants.json` | |
| `routes_scenarios.MERCHANT_METADATA`, `dataset_generator.MERCHANT_HUMAN_NAMES`, DB seed literals | `data/merchants.json` | one source, fixes B7 |
| `agents/__init__.py` (graph) | `agents/graph.py` | `agents/__init__` re-exports for compatibility |
| `agents/triage_agent.py`, `rag_agent.py` | `agents/triage.py`, `agents/retrieval.py` | |
| `agents/settlement_agent.py` (240 lines) | `agents/settlement/{node,prompt,offer}.py` | |
| `agents/customer_proxy_agent.py` | **deleted** | dead code: never imported; the dataset's scripted dialogues already do this job |
| `guardrails/pre_guardrails.py` / `post_guardrails.py` | `guardrails/input_guard.py` / `offer_guard.py` | |
| `mcp/razorpay_mcp_client.py` | `payments/mcp_server.py` + `payments/mcp_client.py` | also stops the `app/mcp` package name shadowing the `mcp` library |
| `rag/documents/*.md` | `rag/policies/*.md` | content expanded (N2) |
| `evals/dataset_generator.py`, `simulation_runner.py`, `sync_langsmith_dataset.py` | `evals/dataset.py`, `runner.py`, `langsmith_sync.py` | |
| `frontend/src/components/ContextCard.jsx` | `features/sandbox/CaseFile.jsx` | |
| `ChatTab.jsx` | `features/sandbox/ChatPanel.jsx` (+ `SettlementSlip.jsx`) | |
| `LiveTraceInspector.jsx` | `features/sandbox/AuditRail.jsx` | |
| `ScenarioSelector.jsx` | `features/sandbox/ScenarioPicker.jsx` | |
| `BatchEvalTab.jsx` | `features/benchmark/*` (split into 4) | |
| `TraceDrawer.jsx` | `features/benchmark/TraceDrawer.jsx` | |
| `src/index.css` | `src/styles/tokens.css` + Tailwind layers | |

---

## 2. Refactoring plan

### 2.1 Modularisation
- Split `settlement_agent.py` into prompt building, offer parsing/validation and node orchestration. Each piece becomes unit-testable without the graph.
- One `build_initial_state(...)` helper replaces the two copy-pasted state dicts.
- One `create_batch(db)` and one `compute_kpis(runs)` replace the 4 and 2 copies.
- Frontend: all HTTP goes through `lib/api.js`, a single `axios` instance with base URL, timeout and normalised errors. Polling and chat logic move into hooks. Repeated markup becomes `components/ui/*` (status badges ×3, KPI tiles ×6, accordions ×3, group/filter buttons ×8).

### 2.2 Naming conventions
- **Python:** snake_case modules named for what they do, without suffixes that repeat the package (`api/chat.py`, not `api/routes_chat.py`). Constants in UPPER_SNAKE. Type hints on public functions.
- **React:** PascalCase component files, one component per file, `useX` hooks. Feature folders own their components; `components/ui` is shared only.
- **API JSON stays snake_case.** Existing response fields are kept; any new fields are added alongside them, never replacing them.

### 2.3 Config / env
- `config.py` uses pydantic-settings only (`model_config = SettingsConfigDict(env_file=".env", extra="ignore")`), dropping the `os.getenv` duplicates and `load_dotenv`.
- **New settings:**

| Setting | Default | Purpose |
|---|---|---|
| `CORS_ORIGINS` | localhost:5173 + Vercel URL | fixes S2 |
| `ADMIN_TOKEN` | — | guards eval runs and ingest (S1) |
| `RAG_MODE` | `hybrid_rerank` | `bm25` / `hybrid` / `hybrid_rerank` |
| `RAZORPAY_MCP_MODE` | `sandbox` | `sandbox` / `stdio` / `remote` |
| `RAZORPAY_MCP_URL` | — | for `remote` mode |
| `LLM_MAX_TOKENS` | — | |
| `LOG_LEVEL` | — | |

- `.env.example` documents every variable (and fixes the 4000 vs 6000 mismatch, B20).
- Frontend keeps `VITE_API_BASE_URL` only.
- Pin Python deps: `requirements.in` lists top-level packages, `uv pip compile` produces a pinned `requirements.txt`, and Render keeps using `pip install -r requirements.txt`.

### 2.4 Error handling
- The LLM offer is parsed through a Pydantic schema with coercion and defaults, reusing the unused `SettlementOfferSchema`. Malformed output becomes the heuristic fallback, never a 500 (B10).
- **API errors:** log the full error with a request id, return a generic message plus the id (S6). `/evals/results` returns 404 for an unknown `batch_id` (B18).
- **`init_db`:** explicit column/table existence checks using the SQLAlchemy inspector, with no `except: pass`, and logged.
- **Payments:** a failing live Razorpay call returns `success: false` and the chat says the link couldn't be created. It no longer fakes a link (B9).
- **Frontend:**
  - One error shape from `lib/api.js`.
  - Every fetch has an error state with Retry.
  - A failed chat turn shows an inline error row that is *not* added to the conversation (B16).

### 2.5 Dead code removal
- Delete `customer_proxy_agent.py` and the unused `run_all_50_evaluations` import.
- Remove the 4 unused npm packages (`framer-motion`, `lucide-react`, `clsx`, `tailwind-merge`) and the unused `Outfit` font.
- The `mcp` package stays; it becomes used.
- `razorpay_fetch_*` tools move into the MCP server (used by N7 if approved; otherwise kept as server tools, since MCP clients can discover them).

### 2.6 New dependencies (justified)

| Package | Where | Why | Size note |
|---|---|---|---|
| `fastembed` | backend runtime | dense embeddings + cross-encoder reranker on ONNX Runtime, **no PyTorch** | about 50 MB wheels + about 150 MB models (bge-small 67 MB, MiniLM reranker 80 MB) |
| `trafilatura` | backend **ingest only** (`requirements-ingest.txt`) | robust main-content extraction from HTML pages | not installed on Render |
| `pytest`, `ruff`, `pyright` | backend dev | tests, lint + format, type-check (matches the repo's existing Pylance "basic" setting) | dev only |
| `eslint` (+ react, react-hooks plugins), `prettier` | frontend dev | the `lint` script exists but is broken (B24) | dev only |
| `vitest`, `@testing-library/react`, `jsdom` | frontend dev | component tests | dev only |
| `@playwright/test` | frontend dev | e2e flows and mobile/tablet/desktop checks | dev only, browsers downloaded once |

**Not added:** Radix or other UI kits (native `<dialog>`, `<button>` and `<details>` cover our needs), a vector DB (the corpus is a few hundred chunks, so in-memory numpy is enough), Alembic (two additive migrations don't justify it), and TypeScript (a language swap is out of scope).

**Risk:** Render's free tier has 512 MB RAM. fastembed with two small models should use roughly 250–350 MB. If it doesn't fit, set `RAG_MODE=bm25` on Render and the app degrades gracefully.

---

## 3. UI/UX redesign plan

### 3.1 Direction
- **Who:** a hackathon judge or fintech engineer with about 3 minutes. They want to *see* that the agent negotiates within bounds and *verify* it from the evidence.
- **Task:** pick a case → negotiate → inspect why the offer is safe → check the benchmark.
- **Feel:** a settlement desk's ledger. It should feel like precise, auditable paperwork, not a neon "AI dashboard".

| | |
|---|---|
| **Domain** | ledger, invoice, dunning notice, settlement slip, rubber stamp, audit trail, case file, mandate, receipt, ceiling/bounds |
| **Colour world** | ledger paper (warm off-white), fountain-pen ink blue, ledger-green "settled" ink, amber "pending" carbon copy, stamp red, graphite rules |
| **Signature** | the **Settlement Slip + Bounds Meter**: every offer renders as a receipt (Original → Concession → Net payable), with a meter showing how much of the merchant's ceiling was used and a stamped verdict (WITHIN BOUNDS / CORRECTED / BLOCKED). Corrected values are shown struck through, so the guardrail is visible. |
| **Rejecting** | dark navy + emerald glow glass panels → paper/ink tones with tonal surfaces (dark "night ledger" kept as a mode); six identical icon-number-label KPI boxes → one statement line with a hero "recovered" figure and demoted secondaries; monospace everywhere at 9–10 px → Geist for UI, Geist Mono only for money and IDs, 12 px minimum |

### 3.2 Tokens
CSS variables are defined in `tokens.css` and mapped into Tailwind (`bg-paper`, `text-ink-2`, `border-rule`…). There is one accent and three semantic colours.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | #F4F2ED | #121110 | page |
| `--sheet` | #FBFAF7 | #191816 | panels |
| `--sheet-raised` | #FFFFFF | #201F1C | popovers, drawer |
| `--well` | #ECE9E3 | #0E0D0C | inputs (inset) |
| `--rule` / `--rule-strong` | rgba(40,32,20,.10/.18) | rgba(255,250,240,.08/.14) | borders |
| `--ink` / `-2` / `-3` / `-4` | #1C1A17 / #4A463F / #6F6A61 / #9A948A | #EDEAE4 / #BDB8AF / #8C877E / #5F5B54 | text tiers |
| `--accent` (ledger ink) | #2E4BB8 | #8FA5FF | primary actions, focus ring, links |
| `--settled` | #1F7A4D | #4CC38A | within bounds, paid, pass |
| `--caution` | #A15C07 | #E0A345 | corrected, running |
| `--void` | #B42318 | #F2716A | blocked, failed, errors |

Text tiers are checked for WCAG AA (≥ 4.5:1) on `--sheet` in both modes before shipping.

### 3.3 Typography, spacing, depth, motion
- **Typography:** Geist (UI) and Geist Mono (amounts, IDs, JSON) with `tabular-nums`. Scale ratio 1.25 from 14 px: **12 · 14 · 16 · 18 · 22 · 28 · 36**. Hierarchy comes from weight (400/500/600) and ink tier before size. Headings get slight negative tracking.
- **Spacing:** 4 px base, workbench density. Panel padding 16, group gap 12, section gap 24.
- **Radius:** 6 (controls), 10 (panels), 14 (dialogs/drawer). Nested elements follow `outer = inner + padding`.
- **Depth:** borders plus tonal surface steps only. No glass, no glows, no drop shadows except a single ring on raised popovers.
- **Motion:**
  - 150–200 ms `cubic-bezier(.23,1,.32,1)` on dropdown, drawer and slip entrance.
  - One "stamp" moment when a link is issued (opacity + scale .96→1).
  - No perpetual animations (the ping, pulse and spin go).
  - `prefers-reduced-motion` honoured throughout.

### 3.4 Layout and responsiveness
- **Header:** brand, nav (Sandbox / Benchmark) and a theme toggle. The scenario picker moves *into the Sandbox page*, so the global header can't overflow on mobile (fixes the main mobile bug).
- **Sandbox:**
  - ≥1280 px: `Case file 300px | Chat 1fr | Audit rail 380px`.
  - 768–1279 px: `Chat | side panel 360px` with Case/Audit tabs.
  - <768 px: full-width chat plus a segmented control (Chat · Case · Audit).
  - `min-h-dvh` everywhere and no fixed `calc(100vh-…)`; the chat log scrolls internally.
- **Benchmark:** statement strip (Recovered ₹ of invoiced ₹ as the hero, then pass rate, breaches, intercepts, faithfulness, p50 latency) → run controls → **Case Ledger** (50 cells coloured by outcome, click to open the trace) → results table (≥768 px) or card list (<768 px) → trace drawer (native `<dialog>`, full-screen sheet on mobile).
- **Scenario picker:** a native `<dialog>` "case browser" with search, group and filter. Items are real `<button>`s and Esc closes it. It becomes a full-screen sheet on mobile.

### 3.5 Reusable components
`Button` (primary / secondary / ghost / danger; 36 px, 44 px touch target on mobile), `Stamp` (verdict badge), `Panel`, `Disclosure` (accordion with `aria-expanded`), `Dialog` (native, focus-returning), `Segmented` (tabs with `role=tablist`), `Skeleton`, `EmptyState`, `ErrorState` (with Retry), `Amount` (₹ en-IN, tabular), `BoundsMeter`, `SettlementSlip`, `AuditRail`, `ThemeToggle`.

### 3.6 Light/dark mode
Follows the system preference by default. The toggle is stored in `localStorage`, and a tiny inline script in `index.html` prevents a flash of the wrong theme.

### 3.7 Accessibility
- Every control is native or has full ARIA.
- Visible focus ring using the accent colour.
- The chat log uses `aria-live="polite"`.
- Labels on all inputs.
- The placeholder no longer rotates.
- 12 px minimum text.
- AA contrast.
- 44 px touch targets on mobile.
- The drawer and picker trap focus and return it to the trigger (built into `<dialog>`).
- Escape closes overlays.

### 3.8 Loading / empty / error states

| Surface | Loading | Empty | Error |
|---|---|---|---|
| Scenarios | skeleton rows in picker + case file | — | inline error + Retry; Send disabled with reason |
| Chat turn | typing row + audit rail shows "Running triage → policy → offer…" | greeting + 3 suggested replies | inline error row with Retry; not added to history |
| Audit rail | step skeleton | "Send a message to see the agent's evidence" | — |
| Benchmark | skeleton strip + ledger | "No runs yet. Run the benchmark" CTA | inline error + Retry; polling stops after 3 failed attempts |
| Drawer | — | "No turns recorded" | — |

---

## 4. Bug-fix list (prioritised)

Each fix gets a regression test written first; it fails before the fix and passes after.

| Pri | Bugs | Fix |
|---|---|---|
| P0 | **B1** price-alignment bypass | The payment-link amount is *always* the guardrail-approved amount. Amounts in the message text are checked against the legitimate figures (original, approved, concession, approved plan prices, split parts). On a mismatch, the message is replaced with a deterministic template and a `TEXT_AMOUNT_MISMATCH` violation is recorded. |
| P0 | **B2, B5** downgrade bypass / splits flagged | (needs **D2**) Offer guard gets per-merchant `plans[]`, `split_rules` (e.g. 50/50 above ₹10,000) and `partial_settlement_pct` (QuickKart 80%). A downgrade must equal a listed lower-tier plan price; a split or partial must match an allowed rule; everything else falls under the discount ceiling. |
| P0 | **B3** RAG tenant mapping | Read the merchant id from `merchants.json` or the filename stem properly. A test asserts all 15 merchants retrieve their own document. |
| P1 | **B4** phantom INR 299 invoices | (needs **D1**) Seed every scenario's customer and invoice. The chat returns 404 for unknown ids instead of silently defaulting. |
| P1 | **B6** global token-budget lockout | Budget per conversation id (client-generated now, server-side with N6), with an LRU cap. The throttle message is not shown raw and uses the configured number. |
| P1 | **S1–S4** | `ADMIN_TOKEN` on eval-run/ingest, simple per-IP rate limit on chat, CORS from env, roles restricted to `user`/`assistant`, max message count and length, and the input guard scans all user turns with a broader pattern set (with tests for the bypasses found). |
| P1 | **B9, S5** fake links | No fake link on live failure; sandbox links are clearly marked (`sandbox: true`, full-entropy id, not on the `rzp.io` domain); no SMS/email notify unless real customer contact details exist. |
| P1 | **B10** 500s on malformed LLM JSON | Schema-validated parsing (§2.4). |
| P2 | **B11** GET runs benchmark | GETs never start runs; an empty list means the UI shows the "Run benchmark" empty state. |
| P2 | **B7** wrong limits in UI | Scenarios API reads limits from the DB. |
| P2 | **B8** cache never hits / caches failures | Ticket id generated after the LLM call (not in the prompt); never cache fallback/error results; bounded LRU. |
| P2 | **B12, B13** outcome / KPIs | Settlement node always sets a final `step`; KPIs are computed from real data (latency, tokens); the "(0 Breaches)" label is removed; expected-vs-actual scoring in N5. |
| P2 | **B14, B15** eval polling | `useEvalRuns` hook: resumes polling when a RUNNING batch is shown, polls only the selected batch, stops on unmount or error. |
| P2 | **B16, B17** | Errors not added to chat history; the audit checklist reflects real per-check results returned by the API. |
| P3 | **B18–B25** | 404 for bad batch, real token/latency figures, env default, favicon, invalid Tailwind classes, hook deps, ESLint setup, triage ordering. |

---

## 5. New features / improvements

✅ = recommended (to be implemented on "proceed").

| # | Feature | Rationale | Effort | Rec |
|---|---|---|---|---|
| **N1** | **Real MCP payments layer.** Our own MCP server (`MCPServer` from the installed `mcp` 2.1 SDK) exposes Razorpay tools named like Razorpay's official server (`create_payment_link`, `fetch_payment_link`, …), backed by the live Razorpay SDK or a sandbox simulator. The agent calls them through an MCP **client**: in-process for sandbox and tests, or switched by env to **Razorpay's official MCP server** (`https://mcp.razorpay.com/mcp` with Basic auth, or its stdio binary/Docker image). The audit rail shows tool discovery, the call arguments and the result. | You asked for it; it makes the "MCP" claim true and lets the official server drop in. | L | ✅ |
| **N2** | **Policy knowledge base v2.** (a) Richer curated *internal* rules per merchant: plans, concessions, splits, escalation and cancellation, written as structured sections. (b) A `python -m app.rag.ingest` CLI that fetches each merchant's *public* pages (pricing, refund/cancellation, help centre) listed in `merchants.json`, respects robots.txt, extracts the main text and saves **dated snapshots** with the source URL into `rag/sources/`. Snapshots are committed, so the app runs offline and reproducibly; refresh is a deliberate command, never a per-chat live fetch. | The .md policies are thin and partly stale (e.g. Hotstar is now JioHotstar); real public text makes answers grounded and citable. | M–L | ✅ |
| **N3** | **Retrieval v2.** Heading-aware chunking with metadata (merchant, source, section, URL, date) → BM25 + dense (fastembed `bge-small-en-v1.5`) fused with reciprocal-rank fusion → cross-encoder rerank (`ms-marco-MiniLM-L-6-v2`) → top-k with **citations** shown in the chat and audit rail. Document embeddings are precomputed at ingest. Retrieved web text is wrapped as untrusted data and scanned by the input guard (indirect prompt-injection defence); guardrails never read numbers from retrieved text. | The quality jump you asked for, without PyTorch. | M | ✅ |
| **N4** | **Retrieval evaluation.** About 60 labelled query→relevant-chunk pairs; reports recall@k and MRR for `bm25` vs `hybrid` vs `hybrid_rerank`; a pytest threshold guards regressions; results shown in TEST_REPORT. | Without this, "RAG is better" is a claim, not a fact. | S–M | ✅ |
| **N5** | **Honest benchmark scoring.** Compare each case's actual action/amount with `expected_action`/`expected_amount` → pass/fail per case + pass-rate KPI; real latency (p50/p95) and token totals; real LangSmith run URLs when tracing is on (hidden otherwise). | Today the benchmark can't fail and some KPIs are invented (B13). | M | ✅ |
| **N6** | **Server-side conversations.** `POST /api/conversations` starts one for a scenario; `POST /api/conversations/{id}/messages` sends only the new user message; the backend stores the history. A "New conversation" button resets it. The old `POST /api/chat` stays for compatibility. | Closes the forged-history hole (S3) and fixes the token budget properly (B6). | M | ✅ |
| N7 | **Payment status loop.** The audit rail can check the link status via the MCP `fetch_payment_link` tool; the sandbox offers "Simulate payment", marking the invoice recovered; the benchmark "Recovered" counts only paid links. | Closes the recovery loop end-to-end; good demo moment. | M | optional |
| N8 | **Streaming responses (SSE).** | Nicer feel, but the agent returns structured JSON, so streaming text adds complexity for little gain. | M | ✗ |

### Honest limits on N2/N3
- **Companies don't publish internal negotiation limits** (max discount, split rules). Those stay as *simulated merchant configuration* in `merchants.json` and are labelled as such in the UI. Websites supply plans, prices, refund and cancellation terms.
- **Not every page can be fetched.** In a probe today, Netflix, Spotify and Slack pages served prices in plain HTML; Notion, Zoho and Jira render prices with JavaScript; Swiggy returned 404; the JioHotstar URL redirected. For those, the curated policy stays the source until a manual snapshot is added. The ingest report lists which merchants are web-backed.
- Real brand names combined with simulated rules is fine for a demo, but the UI and README will state that the internal rules are illustrative.

---

## 6. Testing strategy

| Layer | Tool | What |
|---|---|---|
| **Characterisation (Phase 3, before refactor)** | pytest + FastAPI TestClient, LLM stubbed / offline fallback, sandbox payments, temp SQLite | Pins current behaviour of F1–F23: endpoint shapes, guardrail outputs, graph paths (intercept, escalate, discontinue, link, deferral), scenarios content, eval run on a 5-case subset, LangSmith local mode. Known bugs are captured as `xfail(strict=True)` tests that document correct behaviour and flip to passing in Phase 4.2. |
| Unit | pytest | guards, offer parsing, chunking, fusion and rerank ordering, KPI maths, MCP server tools via the in-process `Client(server)` |
| Integration | pytest | full chat turn through graph + MCP client; conversations API; eval batch (5 cases) |
| Retrieval quality | pytest + `retrieval_eval.py` | recall@k / MRR thresholds per `RAG_MODE` (model-dependent tests marked `slow`) |
| Frontend unit | vitest + Testing Library | picker search/group/filter, slip and meter maths, stamp states, chat error row, polling hook, theme toggle |
| E2E | Playwright against backend in offline mode | select scenario → chat → link issued → audit evidence; run benchmark → open trace; keyboard-only path; screenshots at 390 / 820 / 1440 px, light + dark; zero console errors |
| Static | ruff (lint + format), pyright basic, ESLint, Prettier | must pass in Phase 5 |

All tests run offline: no OpenRouter, Razorpay or LangSmith keys needed. The baseline results from Phase 3 are recorded in `docs/TEST_REPORT.md`.

---

## 7. Execution order (after approval)

1. **Phase 3:** characterisation tests + baseline results.
2. **Phase 4.1:** restructure per §1 (moves, archive, dead code, config, lint/format tooling); tests still green.
3. **Phase 4.2:** bug fixes in §4 priority order, each with a regression test (D1/D2 seed and schema here).
4. **Phase 4.3:** design system + restyle (§3).
5. **Phase 4.4:** validation, error handling, performance and UX-flow improvements.
6. **Phase 4.5:** N1 → N6 (+ N7 if approved), each with tests.
7. **Phases 5–6:** verify and document.
