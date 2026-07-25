import type { ReactNode } from 'react';
import { cn } from '@utils/cn';

export interface StatCardProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  accent?: string;
  className?: string;
}

export function StatCard({ label, value, hint, accent, className }: StatCardProps) {
  return (
    <div
      className={cn(
        'min-w-[104px] rounded-[9px] border border-[var(--aera-line-default)] bg-[var(--aera-bg-surface)] px-3.5 py-2.5',
        className,
      )}
    >
      <div className="text-[10px] uppercase tracking-[0.07em] text-[var(--aera-text-muted)]">
        {label}
      </div>
      <div
        className="mt-0.5 text-[19px] font-semibold leading-tight"
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </div>
      {hint && <div className="text-[10.5px] text-[var(--aera-text-muted)]">{hint}</div>}
    </div>
  );
}

export function StatRow({ children }: { children: ReactNode }) {
  return <div className="mb-3.5 flex flex-wrap gap-2">{children}</div>;
}
