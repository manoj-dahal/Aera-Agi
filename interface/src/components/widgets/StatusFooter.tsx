/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import type { SystemStatus } from '@services/types';
import { formatNumber, formatUptime } from '@utils/format';

/** Bottom status bar (docs/04-DASHBOARD.md). */
export function StatusFooter({
  status,
  connected,
  activeAgent,
}: {
  status: SystemStatus | null;
  connected: boolean;
  activeAgent?: string;
}) {
  const items: Array<[string, string]> = [
    ['Model', (status?.providers ?? []).join(' · ') || 'built-in'],
    ['Agent', activeAgent ?? 'core'],
    ['Agents', `${status?.agents?.running ?? 0}/${status?.agents?.total ?? 0}`],
    ['Memory', formatNumber(status?.memory?.nodes ?? 0)],
    ['Events', formatNumber(status?.events_published ?? 0)],
    ['Uptime', formatUptime(status?.uptime_seconds ?? 0)],
  ];

  return (
    <footer className="flex shrink-0 items-center gap-4 border-t border-[var(--aera-line-default)] bg-[var(--aera-bg-raised)] px-4 py-1.5 text-[10.5px]">
      {items.map(([label, value]) => (
        <span key={label} className="flex items-center gap-1.5">
          <span className="text-[var(--aera-text-disabled)]">{label}</span>
          <span className="text-[var(--aera-text-secondary)]">{value}</span>
        </span>
      ))}
      <span className="ml-auto flex items-center gap-1.5">
        <i
          className="h-1.5 w-1.5 rounded-full"
          style={{
            background: connected ? 'var(--aera-success)' : 'var(--aera-warning)',
            boxShadow: `0 0 6px ${connected ? 'var(--aera-success)' : 'var(--aera-warning)'}`,
          }}
        />
        <span className="text-[var(--aera-text-secondary)]">
          {connected ? 'Connected' : 'Starting'}
        </span>
      </span>
    </footer>
  );
}
