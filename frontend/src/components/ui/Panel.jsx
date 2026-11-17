export function Panel({
  title,
  aside,
  children,
  className = '',
  bodyClassName = '',
  as: Tag = 'section',
  ...rest
}) {
  return (
    <Tag
      className={`flex min-h-0 flex-col rounded-panel border border-rule/10 bg-sheet ${className}`}
      {...rest}
    >
      {(title || aside) && (
        <header className="flex items-center justify-between gap-3 border-b border-rule/10 px-4 py-3">
          {title && <h2 className="text-sm font-semibold tracking-tight text-ink">{title}</h2>}
          {aside}
        </header>
      )}
      <div className={`min-h-0 flex-1 ${bodyClassName}`}>{children}</div>
    </Tag>
  );
}

/** Small uppercase section label inside panels. */
export function Eyebrow({ children, className = '' }) {
  return (
    <p className={`text-xs font-medium uppercase tracking-[0.08em] text-ink-3 ${className}`}>{children}</p>
  );
}
