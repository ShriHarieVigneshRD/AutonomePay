# AutonomePay

**A policy-bound AI concierge that recovers failed subscription payments.**

When a customer's renewal fails, AutonomePay talks to them, looks up the merchant's settlement policy, and offers what the policy allows. That might be a small discount, a cheaper plan, instalments, a grace period, or settling the undisputed part of a disputed order. It then issues a Razorpay payment link through the Model Context Protocol (MCP).

Every offer is checked in code after the LLM replies. A payment link can only ever be created for an amount the guardrail approved, and only after the customer agrees.

Built for the Razorpay AI Buildathon. The live demo at [autonome-pay.vercel.app](https://autonome-pay.vercel.app) runs the earlier version until it is redeployed.

![Sandbox: conversation, settlement slip and audit trail](docs/screenshots/sandbox-desktop.png)

| Benchmark (dark) | Mobile | Mobile case file (dark) |
|---|---|---|
| ![Benchmark dashboard](docs/screenshots/benchmark-desktop-dark.png) | ![Mobile sandbox](docs/screenshots/sandbox-mobile.png) | ![Mobile case file](docs/screenshots/case-file-mobile-dark.png) |

---

## Features

- **Negotiation sandbox.** Pick any of 50 benchmark cases across 15 merchants and play the customer. Each agent reply shows a **settlement slip**: original price, concession or held amount, net payable, bounds meters, and a verdict stamp (*Within bounds* / *Corrected* / *Blocked*).
- **Audit trail.** Every turn shows the triaged intent, the policy passages retrieved (with sources), the offer, each guardrail check with its result, and the MCP tool call.
- **Deterministic guardrails.** Discount ceilings, grace limits, listed plan prices for downgrades, approved instalment schedules, undisputed-portion rules, and a check that every amount in the reply is an approved figure. A prompt-injection screen runs over all customer messages before the LLM.
- **Real MCP payments.** Payment tools (`create_payment_link`, `fetch_payment_link`) are called over MCP. The server is either AutonomePay's own (live Razorpay API or a sandbox) or Razorpay's official hosted MCP server.
- **Payment status loop.** "Check status" asks the provider over MCP. Paid links mark the invoice recovered or partially recovered. Sandbox links open a `/pay/<id>` checkout where a payment can be simulated.
- **Grounded retrieval.** Curated merchant rules plus dated snapshots of public merchant pages. Ranking is BM25 + dense embeddings fused with reciprocal-rank fusion, then a cross-encoder reranker. Replies cite their sources.
- **Honest benchmark.** 50 distinct scripted negotiations, each scored automatically against an expected outcome: the right action, link or no link, and where it matters the exact approved amount and the policy passage, often a public-page snapshot, that must have been consulted. See [docs/BENCHMARK.md](docs/BENCHMARK.md). The dashboard shows a hero "covered by payment links" figure, pass rate, the share of AI-written replies, guardrail corrections, blocked injections, faithfulness, latency and tokens, plus a 50-cell case ledger. Cases run in 5 batches of 10 to fit the free LLM tier, and the Latest results view combines them.
- **Server-side conversations.** The server keeps the history, so it can't be forged. Conversations survive a reload and can be shared (`?case=…&conversation=…`).
- **Works offline.** With no API keys it runs a deterministic, merchant-aware policy engine and sandbox payments, which is how the test suites run.
- **Responsive and accessible.** Phone, tablet and desktop layouts; light and dark themes; native dialogs; keyboard navigation; AA text contrast.

## How the safety works

| Layer | Rule | Where |
|---|---|---|
| Input screen | Injection, jailbreak and "100% off" patterns in **any** customer turn stop the turn before the LLM | `guardrails/input_guard.py` |
| Offer guard | Discount ≤ merchant ceiling; amount ≤ invoice; grace ≤ limit; downgrade = a listed cheaper plan; split = the merchant's schedule; partial = the undisputed % | `guardrails/offer_guard.py` |
| Message check | Every ₹ amount in the reply must be an approved figure, otherwise the reply is replaced with the approved offer | `agents/settlement/node.py` |
| Link gate | Link only for the approved amount, only with explicit consent, never for escalations or cancellations; LLM-written URLs are stripped | `agents/settlement/node.py` |
| Payments | No fake links on provider failure; customers aren't notified unless `RAZORPAY_NOTIFY_CUSTOMERS=true` | `payments/` |

Merchant limits, plans and split rules live in one file, [`backend/app/data/merchants.json`](backend/app/data/merchants.json). It is synced to the database on startup, so the guardrail, the retrieval corpus and the UI always show the same numbers. These internal limits are *simulated* merchant settings; companies don't publish them.

## Architecture

```mermaid
graph LR
  UI[React SPA] -->|/api/conversations| API[FastAPI]
  API --> G[LangGraph]
  subgraph G[Agent graph]
    T[Triage] --> R[Retrieval<br/>BM25 + embeddings + reranker] --> S[Settlement]
  end
  S -->|LiteLLM| LLM[OpenRouter model chain]
  S --> OG[Offer guard]
  S -->|MCP client| MCP[Payments MCP server]
  MCP --> RZ[Razorpay API]
  MCP --> SB[(Sandbox links)]
  API --> DB[(SQLite / PostgreSQL)]
```

## Tech stack

- **Backend:** Python 3.11, FastAPI 0.141, Pydantic 2.13, SQLAlchemy 2.0, LangGraph 1.2, LiteLLM 1.98 (OpenRouter), MCP Python SDK 2.1, Razorpay SDK 2.0, rank-bm25, fastembed 0.9 (ONNX; no PyTorch), LangSmith (optional).
- **Frontend:** React 18, Vite 5, Tailwind CSS 3.4, Phosphor icons, axios.
- **Tooling:** pytest, ruff, pyright, Vitest, Testing Library, Playwright, ESLint 9, Prettier.

## Quick start

**Prerequisites:** Python 3.11+, Node 18+, and [`uv`](https://docs.astral.sh/uv/) (or plain `pip`).

```bash
# Backend
cd backend
uv venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -r requirements-dev.txt            # runtime + ingest + test tools
cp .env.example .env                              # everything is optional
uvicorn app.main:app --reload --port 8000         # http://localhost:8000/docs

# Frontend (second terminal)
cd frontend
npm install
npm run dev                                       # http://localhost:5173
```

With an empty `.env` everything works offline: the policy heuristic answers instead of the LLM, and payment links are sandbox links. The first start with `RAG_MODE=hybrid_rerank` downloads two small models (~150 MB) into `backend/.cache/models`.

### Configuration

All variables are documented in [`backend/.env.example`](backend/.env.example). The important ones:

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY`, `PRIMARY_MODEL`… `FALLBACK_MODEL` | LLM chain, tried in order. **MiniMax M3/M2.7 are no longer free on OpenRouter**: if your `.env` still lists them, switch to the defaults in `.env.example`. |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Test keys create real Razorpay test links; `rzp_test_mock…` or empty uses the sandbox. Razorpay test mode allows 30 payment links per account: expire old ones in the dashboard if you hit the limit. |
| `RAZORPAY_MCP_MODE` | `embedded` (default), `remote` (Razorpay's hosted MCP server, `RAZORPAY_MCP_URL`) or `stdio` (`RAZORPAY_MCP_COMMAND`, e.g. Razorpay's binary). |
| `RAG_MODE` | `bm25` (~290 MB), `hybrid` (~555 MB) or `hybrid_rerank` (~700 MB). |
| `PUBLIC_APP_URL`, `CORS_ORIGINS` | Frontend URL (where sandbox links point) and allowed browser origins. |
| `ADMIN_TOKEN` | If set, starting benchmark runs needs an `X-Admin-Token` header (use on public deployments). |
| `DATABASE_URL` | SQLite by default; any SQLAlchemy URL (e.g. PostgreSQL). |

The frontend needs only `VITE_API_BASE_URL` (empty means the Vite proxy forwards `/api` to `:8000`).

## Usage

- **Sandbox (`/`):**
  - Open the case browser to choose a case.
  - Reply as the customer, or use a suggested reply.
  - Say yes to get a payment link.
  - Open the link and simulate payment (sandbox), then "Check status".
- **Benchmark (`/benchmark`):** choose a batch of 10 cases (or all 50) and press "Run benchmark" (seconds offline, minutes with an LLM). Latest results combines the batches. Click any ledger cell for its full trace, including who wrote each reply.
- **API:** interactive docs at `/docs`. The main endpoints are:
  - `POST /api/conversations`
  - `POST /api/conversations/{id}/messages`
  - `GET /api/payments/{link_id}`
  - `POST /api/evals/run`
  - `GET /api/evals/results`

### Refreshing policies from the web
```bash
cd backend
python -m app.rag.ingest                 # fetch every merchant's public pages
python -m app.rag.ingest --merchant netflix_india
```
Pages are fetched only if robots.txt allows. They are reduced to their main text, screened for prompt injection, and saved as dated snapshots in `backend/app/rag/sources/` (committed, and reviewed like code). The app never fetches the web during a chat. Currently 9 pages for 6 merchants. The others block crawlers or render with JavaScript, so their curated policy is the source.

### Retrieval quality
```bash
python -m app.evals.retrieval_eval       # 56 labelled questions
```

| Mode | hit@1 | hit@3 | MRR@10 |
|---|---|---|---|
| bm25 | 0.804 | 0.929 | 0.879 |
| hybrid | 0.893 | 0.946 | 0.927 |
| hybrid_rerank | 0.893 | 0.946 | 0.931 |

## Project structure

```
backend/
  app/
    api/            chat, conversations, scenarios, evals, payments, schemas, deps (rate limit, admin token)
    agents/         graph, state, triage, retrieval, settlement/{node,prompt,offer}
    guardrails/     input_guard, offer_guard
    payments/       mcp_server, mcp_client, razorpay (live API adapter), ledger
    rag/            chunking, retriever, ingest, policies/ (curated), sources/ (web snapshots)
    evals/          dataset (+ expectations), runner, judge, retrieval_eval, langsmith_sync
    core/           config, database (models), migrations, seed, catalog, llm_gateway
    data/           merchants.json (single source of merchant config)
  tests/            pytest: characterisation, regressions, MCP, conversations, payments, retrieval
frontend/
  src/
    components/     AppHeader, ui/ (Button, Stamp, Panel, Segmented, Dialog, States)
    features/       sandbox/, benchmark/, checkout/
    hooks/          useScenarios, useConversation, useBenchmark, usePaymentStatus
    lib/            api, format, theme, route
    styles/         design tokens (light + dark)
  e2e/              Playwright flows and responsive checks
docs/               ANALYSIS, PLAN, TEST_REPORT, CHANGELOG, screenshots, archive/
```

## Testing

```bash
# backend
cd backend
pytest                    # 184 tests, offline, ~5 s
pytest -m slow            # model-backed retrieval test (downloads models once)
ruff check app tests && ruff format --check app tests && pyright

# frontend
cd frontend
npm test                  # Vitest unit/component tests
npm run lint && npm run format:check && npm run build
npm run test:e2e          # Playwright: starts an offline backend + Vite on ports 8799/5199
```

Results and known limitations are in [docs/TEST_REPORT.md](docs/TEST_REPORT.md).

## Deployment

- **Backend (Render):** [`render.yaml`](render.yaml). Set the secrets in the dashboard: `OPENROUTER_API_KEY`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and optionally `ADMIN_TOKEN` and `LANGCHAIN_API_KEY`.
  - The free 512 MB instance only fits `RAG_MODE=bm25`. Use `hybrid_rerank` on an instance with about 1 GB.
  - SQLite on Render is reset on redeploy; point `DATABASE_URL` at PostgreSQL to keep data.
- **Frontend (Vercel):** root `frontend/`, env `VITE_API_BASE_URL=https://<your-backend>`. SPA rewrites are in `frontend/vercel.json`. Set the backend's `PUBLIC_APP_URL` and `CORS_ORIGINS` to the Vercel URL.

## Future work

- Run the 50-case benchmark against the live model chain and track pass rate per model.
- Move embeddings to an API (e.g. OpenRouter's embedding endpoint) so hybrid retrieval fits a 512 MB instance.
- Headless-browser ingest for JavaScript-rendered policy pages, and a review step that flags price changes (Spotify's live prices already differ from the curated plans).
- Shared rate-limit and budget state (Redis) for multi-instance deployments; a CI workflow running the suites above.
- A merchant admin UI for `merchants.json`, and an independent labelling pass for the retrieval eval.
- Add a LICENSE file (the original README referenced one that doesn't exist).
