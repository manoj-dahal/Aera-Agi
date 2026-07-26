/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import type { SystemEvent } from '@services/types';
import { timeAgo } from '@utils/format';

export function EventFeed({ events }: { events: SystemEvent[] }) {
  if (events.length === 0) {
    return (
      <p className="text-[11.5px] text-[var(--aera-text-disabled)]">
        No activity yet.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      {events.map((event) => {
        const p = event.payload as Record<string, unknown>;
        const detail = (p.agent ?? p.title ?? p.provider ?? p.workflow ?? p.query ?? '') as string;
        return (
          <div
            key={event.id}
            className="animate-rise rounded-[6px] border-l-2 border-[var(--aera-accent-primary)] bg-[var(--aera-bg-surface)] px-2.5 py-1.5"
          >
            <div className="font-mono text-[10px] text-[var(--aera-accent-primary)]">
              {event.topic}
            </div>
            {detail && (
              <div className="mt-0.5 break-words text-[11px] text-[var(--aera-text-muted)]">
                {String(detail)}
              </div>
            )}
            <div className="text-[9.5px] text-[var(--aera-text-disabled)]">
              {timeAgo(event.timestamp)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
