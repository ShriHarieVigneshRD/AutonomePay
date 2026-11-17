import { CaretRight } from '@phosphor-icons/react';
import { actionLabel, inr, pct } from '../../lib/format';
import { OUTCOMES, outcomeOf } from './CaseLedger';

function OutcomeLabel({ row }) {
  const { label, Icon, tone } = OUTCOMES[outcomeOf(row)];
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs text-ink-2">
      {Icon && <Icon className={`h-3.5 w-3.5 ${tone}`} weight="fill" aria-hidden />}
      {label}
    </span>
  );
}

const caseNo = (id) => id.replace('eval_case_', '#');
const WIDE_ONLY = new Set(['Turns', 'Latency']);

/** Full table view of a run (cards below 1024px). */
export function ResultsTable({ rows, onOpen }) {
  return (
    <section aria-label="Results" className="rounded-panel border border-rule/10 bg-sheet">
      <div className="hidden lg:block">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-rule/10 text-xs text-ink-3">
            <tr>
              {[
                'Case',
                'Scenario',
                'Turns',
                'Outcome',
                'Action',
                'Faithfulness',
                'Invoice',
                'Link',
                'Latency',
                '',
              ].map((h) => (
                <th
                  key={h}
                  scope="col"
                  className={`px-4 py-2.5 font-medium ${WIDE_ONLY.has(h) ? 'hidden xl:table-cell' : ''}`}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="num divide-y divide-rule/[0.07]">
            {rows.map((row) => (
              <tr key={row.run_id} className="transition-colors hover:bg-well/60">
                <td className="px-4 py-2.5 font-mono text-xs text-ink-3">{caseNo(row.test_id)}</td>
                <td className="max-w-[12rem] truncate xl:max-w-[16rem] px-4 py-2.5 text-ink">
                  {row.scenario_type.replaceAll('_', ' ').toLowerCase()}
                </td>
                <td className="hidden px-4 py-2.5 text-ink-2 xl:table-cell">{row.turns}</td>
                <td className="px-4 py-2.5">
                  <OutcomeLabel row={row} />
                </td>
                <td className="px-4 py-2.5 text-ink-2">{actionLabel(row.final_action)}</td>
                <td className="px-4 py-2.5 text-ink-2">{pct(row.rag_faithfulness * 100, 0)}</td>
                <td className="px-4 py-2.5 text-ink-2">{inr(row.invoice_inr)}</td>
                <td className="px-4 py-2.5 text-ink">{row.recovered_inr ? inr(row.recovered_inr) : '—'}</td>
                <td className="hidden px-4 py-2.5 text-ink-3 xl:table-cell">
                  {row.latency_ms ? `${Math.round(row.latency_ms)} ms` : '—'}
                </td>
                <td className="px-2 py-1.5 text-right">
                  <button
                    type="button"
                    onClick={() => onOpen(row)}
                    className="inline-flex h-8 items-center gap-1 rounded-control px-2.5 text-xs font-medium text-accent hover:bg-accent/10"
                  >
                    Trace <CaretRight className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="divide-y divide-rule/[0.07] lg:hidden">
        {rows.map((row) => (
          <li key={row.run_id}>
            <button
              type="button"
              onClick={() => onOpen(row)}
              className="flex w-full items-center gap-3 px-4 py-3 text-left"
            >
              <span className="num w-8 font-mono text-xs text-ink-3">{caseNo(row.test_id)}</span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm">
                  {row.scenario_type.replaceAll('_', ' ').toLowerCase()}
                </span>
                <OutcomeLabel row={row} />
              </span>
              <span className="num text-right text-sm text-ink-2">
                {row.recovered_inr ? inr(row.recovered_inr) : '—'}
              </span>
              <CaretRight className="h-4 w-4 text-ink-4" aria-hidden />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
