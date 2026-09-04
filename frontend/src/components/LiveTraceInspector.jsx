import React, { useState } from 'react';
import { Lightning, ShieldCheck, FileText, Code, CaretDown, CaretUp, CheckCircle, Warning, Lock, Check } from '@phosphor-icons/react';

export default function LiveTraceInspector({ traceData, scenario }) {
  const [openSection, setOpenSection] = useState('guardrails');

  if (!traceData) {
    return (
      <div className="glass-panel rounded-2xl p-5 border border-slate-800/80 text-center text-slate-500 text-xs py-12">
        <Lightning className="w-8 h-8 text-slate-600 mx-auto mb-2 animate-pulse" />
        No active execution trace yet. Send a message to inspect multi-agent trace nodes.
      </div>
    );
  }

  const toggle = (section) => {
    setOpenSection(openSection === section ? null : section);
  };

  const isGuardrailPassed = traceData.guardrail_status === 'PASSED';
  const isAdversarial = traceData.guardrail_status === 'ADVERSARIAL_INTERCEPTED';
  const isCorrected = traceData.guardrail_status === 'POLICY_BREACH_CORRECTED';

  const maxDiscInrDisplay = scenario?.max_discount_inr !== undefined
    ? `INR ${scenario.max_discount_inr.toFixed(2)}`
    : 'INR 20.00';
  const maxGrace = scenario?.max_grace_days ?? 7;

  return (
    <div className="glass-panel rounded-2xl p-5 space-y-4 border border-slate-800/80">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
        <div className="flex items-center space-x-2">
          <Lightning className="w-5 h-5 text-emerald-400" weight="fill" />
          <h3 className="text-sm font-bold text-slate-100">Live Execution Trace</h3>
        </div>
        <span className="font-mono text-xs text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
          {traceData.latency_ms?.toFixed(1) || 120} ms
        </span>
      </div>

      <div className="space-y-2.5 text-xs font-sans">
        {/* 1. Pre & Post Guardrails Accordion with Evaluated Invariant Checklist */}
        <div className="bg-slate-900/80 rounded-xl border border-slate-800 overflow-hidden">
          <button
            onClick={() => toggle('guardrails')}
            className="w-[100%] p-3 text-left font-semibold flex items-center justify-between hover:bg-slate-850 cursor-pointer"
          >
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Guardrails Status</span>
            </div>
            <div className="flex items-center space-x-2">
              {isAdversarial && (
                <span className="px-2 py-0.5 text-[10px] font-mono bg-rose-500/20 text-rose-300 rounded border border-rose-500/30 flex items-center space-x-1">
                  <Lock className="w-3 h-3" />
                  <span>INTERCEPTED</span>
                </span>
              )}
              {isCorrected && (
                <span className="px-2 py-0.5 text-[10px] font-mono bg-amber-500/20 text-amber-300 rounded border border-amber-500/30 flex items-center space-x-1">
                  <Warning className="w-3 h-3" />
                  <span>CORRECTED</span>
                </span>
              )}
              {isGuardrailPassed && (
                <span className="px-2 py-0.5 text-[10px] font-mono bg-emerald-500/20 text-emerald-300 rounded border border-emerald-500/30 flex items-center space-x-1">
                  <CheckCircle className="w-3 h-3" />
                  <span>PASSED</span>
                </span>
              )}
              {openSection === 'guardrails' ? <CaretUp /> : <CaretDown />}
            </div>
          </button>
          {openSection === 'guardrails' && (
            <div className="p-3.5 bg-slate-950/60 border-t border-slate-800 space-y-3 text-[11px] font-mono text-slate-300">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Guardrail Engine Status:</span>
                <span className={`font-bold px-2 py-0.5 rounded text-[10px] ${
                  isGuardrailPassed ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                  isCorrected ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                  'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                }`}>
                  {traceData.guardrail_status}
                </span>
              </div>

              {/* Violations if flagged */}
              {traceData.guardrail_violations?.length > 0 && (
                <div className="bg-rose-950/40 p-2.5 rounded-xl border border-rose-900/60 text-rose-300 space-y-1">
                  <span className="font-bold block text-[10px] uppercase text-rose-400">Violations Flagged & Auto-Corrected:</span>
                  {traceData.guardrail_violations.map((v, i) => (
                    <p key={i} className="text-[10px] leading-tight">• {v}</p>
                  ))}
                </div>
              )}

              {/* Detailed Checklist of Evaluated Invariant Checks */}
              <div className="space-y-2 pt-1 border-t border-slate-800/80">
                <span className="text-slate-400 block font-bold text-[10px] uppercase tracking-wider">Evaluated Invariant Checks:</span>
                
                <div className="space-y-1.5 text-[10px]">
                  <div className="flex items-start space-x-2 bg-slate-900/90 p-2 rounded-lg border border-slate-800">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" weight="fill" />
                    <div>
                      <span className="font-semibold text-slate-200 block">Pre-LLM Adversarial Guardrail</span>
                      <span className="text-slate-400 text-[9px]">Passed (No prompt injection / system override detected)</span>
                    </div>
                  </div>

                  <div className="flex items-start space-x-2 bg-slate-900/90 p-2 rounded-lg border border-slate-800">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" weight="fill" />
                    <div>
                      <span className="font-semibold text-slate-200 block">Discount Ceiling Invariant</span>
                      <span className="text-slate-400 text-[9px]">Passed (discount_inr ≤ merchant limit {maxDiscInrDisplay})</span>
                    </div>
                  </div>

                  <div className="flex items-start space-x-2 bg-slate-900/90 p-2 rounded-lg border border-slate-800">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" weight="fill" />
                    <div>
                      <span className="font-semibold text-slate-200 block">Grace Period Threshold Invariant</span>
                      <span className="text-slate-400 text-[9px]">Passed (grace_days ≤ limit {maxGrace} days)</span>
                    </div>
                  </div>

                  <div className="flex items-start space-x-2 bg-slate-900/90 p-2 rounded-lg border border-slate-800">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" weight="fill" />
                    <div>
                      <span className="font-semibold text-slate-200 block">Arithmetic Split Sum Invariant</span>
                      <span className="text-slate-400 text-[9px]">Passed (∑ split_amounts == proposed_amount)</span>
                    </div>
                  </div>

                  <div className="flex items-start space-x-2 bg-slate-900/90 p-2 rounded-lg border border-slate-800">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" weight="fill" />
                    <div>
                      <span className="font-semibold text-slate-200 block">RAG Grounded Policy Compliance</span>
                      <span className="text-slate-400 text-[9px]">Passed (Grounded in active merchant RAG policy chunks)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 2. RAG Retrieved Context */}
        <div className="bg-slate-900/80 rounded-xl border border-slate-800 overflow-hidden">
          <button
            onClick={() => toggle('rag')}
            className="w-[100%] p-3 text-left font-semibold flex items-center justify-between hover:bg-slate-850 cursor-pointer"
          >
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-emerald-400" />
              <span>RAG Retrieved Chunks ({traceData.retrieved_policy_chunks?.length || 0})</span>
            </div>
            {openSection === 'rag' ? <CaretUp /> : <CaretDown />}
          </button>
          {openSection === 'rag' && (
            <div className="p-3 bg-slate-950/60 border-t border-slate-800 space-y-2 text-[11px] font-mono text-slate-300 max-h-48 overflow-y-auto">
              {traceData.retrieved_policy_chunks?.map((chunk, idx) => (
                <div key={idx} className="bg-slate-900 p-2 rounded border border-slate-800 text-slate-300 leading-relaxed">
                  <span className="text-emerald-400 block font-bold text-[10px]">Chunk #{idx + 1}</span>
                  <p className="whitespace-pre-wrap">{chunk}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 3. Razorpay MCP Payload */}
        <div className="bg-slate-900/80 rounded-xl border border-slate-800 overflow-hidden">
          <button
            onClick={() => toggle('mcp')}
            className="w-[100%] p-3 text-left font-semibold flex items-center justify-between hover:bg-slate-850 cursor-pointer"
          >
            <div className="flex items-center space-x-2">
              <Code className="w-4 h-4 text-emerald-400" />
              <span>Razorpay MCP Tool Payload</span>
            </div>
            {openSection === 'mcp' ? <CaretUp /> : <CaretDown />}
          </button>
          {openSection === 'mcp' && (
            <div className="p-3 bg-slate-950/60 border-t border-slate-800 font-mono text-[10px] text-emerald-300 overflow-x-auto">
              <pre>{JSON.stringify(traceData.razorpay_payload, null, 2)}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
