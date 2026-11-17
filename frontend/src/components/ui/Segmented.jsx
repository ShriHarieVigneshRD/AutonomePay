import { useRef } from 'react';

/**
 * Accessible tab strip (role="tablist"): arrow keys move between options.
 * Pass `controls` (id prefix) so each tab points at its panel `${controls}-${value}`.
 */
export function Segmented({ options, value, onChange, label, controls, className = '', size = 'md' }) {
  const refs = useRef([]);
  const onKeyDown = (event, index) => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    const next = (index + step + options.length) % options.length;
    onChange(options[next].value);
    refs.current[next]?.focus();
  };
  return (
    <div
      role="tablist"
      aria-label={label}
      className={`inline-flex rounded-control bg-well p-0.5 ${className}`}
    >
      {options.map((option, index) => {
        const selected = option.value === value;
        const Icon = option.icon;
        return (
          <button
            key={option.value}
            ref={(el) => (refs.current[index] = el)}
            type="button"
            role="tab"
            id={controls ? `${controls}-tab-${option.value}` : undefined}
            aria-controls={controls ? `${controls}-${option.value}` : undefined}
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(option.value)}
            onKeyDown={(e) => onKeyDown(e, index)}
            className={`inline-flex flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-[5px] font-medium transition-colors duration-150 ${
              size === 'sm' ? 'h-7 px-2.5 text-xs' : 'h-8 px-3 text-sm max-md:min-h-10'
            } ${selected ? 'bg-sheet-raised text-ink shadow-[0_0_0_1px_rgb(var(--rule)/0.1)]' : 'text-ink-3 hover:text-ink'}`}
          >
            {Icon && <Icon className="h-4 w-4" aria-hidden />}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
