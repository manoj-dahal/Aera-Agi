import type { ReactNode } from 'react';

export interface EmptyStateProps {
  title?: string;
  message: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <div className="col-span-full flex flex-col items-center gap-2 px-5 py-10 text-center">
      {title && <h3 className="text-[15px] font-medium">{title}</h3>}
      <p className="max-w-md text-[12.5px] text-[var(--aera-text-muted)]">{message}</p>
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="col-span-full px-5 py-8 text-center">
      <p className="text-[12.5px] text-[var(--aera-danger)]">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 text-[12px] text-[var(--aera-accent-primary)] underline"
        >
          Try again
        </button>
      )}
    </div>
  );
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="col-span-full flex items-center justify-center gap-2 py-10 text-[12.5px] text-[var(--aera-text-muted)]">
      <span className="animate-spin-slow">◌</span>
      {label}
    </div>
  );
}
