# SYSTEM SPECIFICATION & ARCHITECTURAL PROMPT: AUTONOMEPAY

You are an expert Principal AI Systems Architect and Full-Stack Engineer. Your task is to build **AutonomePay — Autonomous Financial Concierge & Settlement Sentinel**, an enterprise-grade, bounded multi-agent revenue recovery and customer settlement system for the Razorpay AI Buildathon (Track 03: AI Revenue Recovery).

You will write all code end-to-end, creating a production-ready, modular system consisting of a React frontend, a FastAPI + LangGraph multi-agent backend, a Neon PostgreSQL database, a 15-document multi-tenant RAG engine, an OpenRouter-powered LiteLLM gateway, deterministic guardrails, Razorpay MCP integration, and an automated 50-case multi-turn simulation and evaluation harness synchronized programmatically with LangSmith.

---

## 1. TECH STACK & SYSTEM ARCHITECTURE MATRIX

* **Frontend:** React (Vite, JavaScript), Tailwind CSS, Lucide Icons, Axios.
* **Backend:** FastAPI (Python 3.11+), Uvicorn, Pydantic v2, SQLAlchemy.
* **Agent Framework:** LangGraph (StateGraph, cyclic graphs, conditional routing, state checkpoints).
* **LLM Gateway:** LiteLLM proxy configured with OpenRouter free models (`openrouter/meta-llama/llama-3.3-70b-instruct:free` with fallback to `openrouter/google/gemini-2.0-flash-exp:free`), featuring semantic caching and token budgeting.
* **Database:** Neon DB (Serverless PostgreSQL) storing merchants, customers, invoices, and evaluation logs.
* **RAG System:** In-memory or vector-indexed retrieval over 15 rich multi-tenant merchant policy Markdown documents.
* **Tool Interface:** Razorpay Model Context Protocol (MCP) Client simulating and invoking official Razorpay MCP payment tools (`razorpay_create_payment_link`, `razorpay_fetch_subscription`, `razorpay_fetch_payment_status`).
* **Guardrails Architecture:**
  * **Pre-LLM:** Input sanitization detecting prompt injections, jailbreaks, and adversarial discount extraction.
  * **Post-LLM:** Deterministic Non-LLM Python Invariant Gates and Pydantic schemas validating arithmetic sum invariants, discount ceilings, and maximum grace period thresholds.
* **Observability & Evals:** LangSmith SDK (`@traceable`, programmatic dataset creation `autonomepay-50-eval-benchmark`), RAG Triad Evaluator (Context Relevance, Faithfulness, Answer Relevance), and an automated Multi-Turn Customer Proxy Simulation Runner.

---

## 2. REPOSITORY TREE

```text
autonomepay/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes_chat.py
│   │   │   ├── routes_evals.py
│   │   │   └── routes_scenarios.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── state.py
│   │   │   ├── triage_agent.py
│   │   │   ├── rag_agent.py
│   │   │   ├── settlement_agent.py
│   │   │   └── customer_proxy_agent.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── gateway.py
│   │   │   └── langsmith_client.py
│   │   ├── guardrails/
│   │   │   ├── __init__.py
│   │   │   ├── pre_guardrails.py
│   │   │   └── post_guardrails.py
│   │   ├── mcp/
│   │   │   ├── __init__.py
│   │   │   └── razorpay_mcp_client.py
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── documents/
│   │   │   │   ├── 01_hotstar_policy.md
│   │   │   │   ├── 02_netflix_india_policy.md
│   │   │   │   ├── 03_amazon_prime_policy.md
│   │   │   │   ├── 04_spotify_india_policy.md
│   │   │   │   ├── 05_airtel_postpaid_policy.md
│   │   │   │   ├── 06_jio_fiber_policy.md
│   │   │   │   ├── 07_swiggy_one_policy.md
│   │   │   │   ├── 08_zomato_gold_policy.md
│   │   │   │   ├── 09_notion_saas_policy.md
│   │   │   │   ├── 10_slack_workspace_policy.md
│   │   │   │   ├── 11_zoho_one_policy.md
│   │   │   │   ├── 12_jira_atlassian_policy.md
│   │   │   │   ├── 13_quickkart_b2b_policy.md
│   │   │   │   ├── 14_udaan_wholesale_policy.md
│   │   │   │   └── 15_razorpayx_payroll_policy.md
│   │   │   └── retriever.py
│   │   ├── evals/
│   │   │   ├── __init__.py
│   │   │   ├── dataset_generator.py
│   │   │   ├── sync_langsmith_dataset.py
│   │   │   ├── simulation_runner.py
│   │   │   └── judge.py
│   │   └── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatTab.jsx
│   │   │   ├── BatchEvalTab.jsx
│   │   │   ├── TraceDrawer.jsx
│   │   │   ├── ScenarioSelector.jsx
│   │   │   ├── ContextCard.jsx
│   │   │   └── LiveTraceInspector.jsx
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
└── README.md
```

---

## 3. DATABASE SCHEMA (Neon PostgreSQL DDL)

Create and execute the schema in Neon DB via `backend/app/core/database.py`:

```sql
-- 1. Merchants Table
CREATE TABLE IF NOT EXISTS merchants (
    merchant_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    max_discount_pct NUMERIC(5, 2) DEFAULT 5.00,
    max_grace_days INT DEFAULT 7,
    auto_escalation_limit NUMERIC(12, 2) DEFAULT 50000.00,
    policy_doc_slug VARCHAR(100) NOT NULL
);

-- 2. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(64) PRIMARY KEY,
    merchant_id VARCHAR(64) REFERENCES merchants(merchant_id),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    lifetime_value NUMERIC(12, 2) DEFAULT 0.00,
    risk_tier VARCHAR(20) DEFAULT 'Low',
    tenure_months INT DEFAULT 1,
    failed_payment_history_count INT DEFAULT 0
);

-- 3. Invoices / Mandates Table
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id VARCHAR(64) PRIMARY KEY,
    customer_id VARCHAR(64) REFERENCES customers(customer_id),
    merchant_id VARCHAR(64) REFERENCES merchants(merchant_id),
    plan_name VARCHAR(100) NOT NULL,
    original_amount NUMERIC(12, 2) NOT NULL,
    current_status VARCHAR(50) NOT NULL,
    failure_code VARCHAR(100) NOT NULL,
    due_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    recovered_amount NUMERIC(12, 2) DEFAULT 0.00,
    razorpay_payment_link VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Evaluation Runs & Simulation Logs Table
CREATE TABLE IF NOT EXISTS evaluation_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    test_id VARCHAR(64) NOT NULL,
    scenario_type VARCHAR(100) NOT NULL,
    total_turns INT DEFAULT 1,
    rag_context_relevance NUMERIC(4, 3) DEFAULT 1.00,
    rag_faithfulness NUMERIC(4, 3) DEFAULT 1.00,
    rag_answer_relevance NUMERIC(4, 3) DEFAULT 1.00,
    policy_breach BOOLEAN DEFAULT FALSE,
    adversarial_intercepted BOOLEAN DEFAULT FALSE,
    final_agent_outcome VARCHAR(100),
    amount_recovered NUMERIC(12, 2) DEFAULT 0.00,
    langsmith_trace_url VARCHAR(500),
    execution_trace JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 4. 15 COMPLETE MERCHANT POLICY DOCUMENTS FOR MULTI-TENANT RAG

Create 15 Markdown files inside `backend/app/rag/documents/`. Ensure the RAG Retriever is configured to search the specific document linked to the active `merchant_id`. 

1. **`01_hotstar_policy.md`**: Plans (Mobile INR 149, Super INR 299, Premium INR 499). Max renewal discount INR 20. Pause up to 30 days.
2. **`02_netflix_india_policy.md`**: Plans (Mobile INR 149, Basic INR 199, Standard INR 499). Zero discounts. 48-hour retry window.
3. **`03_amazon_prime_policy.md`**: Plans (Monthly INR 299, Annual INR 1499). 5-day grace period for annual renewals.
4. **`04_spotify_india_policy.md`**: Plans (Individual INR 119, Duo INR 149, Student INR 59). 7-day grace buffer.
5. **`05_airtel_postpaid_policy.md`**: Late fee (INR 100) waived if paid in 24 hours via UPI link. Safe-custody pause up to 60 days.
6. **`06_jio_fiber_policy.md`**: 48-hour emergency data top-up link granted if bank network fails.
7. **`07_swiggy_one_policy.md`**: No split payments. 10% coupon concession (max INR 30) on annual renewals for high-LTV users.
8. **`08_zomato_gold_policy.md`**: 1-month free extension if mandate failed due to gateway timeout.
9. **`09_notion_saas_policy.md`**: Plans (Plus INR 800, Business INR 1500). Invoices over INR 10,000 can be split 50/50 payable 14 days apart. Zero discounts on seats.
10. **`10_slack_workspace_policy.md`**: Fair-billing inactive user credit applied before link generation. 5-day grace buffer.
11. **`11_zoho_one_policy.md`**: 10-day payment extension on annual contract renewal. Max concession 3%.
12. **`12_jira_atlassian_policy.md`**: 14-day formal invoice extension for verified corporate entities.
13. **`13_quickkart_b2b_policy.md`**: Net-30. Hold disputed portion (up to 20%), generate immediate Razorpay link for 80% balance. Prompt payment discount 3%.
14. **`14_udaan_wholesale_policy.md`**: 2-stage milestone settlement permitted for orders > INR 50,000 (40% immediate, 60% on day 15).
15. **`15_razorpayx_payroll_policy.md`**: Mandatory 5-day emergency grace period for salary disbursement accounts.

---

## 5. GATEWAY, GUARDRAILS & MCP ENGINE SPECIFICATIONS

### 1. LiteLLM Gateway (`gateway.py`)
* Configure `litellm.completion` to route to OpenRouter. Maintain an in-memory semantic cache keyed by SHA-256 of `(prompt + system_prompt)`. Set a token spend limit of 4,000 tokens per session.

### 2. Pre-LLM Guardrail (`pre_guardrails.py`)
* Regex and semantic check for injection attacks (e.g., `"system override"`, `"give 100% discount"`). If triggered, set `state["guardrail_status"] = "ADVERSARIAL_INTERCEPTED"` and return a safe refusal.

### 3. Post-LLM Invariant Guardrail (`post_guardrails.py`)
* Deterministic Python validator. Ensure the sum of `split_amounts` equals `proposed_amount`. Validate `proposed_discount_pct <= merchant.max_discount_pct`. Validate `proposed_grace_days <= merchant.max_grace_days`.

### 4. Razorpay MCP Client (`razorpay_mcp_client.py`)
* Simulate standard Razorpay MCP tool calls: `razorpay_create_payment_link(amount_in_inr, customer_id, description)`, `razorpay_fetch_subscription_status(subscription_id)`.

---

## 6. LANGGRAPH STATE MACHINE & MULTI-AGENT DESIGN

Define the `AutonomeState` TypedDict. Implement the cyclic node flow:
1. **Triage Node:** Analyzes failure reason code (`INSUFFICIENT_FUNDS`, `ISSUER_DOWN`, etc.).
2. **Policy RAG Retriever Node:** Queries the merchant's Markdown doc based on extracted customer intent keywords.
3. **Settlement Strategist Agent:** Negotiates multi-turn interactions. Clarifies vague objections using retrieved RAG choices. Outputs structured JSON.
4. **Post-Guardrail Node:** Runs deterministic validation.
5. **Razorpay MCP Tool Node:** Invokes `razorpay_create_payment_link` and formats final response.

---

## 7. 50 SYNTHETIC EVALUATION BENCHMARK & MULTI-TURN SIMULATIONS

### Multi-Turn Requirement (80-90% of Test Cases)
The vast majority of the 50 cases must be multi-turn (2 to 4 turns) to validate the agent's negotiation and RAG retrieval accuracy.

**Multi-Turn Examples (To be generated in `dataset_generator.py`):**
* **Case A (Hotstar Budget Friction):** 
  * Turn 1: Agent notifies INR 299 failure. Customer Proxy says, "I can't afford that right now." 
  * Turn 2: Agent retrieves `hotstar_policy.md`, asks if they want to pause or downgrade to Mobile (INR 149). Customer Proxy says, "Downgrade to mobile." 
  * Turn 3: Agent executes guardrails and creates INR 149 Razorpay link.
* **Case B (Notion SaaS Split Payment):** 
  * Turn 1: Agent notifies INR 15,000 Business plan failure. Customer Proxy says, "Our cash flow is tied up this week." 
  * Turn 2: Agent retrieves `notion_saas_policy.md`, offers a 50/50 split milestone. Customer Proxy agrees. 
  * Turn 3: Agent issues INR 7,500 link today and schedules INR 7,500 in 14 days.

### LangSmith Dataset Synchronization via Code
Implement `backend/app/evals/sync_langsmith_dataset.py` using the `langsmith` SDK to programmatically create the dataset:

```python
from langsmith import Client

def sync_dataset_to_langsmith(synthetic_cases: list[dict]):
    client = Client()
    dataset_name = "autonomepay-50-eval-benchmark"
    
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(dataset_name=dataset_name)
    else:
        dataset = client.read_dataset(dataset_name=dataset_name)
        
    for tc in synthetic_cases:
        client.create_example(
            inputs={"scenario_id": tc["scenario_id"], "merchant_id": tc["merchant_id"], "simulated_dialogue": tc["dialogue_script"]},
            outputs={"expected_action": tc["expected_action"], "expected_amount": tc["expected_amount"]},
            dataset_id=dataset.id
        )
```

### RAG Evaluation Triad & Multi-Turn Tracing (`judge.py` & `simulation_runner.py`)
* Wrap the simulation loop in LangChain’s `@traceable` decorator so every turn (Triage -> RAG -> Agent -> Guardrail -> MCP) appears as a nested child trace under the master session run in LangSmith.
* Implement an LLM-as-a-Judge to calculate the **RAG Triad Metrics** for every run:
  1. **Context Relevance:** Did the retrieved policy chunk match the customer's specific objection?
  2. **Faithfulness:** Did the agent's proposed plan/price exist exactly in the retrieved RAG chunk without hallucination?
  3. **Answer Relevance:** Did the agent's response directly address the customer's concern?

---

## 8. FRONTEND SPECIFICATION (React + Tailwind CSS)

Build a modern two-tab web interface:

### Tab 1: Interactive Concierge & Sandbox
* **Header:** Preset scenario selector dropdown (load specific Hotstar/Notion/QuickKart starting states).
* **Left Column (Context Card):** Displays live merchant name, customer tenure, failed plan, overdue amount, and active guardrail bounds.
* **Center Column (Interactive Chat):** WhatsApp-styled conversation feed with real-time typing indicators and clickable rendered Razorpay payment link pills.
* **Right Column (Live Trace Inspector):** Accordion showing Gateway Latency, Pre-Guardrail Check, RAG Retrieved Policy Chunks, Post-Guardrail Invariant Check, and MCP Tool Payload.

### Tab 2: Batch Evaluation Matrix & LangSmith Inspector
* **Top KPI Analytics Bar:** Total Invoiced, Total Recovered, Policy Breach Count (0), Adversarial Intercepts, RAG Faithfulness (%), Avg Latency / Run.
* **Batch Action Button:** `[ Run All 50 Evals ▶ ]` with a live progress bar.
* **50-Case Matrix Table:** Columns for `Test ID`, `Merchant`, `Turns`, `Outcome`, `Guardrail Status`, `Recovered INR`.
* **Trace Drawer Component:** Clicking `[View Trace]` on any row slides open a drawer containing the complete LangGraph execution graph, prompt payloads, retrieved RAG text, tool calls, and direct clickable LangSmith Trace URL.

---

## 9. EXECUTION INSTRUCTIONS FOR ANTIGRAVITY AGENT
1. Initialize the project structure, generate `backend/requirements.txt`, and scaffold `frontend/package.json`.
2. Write `backend/app/core/database.py` to connect to Neon PostgreSQL and create all DDL tables.
3. Generate all 15 Markdown policy files inside `backend/app/rag/documents/` and build `retriever.py`.
4. Implement `gateway.py`, `pre_guardrails.py`, and `post_guardrails.py` for invariant math verification.
5. Implement the LangGraph multi-agent engine (`state.py`, `triage_agent.py`, `rag_agent.py`, `settlement_agent.py`, `razorpay_mcp_client.py`).
6. Implement the evaluation module (`dataset_generator.py` focusing on 80% multi-turn cases, `sync_langsmith_dataset.py`, `simulation_runner.py`, and `judge.py` applying the RAG triad).
7. Build the FastAPI endpoints (`routes_chat.py`, `routes_scenarios.py`, `routes_evals.py`).
8. Build the complete React frontend.
9. Verify all API endpoints are connected, CORS is configured, and no placeholders remain.