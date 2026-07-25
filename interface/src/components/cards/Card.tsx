import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@utils/cn';

// `title` is redefined as a ReactNode heading, so the native string attribute
// is omitted to avoid a conflicting declaration.
export interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: ReactNode;
  action?: ReactNode;
  interactive?: boolean;
  padded?: boolean;
}

export function Card({
  title,
  action,
  interactive = false,
  padded = true,
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <div
      className={cn(
        'rounded-[10px] border border-[var(--aera-line-default)] bg-[var(--aera-bg-surface)] transition-colors',
        padded && 'p-3.5',
        interactive && 'cursor-default hover:border-[var(--aera-accent-primary)]',
        !interactive && 'hover:border-[var(--aera-line-strong)]',
        className,
      )}
      {...rest}
    >
      {(title || action) && (
        <div className="mb-1.5 flex items-center justify-between gap-2">
          {typeof title === 'string' ? (
            <h4 className="text-[13px] font-semibold">{title}</h4>
          ) : (
            title
          )}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

export function CardGrid({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'grid content-start gap-2 [grid-template-columns:repeat(auto-fill,minmax(265px,1fr))]',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Label/value row used inside cards. */
export function KeyValue({ label, value }: { label: ReactNode; value: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 py-0.5 text-[11.5px]">
      <span className="text-[var(--aera-text-muted)]">{label}</span>
      <span className="selectable break-all text-right">{value}</span>
    </div>
  );
}
