import { useCallback, useEffect, useState } from 'react';
import { api, errorMessage } from '../lib/api';

export const POLL_MS = 2000;
const MAX_POLL_FAILURES = 3;

/**
 * Benchmark runs: list, select, start, and poll the *selected* run while it is RUNNING.
 * Polling resumes when you come back to a running batch and always stops on unmount.
 */
export function useBenchmark() {
  const [batches, setBatches] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(false);

  const refreshBatches = useCallback(
    () =>
      api.batches().then((list) => {
        setBatches(list);
        return list;
      }),
    [],
  );

  const loadList = useCallback(
    () =>
      refreshBatches().then(
        (list) => {
          setSelectedId((current) => current ?? list[0]?.batch_id ?? null);
          setLoading(false);
        },
        (e) => {
          setError(errorMessage(e));
          setLoading(false);
        },
      ),
    [refreshBatches],
  );

  useEffect(() => {
    loadList();
  }, [loadList]);

  useEffect(() => {
    if (!selectedId) return undefined;
    let cancelled = false;
    let timer;
    let failures = 0;

    const tick = async () => {
      try {
        const data = await api.results(selectedId);
        if (cancelled) return;
        failures = 0;
        setResults(data);
        setError(null);
        refreshBatches().catch(() => {}); // keeps the run list's progress labels current
        if (data.batch.status === 'RUNNING') timer = setTimeout(tick, POLL_MS);
      } catch (e) {
        if (cancelled) return;
        failures += 1;
        if (failures >= MAX_POLL_FAILURES) setError(errorMessage(e));
        else timer = setTimeout(tick, POLL_MS);
      }
    };
    tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [selectedId, refreshBatches]);

  const select = (batchId) => {
    if (batchId === selectedId) return;
    setResults(null);
    setSelectedId(batchId);
  };

  const run = async () => {
    setStarting(true);
    setError(null);
    try {
      const batch = await api.runBenchmark();
      await refreshBatches();
      select(batch.batch_id);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setStarting(false);
    }
  };

  const retry = () => {
    setError(null);
    setLoading(true);
    loadList();
  };

  const running = batches.some((b) => b.status === 'RUNNING');
  return { batches, selectedId, results, loading, error, starting, running, run, select, retry };
}
