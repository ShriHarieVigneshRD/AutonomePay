import { useEffect, useRef, useState } from 'react';
import { ArrowClockwise, Handshake, PaperPlaneRight, Prohibit, UserCircleCheck } from '@phosphor-icons/react';
import { Button } from '../../components/ui/Button';
import { Panel } from '../../components/ui/Panel';
import { Stamp } from '../../components/ui/Stamp';
import { SettlementSlip } from './SettlementSlip';

const PAY_LINE = /\n*\[\s*Pay INR[^\]]*\]\(https?:\/\/[^)\s]+\)\s*$/;
const MD_LINK = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g;

/** Plain text with markdown links turned into anchors (used for replies without a slip). */
function RichText({ text }) {
  const parts = [];
  let last = 0;
  for (const match of text.matchAll(MD_LINK)) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    parts.push(
      <a
        key={match.index}
        href={match[2]}
        target="_blank"
        rel="noopener noreferrer"
        className="font-medium text-accent underline"
      >
        {match[1].trim()}
      </a>,
    );
    last = match.index + match[0].length;
  }
  parts.push(text.slice(last));
  return <p className="whitespace-pre-wrap">{parts}</p>;
}

function suggestions(scenario) {
  if (!scenario) return [];
  const policy = scenario.policy ?? {};
  const list = ['Money is tight this month. What can you do?'];
  if (policy.plans?.some((p) => p.price_inr < scenario.original_amount))
    list.push('Can I move to a cheaper plan?');
  if (policy.split_schedule_pct) list.push('Can we split this into instalments?');
  if (policy.partial_settlement_pct) list.push('Some items arrived damaged. Can I pay the undisputed part?');
  list.push('I want to cancel instead.');
  return list.slice(0, 4);
}

const NOTES = {
  HUMAN_ESCALATION: [UserCircleCheck, 'Escalated to a human specialist · no payment requested'],
  GRACEFUL_DISCONTINUATION: [Handshake, 'Cancellation respected · no payment requested'],
  NONE: [Prohibit, 'Conversation limit reached'],
};

function TurnNote({ turn }) {
  if (turn.action === 'BLOCKED') {
    return (
      <div className="mt-2 flex items-center gap-2 text-xs text-ink-3">
        <Stamp verdict="blocked" animate />
        <span>Stopped before the LLM was called.</span>
      </div>
    );
  }
  const note = NOTES[turn.action];
  if (!note) return null;
  const [Icon, text] = note;
  return (
    <p className="mt-2 flex items-center gap-1.5 text-xs text-ink-3">
      <Icon className="h-4 w-4" aria-hidden />
      {text}
    </p>
  );
}

export function ChatPanel({ scenario, conversation, className = '', ...rest }) {
  const { messages, sending, failed, send, retry, reset } = conversation;
  const [draft, setDraft] = useState('');
  const endRef = useRef(null);
  const lastMeta = messages.findLast((m) => m.meta)?.meta;
  const firstName = scenario?.customer_name?.split(' ')[0] ?? 'the customer';

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length, sending, failed]);

  const submit = (event) => {
    event.preventDefault();
    if (!draft.trim() || sending) return;
    send(draft);
    setDraft('');
  };

  return (
    <Panel
      className={className}
      title={
        <span className="flex items-baseline gap-1.5">
          Conversation
          <span className="truncate font-normal text-ink-3">with {scenario?.customer_name ?? '…'}</span>
        </span>
      }
      aside={
        <Button variant="ghost" size="sm" onClick={reset} disabled={!scenario || messages.length < 2}>
          <ArrowClockwise className="h-4 w-4" aria-hidden />
          <span className="max-sm:sr-only">New conversation</span>
        </Button>
      }
      bodyClassName="flex flex-col"
      {...rest}
    >
      <div
        role="log"
        aria-live="polite"
        aria-label="Conversation"
        className="scroll-quiet min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4"
      >
        {messages.map((message, index) => {
          const isUser = message.role === 'user';
          const text = message.meta ? message.content.replace(PAY_LINE, '') : message.content;
          return (
            <div key={index} className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
              <span className="mb-1 text-xs text-ink-3">{isUser ? firstName : 'Concierge'}</span>
              <div
                className={`max-w-[85%] rounded-panel px-3.5 py-2.5 text-sm leading-relaxed ${
                  isUser ? 'bg-accent text-accent-on' : 'border border-rule/10 bg-sheet-raised text-ink'
                }`}
              >
                <RichText text={text} />
              </div>
              {message.meta && (
                <>
                  <SettlementSlip turn={message.meta} scenario={scenario} fresh={message.meta === lastMeta} />
                  <TurnNote turn={message.meta} />
                </>
              )}
            </div>
          );
        })}

        {messages.length === 1 && !sending && (
          <ul className="flex flex-wrap gap-2 pt-1" aria-label="Suggested replies">
            {suggestions(scenario).map((s) => (
              <li key={s}>
                <button
                  type="button"
                  onClick={() => send(s)}
                  className="rounded-full border border-rule/15 px-3 py-1.5 text-xs text-ink-2 transition-colors hover:border-accent/40 hover:text-ink max-md:min-h-10"
                >
                  {s}
                </button>
              </li>
            ))}
          </ul>
        )}

        {sending && (
          <p className="flex items-center gap-2 text-xs text-ink-3" role="status">
            <span className="inline-flex gap-1" aria-hidden>
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-4"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </span>
            Checking {scenario?.merchant_name}&rsquo;s policy…
          </p>
        )}

        {failed && !sending && (
          <div
            role="alert"
            className="flex flex-wrap items-center justify-between gap-3 rounded-panel border border-void/30 bg-void/[0.06] px-3.5 py-2.5 text-sm"
          >
            <span className="text-ink-2">
              Couldn&rsquo;t send &ldquo;{failed.text}&rdquo;. {failed.error}
            </span>
            <Button size="sm" onClick={retry}>
              Retry
            </Button>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={submit} className="flex items-center gap-2 border-t border-rule/10 p-3">
        <label htmlFor="reply" className="sr-only">
          Reply as {firstName}
        </label>
        <input
          id="reply"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={!scenario}
          maxLength={4000}
          autoComplete="off"
          placeholder={`Reply as ${firstName}…`}
          className="h-10 min-w-0 flex-1 rounded-control border border-rule/10 bg-well px-3 text-base text-ink placeholder:text-ink-4 focus:border-accent/50 md:text-sm"
        />
        <Button
          type="submit"
          variant="primary"
          className="h-10"
          disabled={!scenario || sending || !draft.trim()}
        >
          <span className="max-sm:sr-only">Send</span>
          <PaperPlaneRight className="h-4 w-4" weight="fill" aria-hidden />
        </Button>
      </form>
    </Panel>
  );
}
