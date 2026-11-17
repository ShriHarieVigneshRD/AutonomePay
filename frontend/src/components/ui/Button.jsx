const VARIANTS = {
  primary: 'bg-accent text-accent-on hover:bg-accent/90',
  secondary: 'border border-rule/15 bg-sheet-raised text-ink hover:bg-well',
  ghost: 'text-ink-2 hover:bg-well hover:text-ink',
};
const SIZES = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-9 px-4 text-sm',
};

export function Button({ variant = 'secondary', size = 'md', className = '', ...props }) {
  return (
    <button
      type="button"
      className={`inline-flex shrink-0 items-center justify-center gap-2 rounded-control font-medium transition-[transform,background-color,color] duration-150 ease-out active:scale-[0.97] disabled:pointer-events-none disabled:opacity-50 max-md:min-h-11 ${SIZES[size]} ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}

/** A link styled as a button (for real navigation, e.g. a payment link). */
export function ButtonLink({ variant = 'primary', size = 'md', className = '', ...props }) {
  return (
    <a
      className={`inline-flex items-center justify-center gap-2 rounded-control font-medium transition-[transform,background-color] duration-150 ease-out active:scale-[0.97] max-md:min-h-11 ${SIZES[size]} ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}
