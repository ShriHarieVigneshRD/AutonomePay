import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../lib/api';
import { LATEST, POLL_MS, nextBatch, useBenchmark } from './useBenchmark';

vi.mock('../lib/api', async (importOriginal) => ({
  ...(await importOriginal()),
  api: { batches: vi.fn(), results: vi.fn(), latestResults: vi.fn(), runBenchmark: vi.fn() },
}));

const batch = (id, status, completed = 0, extra = {}) => ({
  batch_id: id,
  name: id,
  status,
  total_cases: 50,
  completed_cases: completed,
  ...extra,
});
const latest = (running) => ({ kpi: {}, matrix: [], coverage: { evaluated: 0, total: 50 }, running });
const results = (id, status) => ({ batch: batch(id, status), kpi: {}, matrix: [] });
const flush = () => act(() => vi.advanceTimersByTimeAsync(0));
const tickPoll = () => act(() => vi.advanceTimersByTimeAsync(POLL_MS));

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe('useBenchmark', () => {
  it('B14: opens on the latest results and polls them while a run is in progress', async () => {
    api.batches.mockResolvedValue([batch('b1', 'RUNNING', 10)]);
    api.latestResults.mockResolvedValueOnce(latest(true)).mockResolvedValue(latest(false));
    const { result } = renderHook(() => useBenchmark());
    await flush();
    expect(result.current.selectedId).toBe(LATEST);
    expect(api.latestResults).toHaveBeenCalledTimes(1);
    await tickPoll();
    expect(result.current.results.running).toBe(false);
    await tickPoll();
    await tickPoll();
    expect(api.latestResults).toHaveBeenCalledTimes(2); // no polling once nothing is running
  });

  it('B14: resumes polling a selected running batch and stops when it completes', async () => {
    api.batches.mockResolvedValue([batch('b1', 'RUNNING', 10)]);
    api.latestResults.mockResolvedValue(latest(false));
    api.results.mockResolvedValueOnce(results('b1', 'RUNNING')).mockResolvedValue(results('b1', 'COMPLETED'));
    const { result } = renderHook(() => useBenchmark());
    await flush();
    act(() => result.current.select('b1'));
    await flush();
    await tickPoll();
    expect(result.current.results.batch.status).toBe('COMPLETED');
    await tickPoll();
    expect(api.results).toHaveBeenCalledTimes(2);
  });

  it('B15: selecting another run stops polling the old one', async () => {
    api.batches.mockResolvedValue([batch('b2', 'RUNNING'), batch('b1', 'COMPLETED')]);
    api.latestResults.mockResolvedValue(latest(true));
    api.results.mockImplementation((id) =>
      Promise.resolve(results(id, id === 'b2' ? 'RUNNING' : 'COMPLETED')),
    );
    const { result } = renderHook(() => useBenchmark());
    await flush();
    act(() => result.current.select('b1'));
    await flush();
    expect(result.current.results.batch.batch_id).toBe('b1');
    api.results.mockClear();
    api.latestResults.mockClear();
    await tickPoll();
    await tickPoll();
    expect(api.results).not.toHaveBeenCalled();
    expect(api.latestResults).not.toHaveBeenCalled();
    expect(result.current.results.batch.batch_id).toBe('b1');
  });

  it('stops polling and reports an error after repeated failures', async () => {
    api.batches.mockResolvedValue([batch('b1', 'RUNNING')]);
    api.latestResults.mockRejectedValue(new Error('offline'));
    const { result } = renderHook(() => useBenchmark());
    await flush();
    await tickPoll();
    await tickPoll();
    expect(result.current.error).toMatch(/cannot reach/i);
    await tickPoll();
    expect(api.latestResults).toHaveBeenCalledTimes(3);
  });

  it('shows the server reason when a run cannot start', async () => {
    api.batches.mockResolvedValue([]);
    api.runBenchmark.mockRejectedValue({
      response: { status: 409, data: { detail: 'A benchmark run is already in progress.' } },
    });
    const { result } = renderHook(() => useBenchmark());
    await flush();
    expect(result.current.selectedId).toBeNull();
    await act(() => result.current.run());
    expect(result.current.error).toBe('A benchmark run is already in progress.');
  });

  it('starts the chosen batch', async () => {
    api.batches.mockResolvedValue([]);
    api.runBenchmark.mockResolvedValue(batch('b9', 'RUNNING', 0, { case_batch: 3 }));
    api.results.mockResolvedValue(results('b9', 'COMPLETED'));
    const { result } = renderHook(() => useBenchmark());
    await flush();
    await act(() => result.current.run(3));
    expect(api.runBenchmark).toHaveBeenCalledWith(3);
    expect(result.current.selectedId).toBe('b9');
  });
});

describe('nextBatch', () => {
  it('suggests a batch never run, else the one run longest ago', () => {
    const run = (n, day) =>
      batch(`b${n}${day}`, 'COMPLETED', 10, { case_batch: n, created_at: `2026-11-${day}` });
    expect(nextBatch([])).toBe(1);
    expect(nextBatch([run(2, 18), run(1, 17)])).toBe(3);
    const all = [run(3, 20), run(2, 19), run(5, 16), run(4, 15), run(1, 17)]; // newest first
    expect(nextBatch(all)).toBe(4);
  });
});
