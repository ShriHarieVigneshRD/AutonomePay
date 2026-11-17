import { WarningCircle } from '@phosphor-icons/react';
import { Button } from './Button';

export function Skeleton({ className = '' }) {
  return (
    <div
      aria-hidden
      className={`animate-shimmer rounded-control bg-[linear-gradient(90deg,rgb(var(--well))_0%,rgb(var(--rule)/0.06)_50%,rgb(var(--well))_100%)] bg-[length:200%_100%] ${className}`}
    />
  );
}

export function EmptyState({ icon: Icon, title, children, action, className = '' }) {
  return (
    <div className={`flex flex-col items-center justify-center gap-2 px-6 py-10 text-center ${className}`}>
      {Icon && <Icon className="h-6 w-6 text-ink-4" aria-hidden />}
      <p className="text-sm font-medium text-ink-2">{title}</p>
      {children && <p className="max-w-[40ch] text-xs text-ink-3">{children}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry, className = '' }) {
  return (
    <div
      role="alert"
      className={`flex items-start gap-3 rounded-panel border border-void/30 bg-void/[0.06] px-4 py-3 text-sm ${className}`}
    >
      <WarningCircle className="mt-0.5 h-4 w-4 shrink-0 text-void" weight="bold" aria-hidden />
      <p className="flex-1 text-ink-2">{message}</p>
      {onRetry && (
        <Button size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
