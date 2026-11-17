const inrFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const inrCompact = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  notation: 'compact',
  maximumFractionDigits: 1,
});

/** ₹2,350.00 (Indian digit grouping). Missing values render as an em dash. */
export const inr = (value) => (value === null || value === undefined ? '—' : inrFormatter.format(value));

/** ₹3.4L style, for headline figures. */
export const inrShort = (value) => (value === null || value === undefined ? '—' : inrCompact.format(value));

export const pct = (value, digits = 0) =>
  value === null || value === undefined ? '—' : `${value.toFixed(digits)}%`;

const FAILURE_REASONS = {
  INSUFFICIENT_FUNDS: 'Insufficient funds',
  ISSUER_DOWN: 'Bank issuer down',
  GATEWAY_TIMEOUT: 'Gateway timeout',
  PARTIAL_GOODS_DISPUTE: 'Disputed delivery',
};

export const failureReason = (code) =>
  FAILURE_REASONS[code] ?? code?.replaceAll('_', ' ').toLowerCase() ?? '—';

const ACTION_LABELS = {
  PROPOSE_SETTLEMENT: 'Renewal offer',
  PLAN_DOWNGRADE: 'Plan downgrade',
  MILESTONE_SPLIT: 'Instalments',
  PARTIAL_SETTLEMENT: 'Undisputed portion',
  EXTEND_GRACE: 'Grace extension',
  HUMAN_ESCALATION: 'Escalated to a person',
  GRACEFUL_DISCONTINUATION: 'Cancellation respected',
  BLOCKED: 'Blocked',
  NONE: 'No action',
};

export const actionLabel = (action) =>
  ACTION_LABELS[action] ?? action?.replaceAll('_', ' ').toLowerCase() ?? '—';

/** Guardrail status → verdict shown on the stamp. */
export function verdictOf(status) {
  if (status === 'ADVERSARIAL_INTERCEPTED') return 'blocked';
  if (status === 'POLICY_BREACH_CORRECTED') return 'corrected';
  return 'within';
}
