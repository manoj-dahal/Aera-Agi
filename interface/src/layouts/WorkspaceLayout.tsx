/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import type { ReactNode } from 'react';

/** Master/detail layout: a scrollable list beside a preview pane. */
export function WorkspaceLayout({
  toolbar,
  list,
  detail,
}: {
  toolbar?: ReactNode;
  list: ReactNode;
  detail: ReactNode;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col p-4">
      {toolbar}
      <div className="flex min-h-0 flex-1 gap-2.5">
        <div className="w-[330px] shrink-0 overflow-y-auto">{list}</div>
        <div className="flex min-w-0 flex-1 flex-col">{detail}</div>
      </div>
    </div>
  );
}
