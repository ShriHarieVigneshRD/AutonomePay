# AutonomePay — Autonomous Financial Concierge & Settlement Sentinel

AutonomePay is an enterprise-grade, bounded multi-agent revenue recovery and customer settlement system built for the Razorpay AI Buildathon (Track 03: AI Revenue Recovery). It features a FastAPI + LangGraph multi-agent backend, Neon PostgreSQL database, 15-document multi-tenant RAG engine, LiteLLM/OpenRouter gateway, pre/post LLM guardrails, real Razorpay MCP client integration, 50-case synthetic eval suite with LangSmith sync, and a high-agency React frontend.

---

## 🛠️ Architecture & Key Components Built

### 1. Environment & Dependency Management (`uv`)
- Managed with `uv` virtual environment (`.venv`).
- Dependencies specified in `backend/requirements.txt` (FastAPI, Uvicorn, LangGraph, LiteLLM, mcp, razorpay, langsmith, sentence-transformers, rank-bm25).

### 2. Multi-Tenant RAG Policy Engine (15 Markdown Documents)
- Created 15 rich merchant policy documents in `backend/app/rag/documents/`:
  - `01_hotstar_policy.md` (Super Plan, Mobile Plan downgrade, max INR 20 discount, 30-day pause)
  - `02_netflix_india_policy.md` (Strict zero discount, 48-hr retry window)
  - `03_amazon_prime_policy.md` (5-day annual grace period, max 5% discount)
  - `04_spotify_india_policy.md` (7-day grace buffer)
  - `05_airtel_postpaid_policy.md` (INR 100 late fee waiver if paid in 24h, 60-day safe-custody pause)
  - `06_jio_fiber_policy.md` (48-hr emergency data top-up link for bank gateway downtime)
  - `07_swiggy_one_policy.md` (No split payments, 10% coupon concession max INR 30 for high-LTV users)
  - `08_zomato_gold_policy.md` (1-month free extension on gateway timeout failure)
  - `09_notion_saas_policy.md` (50/50 milestone split for invoices > INR 10,000)
  - `10_slack_workspace_policy.md` (Fair-billing inactive user credit, 5-day grace buffer)
  - `11_zoho_one_policy.md` (10-day payment extension, 3% concession ceiling)
  - `12_jira_atlassian_policy.md` (14-day formal corporate invoice extension)
  - `13_quickkart_b2b_policy.md` (Net-30, hold 20% disputed portion, issue 80% balance link with 3% prompt payment discount)
  - `14_udaan_wholesale_policy.md` (2-stage milestone settlement: 40% immediate, 60% on day 15)
  - `15_razorpayx_payroll_policy.md` (5-day emergency grace period for salary disbursement accounts)
- Implemented `backend/app/rag/retriever.py` with hybrid `sentence-transformers/all-MiniLM-L6-v2` dense embeddings + `rank_bm25` keyword scoring strictly scoped by `merchant_id`.

### 3. Core Gateway, Guardrails & Razorpay MCP Client
- **LiteLLM Gateway (`backend/app/core/gateway.py`):** OpenRouter model proxy (`llama-3.3-70b-instruct:free` with fallback to `gemini-2.0-flash-exp:free`), SHA-256 in-memory semantic caching, and session token spend limit (4,000 tokens).
- **Pre-LLM Guardrail (`backend/app/guardrails/pre_guardrails.py`):** Sanitizes inputs for prompt injections, system overrides, and unauthorized 100% discount requests.
- **Post-LLM Guardrail (`backend/app/guardrails/post_guardrails.py`):** Non-LLM Python Invariant Gate verifying arithmetic split sums, merchant discount ceilings, and maximum grace period thresholds.
- **Razorpay MCP Client (`backend/app/mcp/razorpay_mcp_client.py`):** Model Context Protocol client exposing standard Razorpay tools (`razorpay_create_payment_link`, `razorpay_fetch_subscription_status`, `razorpay_fetch_payment_status`).

### 4. LangGraph Multi-Agent Engine
- Defined `AutonomeState` in `backend/app/agents/state.py`.
- Implemented `triage_node`, `rag_node`, `settlement_node`, and `customer_proxy_node`.
- Compiled the graph flow in `backend/app/agents/__init__.py`.

### 5. Evaluation Harness & LangSmith Sync
- `backend/app/evals/dataset_generator.py`: Generates 50 synthetic test cases (80%+ multi-turn across all 15 merchants).
- `backend/app/evals/sync_langsmith_dataset.py`: Programmatically syncs `autonomepay-50-eval-benchmark` on LangSmith.
- `backend/app/evals/judge.py`: RAG Triad Evaluator (Context Relevance, Faithfulness, Answer Relevance).
- `backend/app/evals/simulation_runner.py`: Wrapped in `@traceable` for LangSmith nested multi-turn trace logging.

### 6. High-Agency React Frontend
- Sleek dark/zinc design system matching `# High-Agency Frontend Skill` directives.
- **Concierge Sandbox (Tab 1):** Preset scenario selector, live context card, WhatsApp-style interactive chat with live typing indicators and rendered Razorpay payment link pills, and Live Trace Inspector accordion.
- **Batch Evaluation Matrix (Tab 2):** Top KPI Analytics bar, `[ Run All 50 Evals ▶ ]` trigger button with progress bar, 50-case matrix table, and `TraceDrawer` slide-out drawer with LangSmith trace links.

---

## 🚀 How to Run the Application

### 1. Backend Server (FastAPI + Uvicorn)
```bash
# Using uv python virtual environment
uv run uvicorn app.main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`

### 2. Frontend Web Interface (React + Vite)
```bash
cd frontend
npm run dev
```
- Web Application: `http://localhost:5173`
