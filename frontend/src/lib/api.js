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
  batches: () => data(http.get('/evals/batches')),
  results: (batchId) => data(http.get('/evals/results', { params: { batch_id: batchId } })),
  runBenchmark: () => data(http.post('/evals/run')),
};
