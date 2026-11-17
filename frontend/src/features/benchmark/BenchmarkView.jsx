import { useState } from 'react';
import { Play, Lightning, ArrowSquareOut, ClockCounterClockwise, Clock } from '@phosphor-icons/react';
import { useBenchmark } from '../../hooks/useBenchmark';
import TraceDrawer from './TraceDrawer';

const fmt = (value, suffix = '') => (value === null || value === undefined ? '—' : `${value}${suffix}`);

export default function BenchmarkView() {
  const { batches, selectedId, results: data, error, starting, running, run, select, retry } = useBenchmark();
  const [selectedRow, setSelectedRow] = useState(null);

  const currentBatch = data?.batch || {};
  const kpi = data?.kpi || {};
  const matrix = data?.matrix || [];
  const loading = starting || currentBatch.status === 'RUNNING';
  const completedCount = currentBatch.completed_cases ?? matrix.length;
  const totalCount = currentBatch.total_cases || 50;
  const progressPct = Math.round((completedCount / totalCount) * 100);

  return (
    <div className="space-y-6">
      {/* Top KPI Analytics Bar */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <div className="glass-panel p-4 rounded-2xl border border-slate-800/80">
          <span className="text-slate-400 font-mono text-[10px] uppercase block">Total Invoiced</span>
          <span className="text-lg font-bold text-slate-100 font-mono">
            INR {fmt(kpi.total_invoiced?.toLocaleString('en-IN'))}
          </span>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800/80">
          <span className="text-slate-400 font-mono text-[10px] uppercase block">Total Recovered</span>
          <span className="text-lg font-bold text-emerald-400 font-mono">
            INR {fmt(kpi.total_recovered?.toLocaleString('en-IN'))}
          </span>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800/80">
          <span className="text-slate-400 font-mono text-[10px] uppercase block">Guardrail Corrections</span>
          <span className="text-lg font-bold text-emerald-400 font-mono">{fmt(kpi.policy_breaches)}</span>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800/80">
          <span className="text-slate-400 font-mono text-[10px] uppercase block">Adversarial Intercepts</span>
          <span className="text-lg font-bold text-amber-400 font-mono">
            {fmt(kpi.adversarial_intercepts)}
          </span>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800/80">
          <span className="text-slate-400 font-mono text-[10px] uppercase block">RAG Faithfulness</span>
          <span className="text-lg font-bold text-emerald-400 font-mono">
            {fmt(kpi.rag_faithfulness_pct, '%')}
          </span>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800/80">
          <span className="text-slate-400 font-mono text-[10px] uppercase block">Avg Latency / Run</span>
          <span className="text-lg font-bold text-slate-100 font-mono">{fmt(kpi.avg_latency_ms, ' ms')}</span>
        </div>
      </div>

      {/* Batch Runner Header & Version Selector */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800/80 flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center space-x-2">
            <Lightning className="w-5 h-5 text-emerald-400" weight="fill" />
            <span>50-Case Multi-Turn Synthetic Benchmark</span>
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Synchronized with LangSmith (
            <span className="text-emerald-400 font-semibold">autonomepay-50-eval-benchmark</span>)
          </p>
        </div>

        <div className="flex items-center space-x-4">
          {/* Run Version Selector Dropdown */}
          <div className="flex items-center space-x-2 bg-slate-950 px-3 py-2 rounded-xl border border-slate-800 text-xs">
            <ClockCounterClockwise className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-400 font-mono font-medium">Run Version:</span>
            <select
              value={selectedId || ''}
              onChange={(e) => select(e.target.value)}
              className="bg-transparent text-emerald-300 font-mono font-bold focus:outline-none cursor-pointer pr-2"
            >
              {batches.map((b) => (
                <option key={b.batch_id} value={b.batch_id} className="bg-slate-900 text-slate-100">
                  {b.name}{' '}
                  {b.status === 'RUNNING'
                    ? `(Evaluating ${b.completed_cases}/${b.total_cases})`
                    : `(${b.status.toLowerCase()})`}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={run}
            disabled={loading || running}
            className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 px-6 py-2.5 rounded-xl font-bold text-xs flex items-center space-x-2 transition-all transform active:scale-95 shadow-lg cursor-pointer shrink-0"
          >
            <Play className="w-4 h-4" weight="fill" />
            <span>{loading ? `Evaluating (${completedCount}/${totalCount})...` : 'Run New 50 Evals'}</span>
          </button>
        </div>
      </div>

      {/* Progress Bar for Active Run */}
      {loading && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-emerald-400 flex items-center space-x-1.5">
              <Clock className="w-3.5 h-3.5 animate-spin" />
              <span>
                Executing Benchmark Run: Case {completedCount} of {totalCount}...
              </span>
            </span>
            <span className="text-emerald-400 font-bold">{progressPct}%</span>
          </div>
          <div className="w-[100%] bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
            <div
              className="bg-emerald-500 h-full transition-all duration-500 shadow-[0_0_12px_#10b981]"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-xs text-rose-200"
        >
          {error}{' '}
          <button className="underline" onClick={retry}>
            Retry
          </button>
        </div>
      )}
      {!error && batches.length === 0 && (
        <p className="text-sm text-slate-400">No benchmark runs yet. Use the run button to start one.</p>
      )}

      {/* 50-Case Matrix Table */}
      <div className="glass-panel rounded-2xl border border-slate-800/80 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-[100%] text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 font-mono border-b border-slate-800 text-[11px]">
              <tr>
                <th className="p-4 font-semibold">Test ID</th>
                <th className="p-4 font-semibold">Scenario Type</th>
                <th className="p-4 font-semibold">Turns</th>
                <th className="p-4 font-semibold">Outcome</th>
                <th className="p-4 font-semibold">Guardrail Status</th>
                <th className="p-4 font-semibold">RAG Faithfulness</th>
                <th className="p-4 font-semibold">Recovered INR</th>
                <th className="p-4 font-semibold text-right">LangSmith Trace</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans text-slate-300">
              {matrix.map((row) => (
                <tr key={row.run_id} className="hover:bg-slate-900/60 transition-colors">
                  <td className="p-4 font-mono font-bold text-slate-100">{row.test_id}</td>
                  <td className="p-4 font-medium text-slate-200">{row.scenario_type}</td>
                  <td className="p-4 font-mono">{row.turns}</td>
                  <td className="p-4">
                    <span className="px-2.5 py-1 text-[10px] font-mono rounded-full bg-slate-900 text-slate-300 border border-slate-800">
                      {row.outcome}
                    </span>
                  </td>
                  <td className="p-4">
                    {row.guardrail_status === 'ADVERSARIAL_INTERCEPTED' ? (
                      <span className="px-2.5 py-1 text-[10px] font-mono rounded-full bg-rose-500/10 text-rose-300 border border-rose-500/30 font-semibold">
                        INTERCEPTED
                      </span>
                    ) : row.guardrail_status === 'POLICY_BREACH_CORRECTED' ? (
                      <span className="px-2.5 py-1 text-[10px] font-mono rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30 font-semibold">
                        CORRECTED
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 text-[10px] font-mono rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 font-semibold">
                        PASSED
                      </span>
                    )}
                  </td>
                  <td className="p-4 font-mono font-bold text-emerald-400">
                    {(row.rag_faithfulness * 100).toFixed(1)}%
                  </td>
                  <td className="p-4 font-mono font-bold text-slate-100">
                    INR {row.recovered_inr?.toFixed(2)}
                  </td>
                  <td className="p-4 text-right">
                    <button
                      onClick={() => setSelectedRow(row)}
                      className="inline-flex items-center space-x-1 font-mono text-[11px] text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/30 transition-all cursor-pointer"
                    >
                      <span>View Trace</span>
                      <ArrowSquareOut className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Slide-out Trace Drawer */}
      <TraceDrawer isOpen={Boolean(selectedRow)} onClose={() => setSelectedRow(null)} rowData={selectedRow} />
    </div>
  );
}
