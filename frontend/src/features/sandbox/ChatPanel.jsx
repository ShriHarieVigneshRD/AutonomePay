import { useState, useRef, useEffect } from 'react';
import { PaperPlaneRight, Robot, User, ArrowSquareOut, CheckCircle } from '@phosphor-icons/react';

export default function ChatPanel({ messages, onSendMessage, loading, failed, onRetry, activeScenario }) {
  const [input, setInput] = useState('');
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // B23: one static hint; rotating placeholders were distracting and unreadable to screen readers.
  const firstName = activeScenario?.customer_name?.split(' ')[0] || 'the customer';
  const placeholder = `Reply as ${firstName}…`;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const renderInlineFormattedText = (textStr) => {
    let cleaned = textStr.replace(/^\s*#{1,6}\s+/gm, '');
    const boldRegex = /\*\*([^*]+)\*\*/g;
    const elements = [];
    let lastIdx = 0;
    let bMatch;

    while ((bMatch = boldRegex.exec(cleaned)) !== null) {
      if (bMatch.index > lastIdx) {
        elements.push(cleaned.substring(lastIdx, bMatch.index));
      }
      elements.push(
        <strong key={bMatch.index} className="font-semibold text-emerald-200">
          {bMatch[1]}
        </strong>,
      );
      lastIdx = boldRegex.lastIndex;
    }
    if (lastIdx < cleaned.length) {
      elements.push(cleaned.substring(lastIdx));
    }
    return elements;
  };

  const renderMessageContent = (content) => {
    const linkRegex = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = linkRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.substring(lastIndex, match.index));
      }
      const label = match[1];
      const url = match[2];
      parts.push(
        <div key={match.index} className="my-2.5">
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center space-x-2 glass-pill px-4 py-2.5 rounded-xl font-bold text-emerald-300 hover:text-white transition-all transform active:scale-95 shadow-lg border border-emerald-500/40"
          >
            <CheckCircle className="w-5 h-5 text-emerald-400" weight="fill" />
            <span>{label}</span>
            <ArrowSquareOut className="w-4 h-4 text-emerald-300 ml-1" />
          </a>
        </div>,
      );
      lastIndex = linkRegex.lastIndex;
    }

    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }

    return (
      <div className="whitespace-pre-wrap leading-relaxed space-y-1">
        {parts.map((p, idx) =>
          typeof p === 'string' ? <span key={idx}>{renderInlineFormattedText(p)}</span> : p,
        )}
      </div>
    );
  };

  return (
    <div className="glass-panel rounded-2xl flex flex-col h-full border border-slate-800/80 overflow-hidden">
      {/* Chat Header */}
      <div className="px-5 py-4 bg-slate-950/60 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shadow-sm">
            <Robot className="w-5 h-5" weight="bold" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-slate-100">AutonomePay Sentinel</h3>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">Bound multi-agent revenue concierge</p>
          </div>
        </div>
        <span className="text-xs text-slate-400 font-mono bg-slate-900 px-3 py-1 rounded-full border border-slate-800">
          Session Active
        </span>
      </div>

      {/* Messages Feed */}
      <div className="flex-1 p-5 overflow-y-auto space-y-4">
        {messages.map((msg, idx) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={idx}
              className={`flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 ${
                  isUser
                    ? 'bg-slate-800 text-slate-200 border border-slate-700'
                    : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Robot className="w-4 h-4" />}
              </div>

              <div
                className={`max-w-[80%] rounded-2xl p-4 text-xs font-sans shadow-md ${
                  isUser
                    ? 'bg-emerald-600/20 text-slate-100 border border-emerald-500/30 rounded-tr-none'
                    : 'bg-slate-900/90 text-slate-200 border border-slate-800 rounded-tl-none'
                }`}
              >
                {renderMessageContent(msg.content)}
              </div>
            </div>
          );
        })}

        {failed && !loading && (
          <div
            role="alert"
            className="flex items-center justify-between gap-3 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-xs text-rose-200"
          >
            <span>
              Couldn&apos;t send &ldquo;{failed.text}&rdquo;: {failed.error}
            </span>
            <button type="button" onClick={onRetry} className="shrink-0 font-semibold underline">
              Retry
            </button>
          </div>
        )}

        {loading && (
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Robot className="w-4 h-4 animate-pulse" />
            </div>
            <div className="bg-slate-900 px-4 py-3 rounded-2xl rounded-tl-none border border-slate-800 flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce"></span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.2s]"></span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.4s]"></span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input Form with Scenario-Aware Rotating Placeholder */}
      <form
        onSubmit={handleSubmit}
        className="p-4 bg-slate-950/80 border-t border-slate-800/80 flex items-center space-x-3"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          aria-label="Your reply"
          disabled={!activeScenario}
          className="flex-1 bg-slate-900 text-slate-100 placeholder-slate-500 text-xs px-4 py-3 rounded-xl border border-slate-800 focus:outline-none focus:border-emerald-500/60 font-sans transition-all"
        />
        <button
          type="submit"
          disabled={loading || !activeScenario || !input.trim()}
          className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-slate-950 px-4 py-3 rounded-xl font-bold text-xs flex items-center space-x-1.5 transition-all transform active:scale-95 shadow-md cursor-pointer"
        >
          <span>Send</span>
          <PaperPlaneRight className="w-4 h-4" weight="bold" />
        </button>
      </form>
    </div>
  );
}
