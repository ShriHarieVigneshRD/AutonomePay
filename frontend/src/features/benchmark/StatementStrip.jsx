import { inr, inrShort, pct } from '../../lib/format';

function Stat({ label, value, hint }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-ink-3">{label}</dt>
      <dd className="mt-1 text-lg font-semibold tracking-tight text-ink">{value}</dd>
      {hint && <dd className="text-xs text-ink-3">{hint}</dd>}
    </div>
  );
}

/** One hero figure (recovered via links) and the supporting measured KPIs. */
export function StatementStrip({ kpi, totalCases }) {
  const recoveredShare =
    kpi.total_invoiced && kpi.total_recovered !== undefined
      ? (100 * kpi.total_recovered) / kpi.total_invoiced
      : null;

  return (
    <section
      aria-label="Benchmark summary"
      className="rounded-panel border border-rule/10 bg-sheet p-5 md:p-6"
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)] lg:items-end">
        <div>
          <p className="text-xs text-ink-3">Covered by issued payment links</p>
          <p
            className="mt-1 text-hero font-semibold tracking-[-0.03em] text-ink"
            title={inr(kpi.total_recovered)}
          >
            {inrShort(kpi.total_recovered)}
          </p>
          <p className="mt-1 text-sm text-ink-2">
            of {inr(kpi.total_invoiced)} invoiced across {totalCases} cases
            {recoveredShare !== null && <span className="text-ink-3"> · {pct(recoveredShare)}</span>}
          </p>
        </div>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3 xl:grid-cols-6">
          <Stat label="Pass rate" value={pct(kpi.pass_rate_pct)} hint="vs expected outcome" />
          <Stat label="Links issued" value={kpi.links_issued ?? '—'} />
          <Stat
            label="Guardrail corrections"
            value={kpi.policy_breaches ?? '—'}
            hint="caught before sending"
          />
          <Stat label="Injections blocked" value={kpi.adversarial_intercepts ?? '—'} />
          <Stat label="RAG faithfulness" value={pct(kpi.rag_faithfulness_pct, 1)} />
          <Stat
            label="Avg latency / turn"
            value={
              kpi.avg_latency_ms !== null && kpi.avg_latency_ms !== undefined
                ? `${Math.round(kpi.avg_latency_ms)} ms`
                : '—'
            }
            hint={kpi.tokens_used ? `${kpi.tokens_used.toLocaleString('en-IN')} tokens` : undefined}
          />
        </dl>
      </div>
    </section>
  );
}
