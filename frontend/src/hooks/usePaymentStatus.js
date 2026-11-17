import { useCallback, useEffect, useState } from 'react';
import { api, errorMessage } from '../lib/api';

/**
 * Status of one payment link. `check()` asks the backend (which asks the payment provider over MCP);
 * it also re-checks whenever the tab becomes visible again, e.g. after paying in another tab.
 */
export function usePaymentStatus(linkId, { auto = true } = {}) {
  const [status, setStatus] = useState(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState(null);

  const check = useCallback(() => {
    if (!linkId) return Promise.resolve();
    setChecking(true);
    return api.paymentStatus(linkId).then(
      (s) => {
        setStatus(s);
        setError(null);
        setChecking(false);
      },
      (e) => {
        setError(errorMessage(e));
        setChecking(false);
      },
    );
  }, [linkId]);

  const paid = status?.status === 'paid';
  useEffect(() => {
    if (!auto || !linkId || paid) return undefined;
    const onVisible = () => document.visibilityState === 'visible' && check();
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [auto, linkId, paid, check]);

  const simulate = () => {
    setChecking(true);
    return api.simulatePayment(linkId).then(
      (s) => {
        setStatus(s);
        setError(null);
        setChecking(false);
      },
      (e) => {
        setError(errorMessage(e));
        setChecking(false);
      },
    );
  };

  return { status, paid, checking, error, check, simulate };
}
