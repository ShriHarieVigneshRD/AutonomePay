import React from 'react';
import { X, ArrowSquareOut, Lightning, ShieldCheck, CheckCircle } from '@phosphor-icons/react';

export default function TraceDrawer({ isOpen, onClose, rowData }) {
  if (!isOpen || !rowData) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/80 backdrop-blur-sm transition-opacity">
      <div className="w-[100%] max-w-xl bg-[#0d1322] border-l border-slate-800 h-[100dvh] flex flex-col shadow-2xl p-6 overflow-y-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <Lightning className="w-5 h-5 text-emerald-400" weight="fill" />
              <h2 className="text-base font-bold text-slate-100">LangGraph Execution Trace</h2>
            </div>
            <p className="text-xs text-slate-400 font-mono">Test ID: {rowData.test_id}</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-slate-800 text-slate-400 hover:text-slate-100 flex items-center justify-center cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* LangSmith Link */}
        {rowData.langsmith_trace_url && (
          <a
            href={rowData.langsmith_trace_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between glass-pill p-3.5 rounded-xl text-emerald-300 font-bold text-xs hover:border-emerald-400/60 transition-all"
          >
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
              <span>Inspect Live LangSmith Trace Run</span>
            </div>
            <ArrowSquareOut className="w-4 h-4" />
          </a>
        )}

        {/* Trace Details Summary */}
        <div className="grid grid-cols-2 gap-3 font-mono text-xs">
          <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-400 block text-[10px] uppercase">Scenario</span>
            <span className="text-slate-100 font-bold">{rowData.scenario_type}</span>
          </div>
          <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-400 block text-[10px] uppercase">Guardrail Status</span>
            <span className="text-emerald-400 font-bold">{rowData.guardrail_status}</span>
          </div>
          <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-400 block text-[10px] uppercase">RAG Faithfulness</span>
            <span className="text-emerald-400 font-bold">{(rowData.rag_faithfulness * 100).toFixed(1)}%</span>
          </div>
          <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-400 block text-[10px] uppercase">Recovered Amount</span>
            <span className="text-emerald-400 font-bold">INR {rowData.recovered_inr?.toFixed(2)}</span>
          </div>
        </div>

        {/* Multi-turn Execution Trace Log */}
        <div className="space-y-4">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Multi-Turn Step Execution</h3>
          <div className="space-y-3">
            {rowData.execution_trace?.map((step, idx) => (
              <div key={idx} className="bg-slate-900/80 rounded-xl p-4 border border-slate-800 space-y-2 text-xs">
                <div className="flex items-center justify-between text-slate-400 font-mono text-[10px]">
                  <span>Turn #{step.turn}</span>
                  <span>{step.latency_ms} ms</span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800 text-slate-300">
                  <span className="text-emerald-400 font-bold block text-[10px]">Customer Proxy Input:</span>
                  <p>{step.user}</p>
                </div>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800 text-slate-200">
                  <span className="text-emerald-400 font-bold block text-[10px]">Agent Output:</span>
                  <p>{step.agent}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
