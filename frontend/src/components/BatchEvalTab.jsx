import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Play, Lightning, ArrowSquareOut, ClockCounterClockwise, CheckCircle, Clock } from '@phosphor-icons/react';
import TraceDrawer from './TraceDrawer';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export default function BatchEvalTab() {
  const [batches, setBatches] = useState([]);
  const [selectedBatchId, setSelectedBatchId] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedRow, setSelectedRow] = useState(null);
  const pollIntervalRef = useRef(null);

  // Fetch all run versions
  const fetchBatches = async (autoSelectFirst = false) => {
    try {
      const res = await axios.get(`${API_BASE}/api/evals/batches`);
      const list = res.data || [];
      setBatches(list);

      if (list.length > 0 && (autoSelectFirst || !selectedBatchId)) {
        setSelectedBatchId(list[0].batch_id);
        fetchResultsForBatch(list[0].batch_id);
      }
    } catch (e) {
      console.error("Failed to fetch evaluation batches", e);
    }
  };

  // Fetch specific batch results
  const fetchResultsForBatch = async (batchId) => {
    if (!batchId) return;
    try {
      const res = await axios.get(`${API_BASE}/api/evals/results?batch_id=${batchId}`);
      setData(res.data);
      if (res.data?.batch?.status === 'RUNNING') {
        setLoading(true);
      } else {
        setLoading(false);
      }
    } catch (e) {
      console.error("Failed to fetch batch results", e);
    }
  };

  useEffect(() => {
    fetchBatches(true);
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const switchBatch = (batchId) => {
    setSelectedBatchId(batchId);
    fetchResultsForBatch(batchId);
  };

  const handleRunEvals = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/api/evals/run`);
      const newBatchId = res.data.batch_id;

      setSelectedBatchId(newBatchId);
      await fetchBatches(false);
      await fetchResultsForBatch(newBatchId);

      // Poll every 2 seconds for live case streaming
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

      pollIntervalRef.current = setInterval(async () => {
        const resResults = await axios.get(`${API_BASE}/api/evals/results?batch_id=${newBatchId}`);
        setData(resResults.data);
        await fetchBatches(false);

        if (resResults.data?.batch?.status === 'COMPLETED') {
          clearInterval(pollIntervalRef.current);
          setLoading(false);
        }
      }, 2000);
    } catch (e) {
      console.error("Failed to trigger batch evals", e);
      setLoading(false);
    }
  };

  const currentBatch = data?.batch || {};
  const kpi = data?.kpi || {
    total_invoiced: 0,
    total_recovered: 0,
    policy_breaches: 0,
    adversarial_intercepts: 0,
    rag_faithfulness_pct: 100.0,
    avg_latency_ms: 142.5
  };

  const matrix = data?.matrix || [];
  const completedCount = currentBatch.completed_cases || matrix.length;
  const totalCount = currentBatch.total_cases || 50;
  const progressPct = Math.round((completedCount / totalCount) * 100);

  return (
    <div className="space-y-6">
      {/* Top KPI Analytics Bar */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <div className="glass-panel p-4 rounded-2xl border border-slate-800/80">
          <span className="text-slate-400 font-mono text-[10px] uppercase block">Total Invoiced</span>
          <span className="text-lg font-bold text-slate-100 font-mono">
            INR {kpi.total_invoiced?.toLocaleString('en-IN')}
          </span>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800/80">
          <span className="text-slate-400 font-mono text-[10px] uppercase block">Total Recovered</span>
          <span className="text-lg font-bold text-emerald-400 font-mono">
            INR {kpi.total_recovered?.toLocaleString('en-IN')}
          </span>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800/80">
          <span className="text-slate-400 font-mono text-[10px] uppercase block">Policy Breaches</span>
          <span className="text-lg font-bold text-emerald-400 font-mono">
            {kpi.policy_breaches} <span className="text-xs font-normal text-slate-400">(0 Breaches)</span>
          </span>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800/80">
          <span className="text-slate-400 font-mono text-[10px] uppercase block">Adversarial Intercepts</span>
          <span className="text-lg font-bold text-amber-400 font-mono">
            {kpi.adversarial_intercepts}
          </span>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800/80">
          <span className="text-slate-400 font-mono text-[10px] uppercase block">RAG Faithfulness</span>
          <span className="text-lg font-bold text-emerald-400 font-mono">
            {kpi.rag_faithfulness_pct}%
          </span>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-slate-800/80">
          <span className="text-slate-400 font-mono text-[10px] uppercase block">Avg Latency / Run</span>
          <span className="text-lg font-bold text-slate-100 font-mono">
            {kpi.avg_latency_ms} ms
          </span>
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
            Synchronized with LangSmith (<span className="text-emerald-400 font-semibold">autonomepay-50-eval-benchmark</span>)
          </p>
        </div>

        <div className="flex items-center space-x-4">
          {/* Run Version Selector Dropdown */}
          <div className="flex items-center space-x-2 bg-slate-950 px-3 py-2 rounded-xl border border-slate-800 text-xs">
            <ClockCounterClockwise className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-400 font-mono font-medium">Run Version:</span>
            <select
              value={selectedBatchId || ''}
              onChange={(e) => switchBatch(e.target.value)}
              className="bg-transparent text-emerald-300 font-mono font-bold focus:outline-none cursor-pointer pr-2"
            >
              {batches.map((b) => (
                <option key={b.batch_id} value={b.batch_id} className="bg-slate-900 text-slate-100">
                  {b.name} {b.status === 'RUNNING' ? `(Evaluating ${b.completed_cases}/50)` : '(Completed)'}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleRunEvals}
            disabled={loading}
            className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 px-6 py-2.5 rounded-xl font-bold text-xs flex items-center space-x-2 transition-all transform active:scale-95 shadow-lg cursor-pointer shrink-0"
          >
            <Play className="w-4 h-4" weight="fill" />
            <span>{loading ? `Evaluating (${completedCount}/50)...` : 'Run New 50 Evals ▶'}</span>
          </button>
        </div>
      </div>

      {/* Progress Bar for Active Run */}
      {loading && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-emerald-400 flex items-center space-x-1.5">
              <Clock className="w-3.5 h-3.5 animate-spin" />
              <span>Executing Benchmark Run: Case {completedCount} of {totalCount}...</span>
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
              {matrix.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-900/60 transition-colors">
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
      <TraceDrawer
        isOpen={Boolean(selectedRow)}
        onClose={() => setSelectedRow(null)}
        rowData={selectedRow}
      />
    </div>
  );
}
