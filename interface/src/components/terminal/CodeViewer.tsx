/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import { cn } from '@utils/cn';

/** Read-only monospace viewer used for file previews and logs. */
export function CodeViewer({
  content,
  emptyMessage = 'Nothing to display.',
  className,
}: {
  content?: string;
  emptyMessage?: string;
  className?: string;
}) {
  return (
    <pre
      className={cn(
        'selectable min-h-0 flex-1 overflow-auto rounded-[9px] border border-[var(--aera-line-default)] bg-[var(--aera-bg-raised)] p-3.5 font-mono text-[11.5px] leading-relaxed text-[var(--aera-text-secondary)]',
        className,
      )}
    >
      {content || emptyMessage}
    </pre>
  );
}
