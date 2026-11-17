import { useState } from 'react';
import { CaretDown, Check, MagnifyingGlass, X } from '@phosphor-icons/react';
import { Button } from '../../components/ui/Button';
import { Dialog } from '../../components/ui/Dialog';
import { Segmented } from '../../components/ui/Segmented';
import { inr } from '../../lib/format';

const GROUPS = [
  { value: 'merchant', label: 'Merchant' },
  { value: 'intent', label: 'Intent' },
  { value: 'sector', label: 'Sector' },
  { value: 'flat', label: 'All' },
];
const FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'multi', label: 'Multi-turn' },
  { value: 'single', label: 'Single-turn' },
  { value: 'adversarial', label: 'Adversarial' },
];

const caseNumber = (id) => id.replace('eval_case_', '#');

export function filterScenarios(scenarios, query, filter) {
  const q = query.toLowerCase().trim();
  return scenarios.filter((sc) => {
    const haystack = [
      sc.title,
      sc.id,
      sc.merchant_name,
      sc.customer_name,
      sc.category,
      sc.scenario_type_title,
    ]
      .join(' ')
      .toLowerCase();
    if (q && !haystack.includes(q)) return false;
    if (filter === 'multi') return sc.is_multi_turn;
    if (filter === 'single') return !sc.is_multi_turn;
    if (filter === 'adversarial') return sc.scenario_type.startsWith('ADVERSARIAL_');
    return true;
  });
}

export function groupScenarios(scenarios, groupBy) {
  if (groupBy === 'flat') return [['All cases', scenarios]];
  const key = { merchant: 'merchant_name', intent: 'scenario_type_title', sector: 'category' }[groupBy];
  const groups = new Map();
  for (const sc of scenarios) {
    const name = sc[key] || 'Other';
    groups.set(name, [...(groups.get(name) ?? []), sc]);
  }
  return [...groups.entries()];
}

export function ScenarioPicker({ scenarios, active, onSelect, disabled }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [groupBy, setGroupBy] = useState('merchant');
  const [filter, setFilter] = useState('all');
  const groups = groupScenarios(filterScenarios(scenarios, query, filter), groupBy);

  const choose = (scenario) => {
    onSelect(scenario);
    setOpen(false);
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={disabled}
        aria-haspopup="dialog"
        className="group flex h-10 min-w-0 max-w-full items-center gap-2 rounded-control border border-rule/15 bg-sheet px-3 text-left text-sm transition-colors hover:border-accent/40 disabled:opacity-60"
      >
        <span className="num shrink-0 font-mono text-xs text-ink-3">
          {active ? caseNumber(active.id) : '—'}
        </span>
        <span className="min-w-0 truncate font-medium">
          {active ? `${active.merchant_name} · ${active.scenario_type_title}` : 'Loading cases…'}
        </span>
        <CaretDown className="ml-1 h-4 w-4 shrink-0 text-ink-3 group-hover:text-ink" aria-hidden />
        <span className="sr-only">Change case</span>
      </button>

      <Dialog open={open} onClose={() => setOpen(false)} labelledBy="case-browser-title" className="flex-col">
        <div className="flex max-h-[min(720px,100dvh)] flex-col max-sm:h-dvh">
          <div className="space-y-3 border-b border-rule/10 p-4">
            <div className="flex items-center justify-between gap-3">
              <h2 id="case-browser-title" className="text-base font-semibold tracking-tight">
                Choose a case{' '}
                <span className="font-normal text-ink-3">· {scenarios.length} benchmark scenarios</span>
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setOpen(false)}
                aria-label="Close case browser"
              >
                <X className="h-4 w-4" aria-hidden />
              </Button>
            </div>
            <label className="relative block">
              <span className="sr-only">Search cases</span>
              <MagnifyingGlass
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-4"
                aria-hidden
              />
              <input
                type="search"
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by merchant, customer, case # or intent"
                className="h-10 w-full rounded-control border border-rule/10 bg-well pl-9 pr-3 text-base placeholder:text-ink-4 focus:border-accent/50 md:text-sm"
              />
            </label>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Segmented
                options={GROUPS}
                value={groupBy}
                onChange={setGroupBy}
                label="Group cases by"
                size="sm"
              />
              <Segmented
                options={FILTERS}
                value={filter}
                onChange={setFilter}
                label="Filter cases"
                size="sm"
              />
            </div>
          </div>

          <div className="scroll-quiet min-h-0 flex-1 overflow-y-auto p-2">
            {groups.length === 0 ? (
              <p className="px-3 py-10 text-center text-sm text-ink-3">
                No cases match &ldquo;{query}&rdquo;.
              </p>
            ) : (
              groups.map(([name, cases]) => (
                <section key={name} aria-label={name} className="mb-2">
                  <h3 className="sticky top-0 z-10 flex justify-between bg-sheet-raised px-3 py-1.5 text-xs font-medium uppercase tracking-[0.08em] text-ink-3">
                    {name}
                    <span className="num">{cases.length}</span>
                  </h3>
                  <ul>
                    {cases.map((sc) => {
                      const current = sc.id === active?.id;
                      return (
                        <li key={sc.id}>
                          <button
                            type="button"
                            onClick={() => choose(sc)}
                            aria-current={current ? 'true' : undefined}
                            className={`flex w-full items-center gap-3 rounded-control px-3 py-2 text-left transition-colors ${
                              current ? 'bg-accent/10' : 'hover:bg-well'
                            }`}
                          >
                            <span className="num w-9 shrink-0 font-mono text-xs text-ink-3">
                              {caseNumber(sc.id)}
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-sm font-medium">
                                {sc.merchant_name} · {sc.scenario_type_title}
                              </span>
                              <span className="block truncate text-xs text-ink-3">
                                {sc.customer_name} · {sc.plan_name} ·{' '}
                                {sc.is_multi_turn ? 'multi-turn' : 'single-turn'}
                              </span>
                            </span>
                            <span className="num shrink-0 text-xs text-ink-2">{inr(sc.original_amount)}</span>
                            {current && (
                              <Check className="h-4 w-4 shrink-0 text-accent" weight="bold" aria-hidden />
                            )}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              ))
            )}
          </div>
        </div>
      </Dialog>
    </>
  );
}
