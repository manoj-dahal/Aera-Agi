import { cn } from '@utils/cn';

/** Horizontal proportion bar used for language and type breakdowns. */
export function BarMeter({
  label,
  value,
  total,
  color = 'var(--aera-accent-primary)',
  className,
}: {
  label: string;
  value: number;
  total: number;
  color?: string;
  className?: string;
}) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className={cn('mb-1.5', className)}>
      <div className="mb-0.5 flex justify-between text-[11px]">
        <span className="text-[var(--aera-text-muted)]">{label}</span>
        <span>{value}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[var(--aera-bg-overlay)]">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}
