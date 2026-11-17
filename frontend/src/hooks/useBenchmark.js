import { useCallback, useEffect, useState } from 'react';
import { api, errorMessage } from '../lib/api';

export const POLL_MS = 2000;
const MAX_POLL_FAILURES = 3;
export const LATEST = 'latest'; // the view combining each case's most recent result
export const BATCH_COUNT = 5;

/** The batch to run next: one never run, else the one run longest ago (`batches` is newest first). */
export function nextBatch(batches) {
  const lastRun = (n) => batches.find((b) => b.case_batch === n)?.created_at ?? '';
  return Array.from({ length: BATCH_COUNT }, (_, i) => i + 1).reduce(
    (best, n) => (lastRun(n) < lastRun(best) ? n : best),
    1,
  );
}

/**
 * Benchmark runs: list, select, start, and poll the selected view while a run is in progress.
 * The default view is LATEST (each case's most recent result across runs). Polling resumes when
 * you come back to a running batch and always stops on unmount.
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
          setSelectedId((current) => current ?? (list.length ? LATEST : null));
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
        const latest = selectedId === LATEST;
        const data = await (latest ? api.latestResults() : api.results(selectedId));
        if (cancelled) return;
        failures = 0;
        setResults(data);
        setError(null);
        refreshBatches().catch(() => {}); // keeps the run list's progress labels current
        if (latest ? data.running : data.batch.status === 'RUNNING') timer = setTimeout(tick, POLL_MS);
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

  const run = async (caseBatch = null) => {
    setStarting(true);
    setError(null);
    try {
      const batch = await api.runBenchmark(caseBatch);
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
