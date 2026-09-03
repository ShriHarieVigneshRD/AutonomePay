import React from 'react';
import { Storefront, User, Receipt, ShieldCheck } from '@phosphor-icons/react';

export default function ContextCard({ scenario }) {
  if (!scenario) return null;

  return (
    <div className="glass-panel rounded-2xl p-4 flex flex-col h-full border border-slate-800/80 overflow-hidden justify-between">
      <div className="space-y-4 overflow-y-auto pr-1">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
              <Storefront className="w-5 h-5" weight="duotone" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 truncate max-w-[160px]">{scenario.merchant_name}</h3>
              <span className="text-xs text-slate-400 font-mono block">{scenario.category}</span>
            </div>
          </div>
          <span className="px-2.5 py-1 text-[10px] font-mono font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
            ACTIVE RAG
          </span>
        </div>

        {/* Customer & Invoice details */}
        <div className="grid grid-cols-1 gap-2.5 text-xs">
          <div className="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/50 flex items-center justify-between">
            <div className="flex items-center space-x-2 text-slate-300">
              <User className="w-4 h-4 text-emerald-400 shrink-0" />
              <span className="font-medium">Customer:</span>
            </div>
            <span className="font-semibold text-slate-100 truncate max-w-[140px]">{scenario.customer_name}</span>
          </div>

          <div className="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/50 flex items-center justify-between">
            <div className="flex items-center space-x-2 text-slate-300">
              <Receipt className="w-4 h-4 text-amber-400 shrink-0" />
              <span className="font-medium">Overdue Plan:</span>
            </div>
            <span className="font-semibold text-amber-300 truncate max-w-[140px]">{scenario.plan_name}</span>
          </div>

          <div className="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/50 flex items-center justify-between">
            <span className="text-slate-400 font-medium">Invoice Amount:</span>
            <span className="font-mono text-base font-bold text-emerald-400">
              INR {scenario.original_amount?.toFixed(2)}
            </span>
          </div>

          <div className="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/50 flex items-center justify-between">
            <span className="text-slate-400 font-medium">Failure Code:</span>
            <span className="font-mono text-xs text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
              {scenario.failure_code}
            </span>
          </div>
        </div>
      </div>

      {/* Active Invariant Guardrail Bounds Footer */}
      <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800/90 space-y-2 mt-4">
        <div className="flex items-center space-x-2 text-xs font-bold text-slate-200">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Non-LLM Invariant Bounds</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
          <div className="bg-slate-900 p-2 rounded border border-slate-800 text-slate-300">
            <span className="text-slate-400 block text-[9px] uppercase">Max Discount</span>
            <span className="text-emerald-400 font-bold">{scenario.max_discount_pct}%</span>
          </div>
          <div className="bg-slate-900 p-2 rounded border border-slate-800 text-slate-300">
            <span className="text-slate-400 block text-[9px] uppercase">Max Grace</span>
            <span className="text-emerald-400 font-bold">{scenario.max_grace_days} Days</span>
          </div>
        </div>
      </div>
    </div>
  );
}
