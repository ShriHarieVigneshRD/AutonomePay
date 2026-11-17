import { defineConfig, devices } from '@playwright/test';
import os from 'node:os';
import path from 'node:path';

// The backend runs fully offline: no LLM key, LLM base URL pointed at a 404 path,
// mock Razorpay keys, throwaway SQLite DB. The real backend/.env keys are overridden.
const BACKEND_PORT = 8799;
const FRONTEND_PORT = 5199;
const python =
  process.env.PYTHON ??
  (process.platform === 'win32' ? path.normalize('.venv/Scripts/python.exe') : '.venv/bin/python');
const dbFile = path.join(os.tmpdir(), `autonomepay-e2e-${Date.now()}.db`).replaceAll('\\', '/');

export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    channel: process.env.PW_CHANNEL ?? 'chrome',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    {
      name: 'tablet',
      testMatch: /responsive/,
      use: { ...devices['Desktop Chrome'], viewport: { width: 820, height: 1180 }, hasTouch: true },
    },
    {
      name: 'mobile',
      testMatch: /responsive/,
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 390, height: 844 },
        hasTouch: true,
        isMobile: true,
      },
    },
  ],
  webServer: [
    {
      command: `${python} -m uvicorn app.main:app --port ${BACKEND_PORT}`,
      cwd: '../backend',
      url: `http://127.0.0.1:${BACKEND_PORT}/`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        DATABASE_URL: `sqlite:///${dbFile}`,
        OPENROUTER_API_KEY: '',
        // A 404 from our own backend fails fast; a closed port takes ~2 s per attempt on Windows.
        OPENROUTER_API_BASE: `http://127.0.0.1:${BACKEND_PORT}/__offline_llm__`,
        RAZORPAY_KEY_ID: 'rzp_test_mock12345',
        RAZORPAY_KEY_SECRET: 'mock_secret',
        LANGCHAIN_API_KEY: '',
        LANGSMITH_API_KEY: '',
        LANGCHAIN_TRACING_V2: 'false',
        LANGSMITH_TRACING: 'false',
        CORS_ORIGINS: `http://localhost:${FRONTEND_PORT}`,
        PUBLIC_APP_URL: `http://localhost:${FRONTEND_PORT}`,
        RAZORPAY_MCP_MODE: 'embedded',
        RAG_MODE: 'bm25', // model-backed retrieval is covered by the backend's slow test
      },
    },
    {
      command: `npx vite --port ${FRONTEND_PORT} --strictPort`,
      url: `http://localhost:${FRONTEND_PORT}/`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: { VITE_API_BASE_URL: `http://127.0.0.1:${BACKEND_PORT}` },
    },
  ],
});
