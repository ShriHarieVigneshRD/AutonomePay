import { useEffect } from 'react';
import { ArrowSquareOut, SealCheck, Storefront } from '@phosphor-icons/react';
import { Button, ButtonLink } from '../../components/ui/Button';
import { Eyebrow } from '../../components/ui/Panel';
import { ErrorState, Skeleton } from '../../components/ui/States';
import { usePaymentStatus } from '../../hooks/usePaymentStatus';
import { inr } from '../../lib/format';

/** /pay/:id: stand-in checkout for sandbox links (live links go to Razorpay instead). */
export function CheckoutPage({ linkId }) {
  const { status, paid, checking, error, check, simulate } = usePaymentStatus(linkId, { auto: false });

  useEffect(() => {
    check();
  }, [check]);

  let body;
  if (error && !status) {
    body = <ErrorState message={error} onRetry={check} />;
  } else if (!status) {
    body = (
      <div className="space-y-3" aria-label="Loading payment">
        <Skeleton className="h-5 w-1/2" />
        <Skeleton className="h-12 w-2/3" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  } else {
    body = (
      <>
        <div className="flex items-center gap-2 text-sm text-ink-2">
          <Storefront className="h-4 w-4" aria-hidden />
          {status.merchant_name ?? 'Merchant'}
        </div>
        <p className="mt-1 text-xs text-ink-3">{status.description}</p>
        <p className="mt-6 text-xs text-ink-3">Amount</p>
        <p className="text-3xl font-semibold tracking-tight">{inr(status.amount_inr)}</p>

        <div className="mt-6 border-t border-rule/10 pt-5">
          {paid ? (
            <div role="status" className="space-y-1">
              <p className="flex items-center gap-2 font-medium text-settled">
                <SealCheck className="h-5 w-5" weight="fill" aria-hidden />
                Payment received
              </p>
              <p className="text-sm text-ink-3">
                You can close this tab. The conversation shows the payment as soon as you return to it.
              </p>
            </div>
          ) : status.sandbox ? (
            <>
              <Button variant="primary" className="w-full" onClick={simulate} disabled={checking}>
                Simulate successful payment
              </Button>
              <p className="mt-2 text-xs text-ink-3">
                Sandbox mode: no money moves. With Razorpay keys configured, links open Razorpay&rsquo;s
                checkout instead.
              </p>
            </>
          ) : (
            <ButtonLink href={status.short_url} className="w-full">
              Continue to Razorpay <ArrowSquareOut className="h-4 w-4" aria-hidden />
            </ButtonLink>
          )}
          {error && status && <p className="mt-2 text-xs text-void">{error}</p>}
        </div>
      </>
    );
  }

  return (
    <div className="flex min-h-full items-start justify-center p-4 pt-10 md:pt-20">
      <section
        aria-labelledby="checkout-title"
        className="w-full max-w-sm rounded-dialog border border-rule/10 bg-sheet-raised p-6"
      >
        <Eyebrow>Sandbox checkout</Eyebrow>
        <h1 id="checkout-title" className="sr-only">
          Pay settlement
        </h1>
        <div className="mt-4">{body}</div>
      </section>
    </div>
  );
}
