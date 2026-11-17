import { ArrowSquareOut, ArrowsClockwise, SealCheck } from '@phosphor-icons/react';
import { Button, ButtonLink } from '../../components/ui/Button';
import { usePaymentStatus } from '../../hooks/usePaymentStatus';
import { inr } from '../../lib/format';

/** The "Pay" link of an issued payment link plus its live status (checked over MCP). */
export function PaymentStatus({ payload }) {
  const { status, paid, checking, error, check } = usePaymentStatus(payload.payment_link_id);

  if (paid) {
    return (
      <p className="flex items-center gap-2 text-sm font-medium text-settled" role="status">
        <SealCheck className="h-5 w-5" weight="fill" aria-hidden />
        Paid {inr(status.amount_paid_inr)}
        <span className="font-normal text-ink-3">
          · invoice {status.invoice_status?.toLowerCase().replace('_', ' ')}
        </span>
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <ButtonLink href={payload.short_url} target="_blank" rel="noopener noreferrer" size="sm">
          Pay {inr(payload.amount_in_inr)}
          <ArrowSquareOut className="h-4 w-4" aria-hidden />
        </ButtonLink>
        <Button size="sm" variant="ghost" onClick={check} disabled={checking}>
          <ArrowsClockwise className={`h-4 w-4 ${checking ? 'animate-spin' : ''}`} aria-hidden />
          Check status
        </Button>
      </div>
      <p className="text-xs text-ink-3" role="status">
        {error ??
          (status
            ? `Status: ${status.status}`
            : `${payload.sandbox ? 'Sandbox link' : 'Razorpay link'} · via MCP`)}
      </p>
    </div>
  );
}
