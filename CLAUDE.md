# CLAUDE.md

Guidance for working on AutonomePay: a FastAPI + LangGraph backend and a React (Vite + Tailwind) frontend. See README.md for the product and docs/ for analysis, plan, test report and changelog.

## Commands

Backend (run from `backend/`, venv at `backend/.venv`):
```bash
uvicorn app.main:app --reload --port 8000     # API at :8000, docs at /docs
pytest                                         # offline suite (~5 s); `-m slow` for model-backed retrieval
ruff check app tests && ruff format app tests && pyright
python -m app.rag.ingest [--merchant ID]       # refresh web policy snapshots (needs requirements-ingest.txt)
python -m app.evals.retrieval_eval             # retrieval quality per RAG_MODE
python -m app.payments.mcp_server              # run the payments MCP server standalone over stdio
```

Frontend (run from `frontend/`):
```bash
npm run dev          # :5173, proxies /api to :8000
npm test             # Vitest
npm run lint         # ESLint (--max-warnings 0)
npm run format       # Prettier (format:check in CI)
npm run build
npm run test:e2e     # Playwright; starts its own offline backend (:8799) and Vite (:5199)
```

## Structure

- `backend/app/api/`: routes. `chat.py` (stateless, compatibility), `conversations.py` (server-side history, preferred), `scenarios.py`, `evals.py`, `payments.py`. `schemas.py` and `deps.py` hold request validation, the rate limiter and the admin token.
- `backend/app/agents/`: LangGraph graph `triage → retrieval → settlement`. `settlement/` is split into `prompt.py`, `offer.py` (pure helpers) and `node.py` (orchestration).
- `backend/app/guardrails/`: `input_guard.py` (injection screen) and `offer_guard.py` (deterministic offer rules, driven by `MerchantRules`).
- `backend/app/payments/`: `mcp_server.py` (our MCP server), `mcp_client.py` (the agent's MCP client; embedded/remote/stdio), `razorpay.py` (live API adapter), `ledger.py` (payment_links bookkeeping).
- `backend/app/rag/`: `chunking.py` (corpus = curated `policies/` + web `sources/` + generated limits chunk), `retriever.py` (bm25 / hybrid / hybrid_rerank), `ingest.py`.
- `backend/app/core/`: `config.py` (pydantic-settings only), `database.py` (typed models), `migrations.py` (additive columns), `seed.py`, `catalog.py`, `llm_gateway.py`.
- `backend/app/data/merchants.json`: **single source of truth** for merchant limits, plans, split/partial rules, demo invoices and public policy URLs. Synced to the DB on every start.
- `frontend/src/`: `features/{sandbox,benchmark,checkout}`, `hooks/` (all data fetching and state), `components/ui/` (shared kit), `lib/` (api client, formatting, theme, routing), `styles/index.css` (design tokens).

## Invariants (don't break these)

- **Link amount.** A payment link is created only for `offer_guard`'s `corrected_offer["proposed_amount"]`, only with `user_gave_consent(...)`, and never for escalations or cancellations. Never derive an amount from LLM text.
- **Merchant data.** All merchant numbers come from `merchants.json` → DB → `MerchantRules`. Don't hard-code limits in prompts, the UI or tests; read them.
- **Untrusted text.** Retrieved policy text and LLM output are untrusted. URLs written by the LLM are stripped; web snapshots are injection-screened at ingest.
- **Offline tests.** Tests never touch the network or real keys. `tests/conftest.py` sets env vars before importing `app` and patches `litellm.completion`. Use the `llm_reply` fixture to script a model reply. Model-dependent tests are marked `slow`.
- **Schema changes.** Add-only. New tables come from `create_all`; new columns go in `core/migrations.py:ADDED_COLUMNS` and must be nullable or defaulted.
- **API compatibility.** Response fields are snake_case and additive; don't rename existing ones (the frontend and older clients rely on them).

## Conventions

- **Python:** type hints on public functions, `logging.getLogger(__name__)`, no `print` outside CLIs, ruff line length 110. Comment only the non-obvious *why*.
- **React:**
  - Function components with named exports, one per file.
  - Data fetching and state live in `hooks/`, and all HTTP goes through `lib/api.js`.
  - Native elements first (`<button>`, `<a>`, `<dialog>`, `<details>`).
- **Styling:** design tokens only (`bg-sheet`, `text-ink-2`, `border-rule/10`, `bg-accent`, `text-settled|caution-ink|void`). Never raw hex or Tailwind palette colours.
  - Status colours are reserved for status and always come with an icon and a label.
  - See `.interface-design/system.md` for the type scale, spacing, radius and motion rules.
- **Bugs:** a fix comes with a regression test (`backend/tests/test_regressions.py` or next to the feature). New features come with tests.
- **Commits:** small and focused, with conventional prefixes (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).

## Gotchas

- On Windows, scripted file edits must write UTF-8 explicitly (the default code page corrupts `₹` and `—`). Prefer the editor tools for anything containing backslash escapes.
- `RAG_MODE=hybrid*` loads ONNX models. Embed in small batches (`EMBED_BATCH`); large batches grow ONNX Runtime's memory arena to GBs. Measured memory: bm25 ~290 MB, hybrid ~555 MB, hybrid_rerank ~700 MB.
- In tests, `PUBLIC_APP_URL`, `RAZORPAY_MCP_MODE=embedded` and `RAG_MODE=bm25` are pinned in `conftest.py` and `playwright.config.js`. A developer's `.env` must not leak into tests.
- Razorpay test mode caps an account at 30 payment links. When live link creation fails, the app reports `LINK_FAILED` and never shows a fake link.
