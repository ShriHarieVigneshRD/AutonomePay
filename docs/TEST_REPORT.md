# Test Report

## Phase 3 baseline (before any refactor), 2026-11-17

All tests run **offline**: no OpenRouter, Razorpay or LangSmith keys are used. The real `backend/.env` is overridden by test environment variables.

### Backend: `cd backend && .venv/Scripts/python -m pytest`
| Suite | Result |
|---|---|
| `test_characterization_api.py`: F1–F4, F5, F6, F8–F14 through HTTP | 19 passed |
| `test_characterization_units.py`: input/offer guards, retriever, gateway fallback chain + budget, seed data | 16 passed |
| `test_characterization_evals.py`: run → batches → results → LangSmith local mode | 5 passed |
| `test_known_bugs.py`: B1, B2, B3, B4, B5, B6, B7, B10, B11, B18, B26, S3, S4 written as correct behaviour | **20 xfailed (strict)** |
| **Total** | **40 passed, 20 xfailed, ~5 s** |

A new bug found while writing the safety net:
- **B26**: the "has the customer agreed?" check matches the substring `pay` inside `payment`. So "My payment failed." on the very first turn counts as consent and a payment link is issued (`settlement_agent.py:208`).

### Frontend e2e: `cd frontend && npx playwright test`
Playwright starts its own offline backend (temp DB, mock keys, LLM URL pointed at a local 404) and a Vite dev server. It uses the installed Chrome (`channel: 'chrome'`) at 1440×900.

| Test | Result |
|---|---|
| F25–F27 first scenario greeting + context card | passed |
| F27–F28 send message → reply + trace | passed |
| F28 prompt injection intercepted | passed |
| F25 scenario search → select Notion case | passed |
| F29–F30 run benchmark → 50 rows → open trace | passed |
| **Total** | **5 passed, ~21 s** |

Not covered at baseline:
- Mobile and tablet layouts are known broken (ANALYSIS §9) and get viewport projects after the redesign.
- `npm run lint` is broken (B24).
- There were no component unit tests yet.
