/**
 * How much of a merchant limit an offer uses. Track is a lighter step of the fill's own hue;
 * the fill turns amber when the guardrail had to correct the offer.
 */
export function BoundsMeter({ label, used, limit, format = (v) => v, corrected = false }) {
  if (!limit) {
    return (
      <div className="flex items-baseline justify-between gap-3 text-xs">
        <span className="text-ink-3">{label}</span>
        <span className="text-ink-2">Not allowed by policy</span>
      </div>
    );
  }
  const ratio = Math.max(0, Math.min(1, used / limit));
  const summary = `${format(used)} of ${format(limit)}`;
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 text-xs">
        <span className="text-ink-3">{label}</span>
        <span className="num text-ink-2">{summary}</span>
      </div>
      <div
        role="meter"
        aria-label={`${label}: ${summary}`}
        aria-valuemin={0}
        aria-valuemax={limit}
        aria-valuenow={used}
        className={`mt-1.5 h-1.5 overflow-hidden rounded-full ${corrected ? 'bg-caution/20' : 'bg-accent/15'}`}
      >
        <div
          className={`h-full rounded-full ${corrected ? 'bg-caution' : 'bg-accent'}`}
          style={{ width: `${ratio * 100}%` }}
        />
      </div>
    </div>
  );
}
