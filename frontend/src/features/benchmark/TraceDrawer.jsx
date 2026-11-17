import { ArrowSquareOut, X } from '@phosphor-icons/react';
import { Button } from '../../components/ui/Button';
import { Dialog } from '../../components/ui/Dialog';
import { Eyebrow } from '../../components/ui/Panel';
import { Stamp } from '../../components/ui/Stamp';
import { actionLabel, inr, pct, verdictOf } from '../../lib/format';
import { OUTCOMES, outcomeOf } from './CaseLedger';

/** Every turn of one benchmark case, as a side sheet (full screen on mobile). */
export function TraceDrawer({ row, onClose }) {
  return (
    <Dialog open={Boolean(row)} onClose={onClose} labelledBy="trace-title" variant="sheet">
      {row && (
        <div className="flex h-full flex-col">
          <header className="flex items-start justify-between gap-3 border-b border-rule/10 px-5 py-4">
            <div>
              <Eyebrow>{row.test_id.replace('eval_case_', 'Case #')}</Eyebrow>
              <h2 id="trace-title" className="mt-0.5 text-base font-semibold tracking-tight">
                {row.scenario_type.replaceAll('_', ' ').toLowerCase()}
              </h2>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close trace">
              <X className="h-4 w-4" aria-hidden />
            </Button>
          </header>

          <div className="scroll-quiet min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-4">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <div>
                <dt className="text-xs text-ink-3">Outcome</dt>
                <dd>{OUTCOMES[outcomeOf(row)].label}</dd>
              </div>
              <div>
                <dt className="text-xs text-ink-3">Final action</dt>
                <dd>{actionLabel(row.final_action)}</dd>
              </div>
              <div>
                <dt className="text-xs text-ink-3">Invoice → link</dt>
                <dd className="num">
                  {inr(row.invoice_inr)} → {row.recovered_inr ? inr(row.recovered_inr) : 'no link'}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-ink-3">RAG faithfulness</dt>
                <dd className="num">{pct(row.rag_faithfulness * 100, 1)}</dd>
              </div>
              {row.expected_action && (
                <div className="col-span-2">
                  <dt className="text-xs text-ink-3">Expected</dt>
                  <dd>{actionLabel(row.expected_action)}</dd>
                </div>
              )}
            </dl>

            {row.langsmith_trace_url && (
              <a
                href={row.langsmith_trace_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-accent underline"
              >
                Open in LangSmith <ArrowSquareOut className="h-4 w-4" aria-hidden />
              </a>
            )}

            <section>
              <Eyebrow>Opening message</Eyebrow>
              <p className="mt-1.5 rounded-panel border border-rule/10 bg-sheet px-3.5 py-2.5 text-sm text-ink-2">
                {row.initial_message}
              </p>
            </section>

            <section>
              <Eyebrow>Turns</Eyebrow>
              <ol className="mt-1.5 space-y-3">
                {row.execution_trace?.map((step) => (
                  <li key={step.turn} className="rounded-panel border border-rule/10 bg-sheet p-3.5 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-3">
                      <span>
                        Turn {step.turn}
                        {step.action ? ` · ${actionLabel(step.action)}` : ''}
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="num">{Math.round(step.latency_ms)} ms</span>
                        <Stamp verdict={verdictOf(step.guardrail_status)} />
                      </span>
                    </div>
                    <p className="mt-2.5 text-xs text-ink-3">Customer (scripted)</p>
                    <p className="text-ink">{step.user}</p>
                    <p className="mt-2.5 text-xs text-ink-3">Concierge</p>
                    <p className="whitespace-pre-wrap text-ink-2">{step.agent}</p>
                    {step.sources?.length > 0 && (
                      <p className="mt-2 text-xs text-ink-3">
                        Policy used: {[...new Set(step.sources)].join(' · ')}
                      </p>
                    )}
                  </li>
                ))}
              </ol>
            </section>
          </div>
        </div>
      )}
    </Dialog>
  );
}
