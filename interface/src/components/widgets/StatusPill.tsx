import { agentStatusColors, type AgentStatus } from '@design/colors';
import { cn } from '@utils/cn';

export interface StatusPillProps {
  status: string;
  label?: string;
  className?: string;
}

/** Small coloured status chip used for agents, providers and runs. */
export function StatusPill({ status, label, className }: StatusPillProps) {
  const color =
    agentStatusColors[status as AgentStatus] ??
    (status === 'success' || status === 'healthy'
      ? agentStatusColors.running
      : status === 'failed' || status === 'offline'
        ? agentStatusColors.error
        : agentStatusColors.idle);

  return (
    <span
      className={cn(
        'rounded-full px-2 py-[2px] text-[9.5px] uppercase tracking-[0.05em]',
        className,
      )}
      style={{ color, backgroundColor: `${color}22` }}
    >
      {label ?? status}
    </span>
  );
}

export function Tag({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'rounded-[4px] bg-[var(--aera-bg-overlay)] px-1.5 py-[2px] text-[9.5px] text-[var(--aera-text-muted)]',
        className,
      )}
    >
      {children}
    </span>
  );
}
