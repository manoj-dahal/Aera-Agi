/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import { cn } from '@utils/cn';
import type { SystemStatus } from '@services/types';
import { formatNumber } from '@utils/format';

export interface StatusBarProps {
  status: SystemStatus | null;
  connected: boolean;
}

function Chip({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'max-w-[220px] truncate rounded-[5px] border border-[var(--aera-line-default)] bg-[var(--aera-bg-surface)] px-2.5 py-[3px] text-[11px] text-[var(--aera-text-muted)]',
        className,
      )}
    >
      {children}
    </span>
  );
}

export function StatusBar({ status, connected }: StatusBarProps) {
  const workspace = status?.workspace as { name?: string } | undefined;

  return (
    <header className="flex shrink-0 items-center justify-between border-b border-[var(--aera-line-default)] bg-[var(--aera-bg-raised)] px-3.5 py-1.5">
      <div className="flex items-center gap-2 text-[12px] font-semibold tracking-[0.16em]">
        <span className="text-gradient text-[15px]">◈</span>
        AERA
      </div>

      <div className="flex items-center gap-1.5">
        <Chip>{workspace?.name ?? 'No project'}</Chip>
        <Chip>{status?.providers?.join(' · ') || 'no model'}</Chip>
        <Chip>
          {status ? `${status.agents.running}/${status.agents.total}` : '0/0'} agents
        </Chip>
        <Chip>{formatNumber(status?.memory?.nodes ?? 0)} memories</Chip>
        <Chip className="flex items-center gap-1.5">
          <i
            className="h-1.5 w-1.5 rounded-full"
            style={{
              background: connected ? 'var(--aera-success)' : 'var(--aera-warning)',
              boxShadow: `0 0 6px ${connected ? 'var(--aera-success)' : 'var(--aera-warning)'}`,
            }}
          />
          kernel
        </Chip>
      </div>
    </header>
  );
}
