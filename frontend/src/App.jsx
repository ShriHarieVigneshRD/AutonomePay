import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldCheck, ChatTeardropText, ChartBar } from '@phosphor-icons/react';

import ScenarioSelector from './components/ScenarioSelector';
import ContextCard from './components/ContextCard';
import ChatTab from './components/ChatTab';
import LiveTraceInspector from './components/LiveTraceInspector';
import BatchEvalTab from './components/BatchEvalTab';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'evals'
  const [scenarios, setScenarios] = useState([]);
  const [activeScenario, setActiveScenario] = useState(null);

  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [traceData, setTraceData] = useState(null);

  // Fetch preset scenarios on mount
  useEffect(() => {
    axios.get(`${API_BASE}/api/scenarios`)
      .then((res) => {
        setScenarios(res.data);
        if (res.data.length > 0) {
          selectScenario(res.data[0]);
        }
      })
      .catch((err) => {
        console.error("Failed to load scenarios:", err);
      });
  }, []);

  const selectScenario = (sc) => {
    setActiveScenario(sc);
    setMessages([
      { role: 'assistant', content: sc.initial_message }
    ]);
    setTraceData(null);
  };

  const handleSendMessage = async (userMsg) => {
    if (!activeScenario) return;

    const newMsgs = [...messages, { role: 'user', content: userMsg }];
    setMessages(newMsgs);
    setLoading(true);

    try {
      const res = await axios.post(`${API_BASE}/api/chat`, {
        merchant_id: activeScenario.merchant_id,
        customer_id: activeScenario.customer_id,
        invoice_id: activeScenario.invoice_id,
        messages: newMsgs
      });

      const data = res.data;
      setMessages([...newMsgs, { role: 'assistant', content: data.final_response }]);
      setTraceData(data);
    } catch (e) {
      console.error("Chat turn failed", e);
      setMessages([
        ...newMsgs,
        {
          role: 'assistant',
          content: "We encountered an issue processing your request. Please try again."
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

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
            <p className="text-[10px] text-slate-400 font-mono">Autonomous Financial Concierge & Settlement Sentinel</p>
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

        {/* Header Scenario Selector */}
        {activeTab === 'chat' && (
          <ScenarioSelector
            scenarios={scenarios}
            activeScenario={activeScenario}
            onSelectScenario={selectScenario}
          />
        )}
      </header>

      {/* Main App Content Area (Viewport Lock: h-[calc(100vh-55px)]) */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto p-4 overflow-hidden flex flex-col h-[calc(100vh-55px)]">
        {activeTab === 'chat' ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch h-full flex-1 overflow-hidden">
            {/* Left Column: Context Card (3 cols) */}
            <div className="lg:col-span-3 h-full overflow-hidden flex flex-col">
              <ContextCard scenario={activeScenario} />
            </div>

            {/* Center Column: Interactive Chat (6 cols) */}
            <div className="lg:col-span-6 h-full overflow-hidden flex flex-col">
              <ChatTab
                messages={messages}
                onSendMessage={handleSendMessage}
                loading={loading}
                activeScenario={activeScenario}
              />
            </div>

            {/* Right Column: Live Trace Inspector (3 cols) */}
            <div className="lg:col-span-3 h-full overflow-hidden flex flex-col">
              <LiveTraceInspector traceData={traceData} scenario={activeScenario} />
            </div>
          </div>
        ) : (
          <div className="h-full overflow-y-auto">
            <BatchEvalTab />
          </div>
        )}
      </main>
    </div>
  );
}
