import { Prohibit, SealCheck, WarningDiamond } from '@phosphor-icons/react';

export const VERDICTS = {
  within: { label: 'Within bounds', className: 'border-settled text-settled', Icon: SealCheck },
  corrected: { label: 'Corrected', className: 'border-caution text-caution-ink', Icon: WarningDiamond },
  blocked: { label: 'Blocked', className: 'border-void text-void', Icon: Prohibit },
};

/** The guardrail verdict, inked like a rubber stamp. Always icon + label, never colour alone. */
export function Stamp({ verdict = 'within', animate = false, className = '' }) {
  const { label, className: tone, Icon } = VERDICTS[verdict] ?? VERDICTS.within;
  return (
    <span
      className={`inline-flex -rotate-1 items-center gap-1.5 rounded-[4px] border-[1.5px] px-2 py-0.5 text-xs font-semibold uppercase tracking-[0.08em] ${tone} ${animate ? 'animate-stamp' : ''} ${className}`}
    >
      <Icon className="h-3.5 w-3.5" weight="bold" aria-hidden />
      {label}
    </span>
  );
}
