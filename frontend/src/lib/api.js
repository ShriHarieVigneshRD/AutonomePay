import axios from 'axios';

// Empty VITE_API_BASE_URL means same origin (the Vite dev proxy forwards /api to the backend).
const http = axios.create({
  baseURL: `${import.meta.env.VITE_API_BASE_URL || ''}/api`,
  timeout: 120_000,
});

const data = (request) => request.then((res) => res.data);

export const api = {
  scenarios: () => data(http.get('/scenarios')),
  chat: (body) => data(http.post('/chat', body)),
  startConversation: (scenarioId) => data(http.post('/conversations', { scenario_id: scenarioId })),
  getConversation: (id) => data(http.get(`/conversations/${encodeURIComponent(id)}`)),
  sendMessage: (id, content) =>
    data(http.post(`/conversations/${encodeURIComponent(id)}/messages`, { content })),
  batches: () => data(http.get('/evals/batches')),
  results: (batchId) => data(http.get('/evals/results', { params: { batch_id: batchId } })),
  latestResults: () => data(http.get('/evals/latest')),
  // caseBatch 1-5 runs that batch of 10 cases; null runs all 50.
  runBenchmark: (caseBatch = null) =>
    data(http.post('/evals/run', null, { params: caseBatch ? { batch: caseBatch } : {} })),
  paymentStatus: (linkId) => data(http.get(`/payments/${encodeURIComponent(linkId)}`)),
  simulatePayment: (linkId) => data(http.post(`/payments/${encodeURIComponent(linkId)}/simulate-payment`)),
};

/** One readable sentence for any failed request. */
export function errorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (error?.response?.status === 429) return 'Too many requests. Please wait a moment.';
  if (error?.code === 'ECONNABORTED') return 'The server took too long to respond.';
  if (!error?.response) return 'Cannot reach the AutonomePay server. Check that the backend is running.';
  return `Request failed (${error.response.status}).`;
}

export function newSessionId() {
  return `s_${crypto.randomUUID().replaceAll('-', '')}`;
}
