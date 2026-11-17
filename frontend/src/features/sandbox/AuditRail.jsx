import { CheckCircle, MinusCircle, Path, Prohibit, WarningDiamond } from '@phosphor-icons/react';
import { Panel } from '../../components/ui/Panel';
import { Stamp } from '../../components/ui/Stamp';
import { EmptyState, Skeleton } from '../../components/ui/States';
import { actionLabel, inr, verdictOf } from '../../lib/format';

const CHECK_ICONS = {
  passed: [CheckCircle, 'text-settled'],
  corrected: [WarningDiamond, 'text-caution'],
  blocked: [Prohibit, 'text-void'],
  skipped: [MinusCircle, 'text-ink-4'],
};

const humanIntent = (intent) =>
  intent
    ? intent
        .replace(/^STANDARD_RECOVERY_/, 'General recovery · ')
        .replaceAll('_', ' ')
        .toLowerCase()
    : '—';

function Step({ index, title, children, last = false }) {
  return (
    <li className="relative pl-8">
      {!last && <span aria-hidden className="absolute bottom-0 left-[11px] top-7 w-px bg-rule/15" />}
      <span
        aria-hidden
        className="absolute left-0 top-0.5 flex h-6 w-6 items-center justify-center rounded-full border border-rule/15 bg-sheet-raised text-xs font-medium text-ink-3"
      >
        {index}
      </span>
      <h3 className="text-sm font-medium text-ink">{title}</h3>
      <div className="mt-1.5 pb-5 text-sm text-ink-2">{children}</div>
    </li>
  );
}

const KIND_LABELS = { policy: 'Merchant rule', web: 'Public page', limits: 'Enforced limit' };

function PolicyPassages({ chunks, sources = [] }) {
  if (!chunks?.length || chunks[0] === 'No specific merchant policy found.') {
    return <p className="text-ink-3">No policy passages retrieved.</p>;
  }
  return (
    <ol className="space-y-1.5">
      {chunks.map((chunk, i) => {
        const source = sources[i];
        const [heading, ...lines] = chunk.split('\n');
        const body = lines.join('\n');
        return (
          <li key={source?.id ?? i}>
            <details className="group rounded-control border border-rule/10 bg-well/60">
              <summary className="cursor-pointer list-none px-2.5 py-1.5 text-xs marker:hidden">
                <span className="flex items-baseline gap-1.5">
                  <span className="num font-mono text-ink-4">S{i + 1}</span>
                  <span className="min-w-0 flex-1 text-ink-2">
                    {source ? `${source.source} › ${source.section}` : heading}
                  </span>
                </span>
                {source && (
                  <span className="mt-0.5 block pl-6 text-ink-4">
                    {KIND_LABELS[source.kind] ?? source.kind}
                    {source.fetched_at ? ` · fetched ${source.fetched_at}` : ''}
                  </span>
                )}
              </summary>
              <div className="border-t border-rule/10 px-2.5 py-2 text-xs leading-relaxed text-ink-3">
                <p className="whitespace-pre-wrap">{body}</p>
                {source?.url && (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1.5 inline-block text-accent underline"
                  >
                    Open source page
                  </a>
                )}
              </div>
            </details>
          </li>
        );
      })}
    </ol>
  );
}

/** Evidence for the latest agent turn, in the order the graph produced it. */
export function AuditRail({ turn, sending, className = '', ...rest }) {
  const meta =
    turn &&
    `${Math.round(turn.latency_ms)} ms${turn.token_spend ? ` · ${turn.token_spend.toLocaleString('en-IN')} tokens` : ''}`;

  let body;
  if (sending) {
    body = (
      <div className="space-y-4 p-4" aria-label="Running triage, policy retrieval and guardrails">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="h-6 w-6 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-10 w-full" />
            </div>
          </div>
        ))}
      </div>
    );
  } else if (!turn) {
    body = (
      <EmptyState icon={Path} title="No evidence yet">
        Send a reply and every step the agent took appears here: intent, policy passages, the offer, each
        guardrail check and the payment tool call.
      </EmptyState>
    );
  } else {
    const offer = turn.proposed_offer ?? {};
    const payload = turn.razorpay_payload;
    body = (
      <ol className="p-4">
        <Step index={1} title="Triage">
          <span className="capitalize">{humanIntent(turn.customer_intent)}</span>
        </Step>
        <Step index={2} title={`Policy retrieved (${turn.retrieved_policy_chunks?.length ?? 0})`}>
          <PolicyPassages chunks={turn.retrieved_policy_chunks} sources={turn.retrieved_sources} />
        </Step>
        <Step index={3} title="Offer">
          {turn.action === 'BLOCKED' ? (
            <p className="text-ink-3">Not generated: the input guard stopped this turn.</p>
          ) : (
            <p>
              {actionLabel(turn.action)}
              {offer.proposed_amount ? (
                <span className="num ml-1.5 font-medium text-ink">{inr(offer.proposed_amount)}</span>
              ) : null}
            </p>
          )}
        </Step>
        <Step index={4} title="Guardrails">
          <Stamp verdict={verdictOf(turn.guardrail_status)} className="mb-2.5" />
          <ul className="space-y-2">
            {(turn.guardrail_checks ?? []).map((check) => {
              const [Icon, tone] = CHECK_ICONS[check.status] ?? CHECK_ICONS.skipped;
              return (
                <li key={check.id} className="flex gap-2">
                  <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${tone}`} weight="fill" aria-hidden />
                  <div>
                    <p className="text-xs font-medium text-ink">
                      {check.label} <span className="font-normal text-ink-3">· {check.status}</span>
                    </p>
                    <p className="text-xs text-ink-3">{check.detail}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </Step>
        <Step index={5} title="Payment tool" last>
          {payload ? (
            <>
              <p className="text-xs">
                <span className="font-mono">{payload.tool ?? 'create_payment_link'}</span>
                <span className="text-ink-3">
                  {' '}
                  · {payload.transport ?? 'mcp'} · {payload.sandbox ? 'sandbox' : 'Razorpay'}
                </span>
              </p>
              <p className="mt-1 text-xs text-ink-3">
                {payload.success ? `Link created for ${inr(payload.amount_in_inr)}` : payload.error}
              </p>
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-accent">Raw tool result</summary>
                <pre className="scroll-quiet mt-1.5 overflow-x-auto rounded-control bg-well p-2.5 font-mono text-xs text-ink-2">
                  {JSON.stringify(payload, null, 2)}
                </pre>
              </details>
            </>
          ) : (
            <p className="text-ink-3">Not called: no customer consent to pay on this turn.</p>
          )}
        </Step>
      </ol>
    );
  }

  return (
    <Panel
      title="Audit trail"
      aside={meta && <span className="num text-xs text-ink-3">{meta}</span>}
      className={className}
      bodyClassName="scroll-quiet overflow-y-auto"
      {...rest}
    >
      {body}
    </Panel>
  );
}
