import { useState } from 'react';
import { CaretDown, ChartBar, Play } from '@phosphor-icons/react';
import { Button } from '../../components/ui/Button';
import { EmptyState, ErrorState, Skeleton } from '../../components/ui/States';
import { BATCH_COUNT, LATEST, nextBatch, useBenchmark } from '../../hooks/useBenchmark';
import { pct } from '../../lib/format';
import { CaseLedger } from './CaseLedger';
import { ResultsTable } from './ResultsTable';
import { StatementStrip } from './StatementStrip';
import { TraceDrawer } from './TraceDrawer';

const BATCHES = Array.from({ length: BATCH_COUNT }, (_, i) => i + 1);
const day = (iso) => new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });

function runLabel(b) {
  if (b.status === 'RUNNING') return `${b.name} · running ${b.completed_cases}/${b.total_cases}`;
  return `${b.name} · ${b.status.toLowerCase()}`;
}

/** "Batch 2 · 90% · 17 Nov" from that batch's most recent run (`batches` is newest first). */
function batchLabel(n, batches) {
  const last = batches.find((b) => b.case_batch === n);
  if (!last) return `Batch ${n} of ${BATCH_COUNT} · not run yet`;
  const score = last.kpis?.pass_rate_pct;
  return `Batch ${n} of ${BATCH_COUNT} · ${score !== null && score !== undefined ? `${pct(score)} · ` : ''}${day(last.created_at)}`;
}

function Select({ label, value, onChange, className, children }) {
  return (
    <label className={`relative w-full min-w-0 sm:w-auto ${className}`}>
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full appearance-none rounded-control border border-rule/15 bg-sheet pl-3 pr-8 text-sm max-md:h-11"
      >
        {children}
      </select>
      <CaretDown
        className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3"
        aria-hidden
      />
    </label>
  );
}

export function BenchmarkView() {
  const { batches, selectedId, results, loading, error, starting, running, run, select, retry } =
    useBenchmark();
  const [openRow, setOpenRow] = useState(null);
  const [scope, setScope] = useState(null); // null = the suggested next batch
  const toRun = scope ?? String(nextBatch(batches));
  const startRun = () => run(toRun === 'all' ? null : Number(toRun));

  const isLatest = selectedId === LATEST;
  const rows = results?.matrix ?? [];
  const active = batches.find((b) => b.status === 'RUNNING');
  const progress = active ? Math.round((100 * active.completed_cases) / (active.total_cases || 1)) : 0;
  const coverage = results?.coverage;
  const versions = results?.code_versions ?? [];

  return (
    <div className="mx-auto max-w-[1440px] space-y-4 p-3 md:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Benchmark</h1>
          <p className="max-w-[60ch] text-sm text-ink-3">
            50 scripted negotiations across 15 merchants, run in {BATCH_COUNT} batches of 10 and scored
            against policy. Every figure below is measured from the stored runs.
          </p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          {batches.length > 0 && (
            <Select label="Results to show" value={selectedId ?? ''} onChange={select} className="sm:w-72">
              <option value={LATEST}>Latest results · all batches</option>
              {batches.map((b) => (
                <option key={b.batch_id} value={b.batch_id}>
                  {runLabel(b)}
                </option>
              ))}
            </Select>
          )}
          <Select label="Cases to run" value={toRun} onChange={setScope} className="sm:w-60">
            {BATCHES.map((n) => (
              <option key={n} value={String(n)}>
                {batchLabel(n, batches)}
              </option>
            ))}
            <option value="all">All 50 cases</option>
          </Select>
          <Button
            variant="primary"
            className="max-sm:w-full"
            onClick={startRun}
            disabled={starting || running}
          >
            <Play className="h-4 w-4" weight="fill" aria-hidden />
            {running ? 'Run in progress' : 'Run benchmark'}
          </Button>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={retry} />}

      {active && (
        <div className="rounded-panel border border-rule/10 bg-sheet p-4">
          <div className="flex justify-between gap-3 text-xs text-ink-2">
            <span>
              Running case {active.completed_cases} of {active.total_cases} · {active.name}
            </span>
            <span className="num">{progress}%</span>
          </div>
          <div
            role="progressbar"
            aria-label="Benchmark progress"
            aria-valuemin={0}
            aria-valuemax={active.total_cases}
            aria-valuenow={active.completed_cases}
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
              <Button variant="primary" className="mt-2" onClick={startRun} disabled={starting}>
                <Play className="h-4 w-4" weight="fill" aria-hidden />
                {toRun === 'all' ? 'Run all 50 cases' : `Run batch ${toRun} (10 cases)`}
              </Button>
            }
          >
            Each batch is every 5th case, so it covers most merchants. The Latest results view combines the
            batches into one 50-case scorecard. A batch takes a few seconds offline, or several minutes with a
            live LLM.
          </EmptyState>
        </div>
      ) : results ? (
        <>
          <StatementStrip
            kpi={results.kpi ?? {}}
            casesLabel={
              isLatest
                ? `${coverage?.evaluated ?? 0} of ${coverage?.total ?? 50} cases`
                : `${results.batch?.total_cases ?? rows.length} cases`
            }
          />
          {isLatest && versions.length > 1 && (
            <p className="rounded-panel border border-caution/40 bg-caution/10 px-4 py-2.5 text-sm text-ink-2">
              These results come from {versions.length} code versions ({versions.join(', ')}). Rerun the older
              batches to compare like with like.
            </p>
          )}
          <CaseLedger
            rows={rows}
            total={coverage?.total ?? 50}
            pendingLabel={isLatest ? 'Not run yet' : 'Not in this run'}
            onOpen={setOpenRow}
          />
          {rows.length > 0 && <ResultsTable rows={rows} onOpen={setOpenRow} />}
        </>
      ) : (
        !error && <Skeleton className="h-40 w-full" />
      )}

      <TraceDrawer row={openRow} onClose={() => setOpenRow(null)} />
    </div>
  );
}
