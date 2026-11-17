import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../lib/api';
import { POLL_MS, useBenchmark } from './useBenchmark';

vi.mock('../lib/api', async (importOriginal) => ({
  ...(await importOriginal()),
  api: { batches: vi.fn(), results: vi.fn(), runBenchmark: vi.fn() },
}));

const batch = (id, status, completed = 0) => ({
  batch_id: id,
  name: id,
  status,
  total_cases: 50,
  completed_cases: completed,
});
const results = (id, status) => ({ batch: batch(id, status), kpi: {}, matrix: [] });
const flush = () => act(() => vi.advanceTimersByTimeAsync(0));
const tickPoll = () => act(() => vi.advanceTimersByTimeAsync(POLL_MS));

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe('useBenchmark', () => {
  it('B14: resumes polling a running batch on mount and stops when it completes', async () => {
    api.batches.mockResolvedValue([batch('b1', 'RUNNING', 10)]);
    api.results.mockResolvedValueOnce(results('b1', 'RUNNING')).mockResolvedValue(results('b1', 'COMPLETED'));
    const { result } = renderHook(() => useBenchmark());
    await flush();
    expect(result.current.selectedId).toBe('b1');
    expect(api.results).toHaveBeenCalledTimes(1);
    await tickPoll();
    expect(result.current.results.batch.status).toBe('COMPLETED');
    await tickPoll();
    await tickPoll();
    expect(api.results).toHaveBeenCalledTimes(2); // no polling after completion
  });

  it('B15: selecting another run stops polling the old one', async () => {
    api.batches.mockResolvedValue([batch('b2', 'RUNNING'), batch('b1', 'COMPLETED')]);
    api.results.mockImplementation((id) =>
      Promise.resolve(results(id, id === 'b2' ? 'RUNNING' : 'COMPLETED')),
    );
    const { result } = renderHook(() => useBenchmark());
    await flush();
    act(() => result.current.select('b1'));
    await flush();
    expect(result.current.results.batch.batch_id).toBe('b1');
    api.results.mockClear();
    await tickPoll();
    await tickPoll();
    expect(api.results).not.toHaveBeenCalled();
    expect(result.current.results.batch.batch_id).toBe('b1');
  });

  it('stops polling and reports an error after repeated failures', async () => {
    api.batches.mockResolvedValue([batch('b1', 'RUNNING')]);
    api.results.mockRejectedValue(new Error('offline'));
    const { result } = renderHook(() => useBenchmark());
    await flush();
    await tickPoll();
    await tickPoll();
    expect(result.current.error).toMatch(/cannot reach/i);
    await tickPoll();
    expect(api.results).toHaveBeenCalledTimes(3);
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
});
