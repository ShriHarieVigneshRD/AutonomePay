import { CheckCircle, Prohibit, WarningDiamond, XCircle } from '@phosphor-icons/react';
import { actionLabel } from '../../lib/format';

export const OUTCOMES = {
  within: {
    label: 'Within bounds',
    Icon: CheckCircle,
    tone: 'text-settled',
    cell: 'border-settled/30 bg-settled/10',
  },
  corrected: {
    label: 'Corrected',
    Icon: WarningDiamond,
    tone: 'text-caution-ink',
    cell: 'border-caution/40 bg-caution/15',
  },
  blocked: {
    label: 'Injection blocked',
    Icon: Prohibit,
    tone: 'text-void',
    cell: 'border-void/30 bg-void/10',
  },
  failed: {
    label: 'Missed expected outcome',
    Icon: XCircle,
    tone: 'text-void',
    cell: 'border-void/50 bg-void/5',
  },
  pending: { label: 'Not run yet', Icon: null, tone: 'text-ink-4', cell: 'border-dashed border-rule/25' },
};

export function outcomeOf(row) {
  if (!row) return 'pending';
  if (row.guardrail_status === 'ADVERSARIAL_INTERCEPTED') return 'blocked';
  if (row.passed === false) return 'failed';
  if (row.guardrail_status === 'POLICY_BREACH_CORRECTED') return 'corrected';
  return 'within';
}

/**
 * One cell per benchmark case. Outcome is encoded three ways (colour, icon, legend label) so it
 * never depends on colour alone; the results table below is the full table view.
 */
export function CaseLedger({ rows, total, onOpen }) {
  const byId = new Map(rows.map((r) => [r.test_id, r]));
  const ids = Array.from({ length: total }, (_, i) => `eval_case_${String(i + 1).padStart(2, '0')}`);
  const counts = ids.reduce((acc, id) => {
    const o = outcomeOf(byId.get(id));
    acc[o] = (acc[o] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <section
      aria-labelledby="ledger-title"
      className="rounded-panel border border-rule/10 bg-sheet p-4 md:p-5"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 id="ledger-title" className="text-sm font-semibold tracking-tight">
          Case ledger
        </h2>
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2" aria-label="Legend">
          {Object.entries(OUTCOMES)
            .filter(([key]) => counts[key])
            .map(([key, { label, Icon }]) => (
              <li key={key} className="flex items-center gap-1.5">
                {Icon ? (
                  <Icon className={`h-3.5 w-3.5 ${OUTCOMES[key].tone}`} weight="fill" aria-hidden />
                ) : (
                  <span className="h-3 w-3 rounded-[3px] border border-dashed border-rule/40" aria-hidden />
                )}
                {label} <span className="num text-ink-3">{counts[key]}</span>
              </li>
            ))}
        </ul>
      </div>

      <ol className="mt-4 grid grid-cols-5 gap-1.5 sm:grid-cols-10">
        {ids.map((id, i) => {
          const row = byId.get(id);
          const outcome = outcomeOf(row);
          const { label, Icon, cell, tone } = OUTCOMES[outcome];
          const name = `Case ${i + 1}: ${label}${row ? `, ${actionLabel(row.final_action)}` : ''}`;
          return (
            <li key={id}>
              <button
                type="button"
                disabled={!row}
                onClick={() => onOpen(row)}
                title={name}
                aria-label={name}
                className={`flex h-10 w-full items-center justify-center gap-1 rounded-control border text-xs font-medium transition-transform duration-150 ease-out enabled:hover:-translate-y-px enabled:active:scale-[0.97] ${cell} ${tone}`}
              >
                <span className="num">{i + 1}</span>
                {Icon && <Icon className="h-3.5 w-3.5" weight="fill" aria-hidden />}
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
