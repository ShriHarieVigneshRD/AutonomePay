import { useState } from 'react';
import { CaretDown, ChartBar, Play } from '@phosphor-icons/react';
import { Button } from '../../components/ui/Button';
import { EmptyState, ErrorState, Skeleton } from '../../components/ui/States';
import { useBenchmark } from '../../hooks/useBenchmark';
import { CaseLedger } from './CaseLedger';
import { ResultsTable } from './ResultsTable';
import { StatementStrip } from './StatementStrip';
import { TraceDrawer } from './TraceDrawer';

function runLabel(b) {
  if (b.status === 'RUNNING') return `${b.name} · running ${b.completed_cases}/${b.total_cases}`;
  return `${b.name} · ${b.status.toLowerCase()}`;
}

export function BenchmarkView() {
  const { batches, selectedId, results, loading, error, starting, running, run, select, retry } =
    useBenchmark();
  const [openRow, setOpenRow] = useState(null);
  const batch = results?.batch;
  const rows = results?.matrix ?? [];
  const progress = batch ? Math.round((100 * batch.completed_cases) / (batch.total_cases || 1)) : 0;

  return (
    <div className="mx-auto max-w-[1440px] space-y-4 p-3 md:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Benchmark</h1>
          <p className="max-w-[60ch] text-sm text-ink-3">
            50 scripted negotiations across 15 merchants, scored against policy. Every figure below is
            measured from the stored runs.
          </p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          {batches.length > 0 && (
            <label className="relative min-w-0 flex-1 sm:flex-none">
              <span className="sr-only">Benchmark run</span>
              <select
                value={selectedId ?? ''}
                onChange={(e) => select(e.target.value)}
                className="h-9 w-full appearance-none rounded-control border border-rule/15 bg-sheet pl-3 pr-8 text-sm max-md:h-11 sm:w-72"
              >
                {batches.map((b) => (
                  <option key={b.batch_id} value={b.batch_id}>
                    {runLabel(b)}
                  </option>
                ))}
              </select>
              <CaretDown
                className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3"
                aria-hidden
              />
            </label>
          )}
          <Button variant="primary" onClick={run} disabled={starting || running}>
            <Play className="h-4 w-4" weight="fill" aria-hidden />
            {running ? 'Run in progress' : 'Run benchmark'}
          </Button>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={retry} />}

      {batch?.status === 'RUNNING' && (
        <div className="rounded-panel border border-rule/10 bg-sheet p-4">
          <div className="flex justify-between text-xs text-ink-2">
            <span>
              Running case {batch.completed_cases} of {batch.total_cases}
            </span>
            <span className="num">{progress}%</span>
          </div>
          <div
            role="progressbar"
            aria-label="Benchmark progress"
            aria-valuemin={0}
            aria-valuemax={batch.total_cases}
            aria-valuenow={batch.completed_cases}
            className="mt-2 h-1.5 overflow-hidden rounded-full bg-accent/15"
          >
            <div
              className="h-full rounded-full bg-accent transition-[width] duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {loading ? (
        <div className="space-y-4" aria-label="Loading benchmark runs">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : batches.length === 0 && !error ? (
        <div className="rounded-panel border border-rule/10 bg-sheet">
          <EmptyState
            icon={ChartBar}
            title="No benchmark runs yet"
            action={
              <Button variant="primary" className="mt-2" onClick={run} disabled={starting}>
                <Play className="h-4 w-4" weight="fill" aria-hidden />
                Run the 50-case benchmark
              </Button>
            }
          >
            The run takes a few seconds offline, or a few minutes with a live LLM. Results stream in as each
            case finishes.
          </EmptyState>
        </div>
      ) : results ? (
        <>
          <StatementStrip kpi={results.kpi ?? {}} totalCases={batch?.total_cases ?? rows.length} />
          <CaseLedger rows={rows} total={batch?.total_cases ?? 50} onOpen={setOpenRow} />
          {rows.length > 0 && <ResultsTable rows={rows} onOpen={setOpenRow} />}
        </>
      ) : (
        !error && <Skeleton className="h-40 w-full" />
      )}

      <TraceDrawer row={openRow} onClose={() => setOpenRow(null)} />
    </div>
  );
}
