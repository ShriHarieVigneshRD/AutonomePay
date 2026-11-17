import { Clock } from '@phosphor-icons/react';
import { Eyebrow } from '../../components/ui/Panel';
import { Stamp } from '../../components/ui/Stamp';
import { actionLabel, inr, verdictOf } from '../../lib/format';
import { BoundsMeter } from './BoundsMeter';
import { PaymentStatus } from './PaymentStatus';

const NO_SLIP = new Set(['HUMAN_ESCALATION', 'GRACEFUL_DISCONTINUATION', 'BLOCKED', 'NONE']);

function slipLines(offer, action, scenario) {
  const original = offer.original_amount;
  const amount = offer.proposed_amount;
  if (action === 'PLAN_DOWNGRADE') {
    return [
      ['Current plan', inr(original)],
      ['New plan', inr(amount)],
    ];
  }
  if (action === 'MILESTONE_SPLIT' && offer.split_amounts?.length > 1) {
    return [
      ['Invoice', inr(original)],
      ...offer.split_amounts.slice(1).map((part, i) => [`Instalment ${i + 2} (later)`, inr(part)]),
    ];
  }
  if (action === 'PARTIAL_SETTLEMENT') {
    const pct = scenario?.policy?.partial_settlement_pct;
    const undisputed = pct ? (original * pct) / 100 : amount + offer.discount_inr;
    const lines = [
      ['Invoice', inr(original)],
      ['Held while disputed', `−${inr(original - undisputed)}`],
    ];
    if (offer.discount_inr > 0) lines.push(['Prompt-payment discount', `−${inr(offer.discount_inr)}`]);
    return lines;
  }
  const lines = [['Invoice', inr(original)]];
  if (offer.discount_inr > 0) lines.push(['Concession', `−${inr(offer.discount_inr)}`]);
  return lines;
}

/** The approved offer for one agent turn, as a receipt the customer can act on. */
export function SettlementSlip({ turn, scenario, fresh = false }) {
  const offer = turn?.proposed_offer;
  if (!offer?.proposed_amount || NO_SLIP.has(turn.action)) return null;

  const verdict = verdictOf(turn.guardrail_status);
  const corrected = verdict === 'corrected';
  const payload = turn.razorpay_payload;
  const isDiscount = turn.action === 'PROPOSE_SETTLEMENT' || turn.action === 'EXTEND_GRACE';

  return (
    <article
      aria-label="Settlement slip"
      className="mt-2 w-full max-w-sm rounded-panel border border-rule/15 bg-sheet-raised text-sm"
    >
      <header className="flex items-center justify-between gap-3 border-b border-dashed border-rule/20 px-4 py-2.5">
        <Eyebrow>{actionLabel(turn.action)}</Eyebrow>
        <Stamp verdict={verdict} animate={fresh} />
      </header>

      <dl className="space-y-1.5 px-4 py-3">
        {slipLines(offer, turn.action, scenario).map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4">
            <dt className="text-ink-3">{label}</dt>
            <dd className="num text-ink-2">{value}</dd>
          </div>
        ))}
        <div className="flex items-baseline justify-between gap-4 border-t border-rule/10 pt-2">
          <dt className="font-medium text-ink">
            {turn.action === 'MILESTONE_SPLIT' ? 'Due now' : 'Net payable'}
          </dt>
          <dd className="num text-xl font-semibold tracking-tight text-ink">{inr(offer.proposed_amount)}</dd>
        </div>
        {offer.grace_days > 0 && (
          <div className="flex justify-between gap-4 text-xs">
            <dt className="text-ink-3">Grace period</dt>
            <dd className="text-ink-2">{offer.grace_days} days</dd>
          </div>
        )}
      </dl>

      {scenario && (
        <div className="space-y-2.5 border-t border-rule/10 px-4 py-3">
          {isDiscount && (
            <BoundsMeter
              label="Discount used"
              used={offer.discount_inr}
              limit={scenario.max_discount_inr}
              format={inr}
              corrected={corrected}
            />
          )}
          <BoundsMeter
            label="Grace days used"
            used={offer.grace_days}
            limit={scenario.max_grace_days}
            format={(d) => `${d} d`}
          />
        </div>
      )}

      {turn.guardrail_violations?.length > 0 && (
        <ul className="space-y-1 border-t border-rule/10 px-4 py-2.5 text-xs text-caution-ink">
          {turn.guardrail_violations.map((v) => (
            <li key={v}>Guardrail: {v}</li>
          ))}
        </ul>
      )}

      <footer className="border-t border-rule/10 px-4 py-3">
        {payload?.success ? (
          <PaymentStatus payload={payload} />
        ) : payload && !payload.success ? (
          <p className="text-xs text-void">{payload.error || 'The payment link could not be created.'}</p>
        ) : (
          <p className="flex items-center gap-1.5 text-xs text-ink-3">
            <Clock className="h-3.5 w-3.5" aria-hidden />
            Link is issued only after the customer agrees.
          </p>
        )}
      </footer>
    </article>
  );
}
