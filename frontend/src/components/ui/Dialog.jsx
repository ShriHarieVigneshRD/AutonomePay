import { useEffect, useRef } from 'react';

/**
 * Native <dialog>: focus trap, Escape and focus return come from the platform.
 * `variant="sheet"` docks to the right on desktop and fills the screen on mobile.
 */
export function Dialog({ open, onClose, labelledBy, variant = 'center', className = '', children }) {
  const ref = useRef(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const placement =
    variant === 'sheet'
      ? 'm-0 ml-auto h-dvh max-h-dvh w-full max-w-xl rounded-none sm:rounded-l-dialog'
      : 'w-[calc(100%-2rem)] max-w-2xl rounded-dialog max-sm:m-0 max-sm:h-dvh max-sm:max-h-dvh max-sm:w-full max-sm:max-w-none max-sm:rounded-none';

  return (
    <dialog
      ref={ref}
      aria-labelledby={labelledBy}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => e.target === ref.current && onClose()}
      className={`border border-rule/10 bg-sheet-raised p-0 text-ink shadow-[0_0_0_1px_rgb(var(--rule)/0.06),0_24px_48px_-12px_rgb(0_0_0/0.25)] backdrop:backdrop-blur-[2px] open:animate-stamp ${placement} ${className}`}
    >
      {open && children}
    </dialog>
  );
}
