import { useState } from 'react';
import { ShieldCheck, ChatTeardropText, ChartBar } from '@phosphor-icons/react';

import { useScenarios } from './hooks/useScenarios';
import { useConversation } from './hooks/useConversation';
import ScenarioPicker from './features/sandbox/ScenarioPicker';
import CaseFile from './features/sandbox/CaseFile';
import ChatPanel from './features/sandbox/ChatPanel';
import AuditRail from './features/sandbox/AuditRail';
import BenchmarkView from './features/benchmark/BenchmarkView';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'evals'
  const { scenarios, error: scenariosError, retry: retryScenarios } = useScenarios();
  const [selectedId, setSelectedId] = useState(null);
  const activeScenario = scenarios.find((s) => s.id === selectedId) ?? scenarios[0] ?? null;
  const conversation = useConversation(activeScenario);

  return (
    <div className="h-screen bg-[#090d16] text-slate-100 flex flex-col overflow-hidden selection:bg-emerald-500/30 selection:text-emerald-300">
      {/* Top Header Navbar */}
      <header className="shrink-0 bg-[#090d16]/90 backdrop-blur-md border-b border-slate-800/80 px-6 py-2.5 flex items-center justify-between z-40">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-md">
            <ShieldCheck className="w-5 h-5" weight="fill" />
          </div>
          <div>
            <h1 className="text-sm font-extrabold tracking-tight text-slate-100 flex items-center space-x-2">
              <span>AutonomePay</span>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Razorpay AI Buildathon
              </span>
            </h1>
            <p className="text-[10px] text-slate-400 font-mono">
              Autonomous Financial Concierge & Settlement Sentinel
            </p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-3.5 py-1.5 rounded-lg font-semibold text-xs flex items-center space-x-2 transition-all cursor-pointer ${
              activeTab === 'chat'
                ? 'bg-emerald-500 text-slate-950 shadow-md'
                : 'text-slate-400 hover:text-slate-100'
            }`}
          >
            <ChatTeardropText className="w-4 h-4" weight="bold" />
            <span>Concierge Sandbox</span>
          </button>
          <button
            onClick={() => setActiveTab('evals')}
            className={`px-3.5 py-1.5 rounded-lg font-semibold text-xs flex items-center space-x-2 transition-all cursor-pointer ${
              activeTab === 'evals'
                ? 'bg-emerald-500 text-slate-950 shadow-md'
                : 'text-slate-400 hover:text-slate-100'
            }`}
          >
            <ChartBar className="w-4 h-4" weight="bold" />
            <span>Batch Eval Matrix</span>
          </button>
        </div>

        {activeTab === 'chat' && (
          <ScenarioPicker
            scenarios={scenarios}
            activeScenario={activeScenario}
            onSelectScenario={(sc) => setSelectedId(sc.id)}
          />
        )}
      </header>

      {scenariosError && (
        <div
          role="alert"
          className="mx-4 mt-3 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-xs text-rose-200"
        >
          {scenariosError}{' '}
          <button className="underline" onClick={retryScenarios}>
            Retry
          </button>
        </div>
      )}

      <main className="flex-1 max-w-[1600px] w-full mx-auto p-4 overflow-hidden flex flex-col h-[calc(100vh-55px)]">
        {activeTab === 'chat' ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch h-full flex-1 overflow-hidden">
            <div className="lg:col-span-3 h-full overflow-hidden flex flex-col">
              <CaseFile scenario={activeScenario} />
            </div>
            <div className="lg:col-span-6 h-full overflow-hidden flex flex-col">
              <ChatPanel
                messages={conversation.messages}
                onSendMessage={conversation.send}
                loading={conversation.sending}
                failed={conversation.failed}
                onRetry={conversation.retry}
                activeScenario={activeScenario}
              />
            </div>
            <div className="lg:col-span-3 h-full overflow-hidden flex flex-col">
              <AuditRail traceData={conversation.trace} scenario={activeScenario} />
            </div>
          </div>
        ) : (
          <div className="h-full overflow-y-auto">
            <BenchmarkView />
          </div>
        )}
      </main>
    </div>
  );
}
