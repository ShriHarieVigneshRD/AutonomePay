import { Info } from '@phosphor-icons/react';
import { Eyebrow, Panel } from '../../components/ui/Panel';
import { Skeleton } from '../../components/ui/States';
import { failureReason, inr } from '../../lib/format';

function Row({ label, children }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <dt className="text-ink-3">{label}</dt>
      <dd className="text-right text-ink">{children}</dd>
    </div>
  );
}

/** Who owes what, and every bound the guardrail will enforce for this merchant. */
export function CaseFile({ scenario, loading, className = '', ...rest }) {
  if (loading || !scenario) {
    return (
      <Panel title="Case file" className={className} bodyClassName="space-y-3 p-4" {...rest}>
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-24 w-full" />
      </Panel>
    );
  }
  const policy = scenario.policy ?? {};
  const cheaper = (policy.plans ?? []).filter((p) => p.price_inr < scenario.original_amount);

  return (
    <Panel title="Case file" className={className} bodyClassName="scroll-quiet overflow-y-auto" {...rest}>
      <div className="border-b border-rule/10 px-4 py-4">
        <p className="text-base font-semibold tracking-tight">{scenario.merchant_name}</p>
        <p className="text-xs text-ink-3">{scenario.category}</p>
        <p className="num mt-4 text-2xl font-semibold tracking-tight">{inr(scenario.original_amount)}</p>
        <p className="text-xs text-ink-3">
          {scenario.plan_name} · <span className="text-void">{failureReason(scenario.failure_code)}</span>
        </p>
      </div>

      <dl className="border-b border-rule/10 px-4 py-2 text-sm">
        <Row label="Customer">{scenario.customer_name}</Row>
        <Row label="Invoice">
          <span className="num font-mono text-xs">{scenario.invoice_id}</span>
        </Row>
        <Row label="Scenario">{scenario.scenario_type_title}</Row>
      </dl>

      <div className="px-4 py-3">
        <Eyebrow>Policy bounds</Eyebrow>
        <dl className="mt-1 text-sm">
          <Row label="Max discount">
            {scenario.max_discount_inr ? inr(scenario.max_discount_inr) : 'None'}
          </Row>
          <Row label="Max grace">{scenario.max_grace_days} days</Row>
          {cheaper.length > 0 && (
            <Row label="Downgrade to">
              {cheaper.map((p) => (
                <span key={p.name} className="block">
                  {p.name} <span className="num text-ink-3">{inr(p.price_inr)}</span>
                </span>
              ))}
            </Row>
          )}
          {policy.split_schedule_pct && (
            <Row label="Instalments">
              {policy.split_schedule_pct.join('/')} split
              {policy.split_min_invoice_inr ? (
                <span className="block text-xs text-ink-3">above {inr(policy.split_min_invoice_inr)}</span>
              ) : null}
            </Row>
          )}
          {policy.partial_settlement_pct && (
            <Row label="Disputes">Pay undisputed {policy.partial_settlement_pct}%</Row>
          )}
          {policy.auto_escalation_limit ? (
            <Row label="Escalate above">{inr(policy.auto_escalation_limit)}</Row>
          ) : null}
        </dl>
        <p className="mt-3 flex gap-1.5 text-xs text-ink-3">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          Limits are simulated merchant settings, enforced in code after every LLM reply.
        </p>
      </div>
    </Panel>
  );
}
