/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import type { SystemStatus } from '@services/types';

/**
 * "AI Core" panel: active model, agent and memory status
 * (docs/04-DASHBOARD.md, left column).
 */
export function AICorePanel({
  status,
  activeAgent,
  processing,
}: {
  status: SystemStatus | null;
  activeAgent?: string;
  processing?: boolean;
}) {
  const rows: Array<[string, string]> = [
    ['Active AI', status?.providers?.[0] ?? '—'],
    ['Model', (status?.providers ?? []).join(', ') || 'built-in'],
    ['State', processing ? 'processing' : (status?.ready ? 'ready' : 'starting')],
    ['Agent', activeAgent ?? 'core'],
    ['Memory', `${status?.memory?.nodes ?? 0} nodes`],
  ];

  return (
    <div className="rounded-[10px] border border-[var(--aera-line-strong)] bg-[var(--aera-bg-surface)] p-3">
      <div className="mb-2 text-center text-[9.5px] uppercase tracking-[0.14em] text-[var(--aera-text-muted)]">
        System Info
      </div>
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between gap-2 py-[3px] text-[11px]">
          <span className="text-[var(--aera-text-muted)]">{label}</span>
          <span className="truncate text-right" title={value}>
            {value}
          </span>
        </div>
      ))}
    </div>
  );
}
