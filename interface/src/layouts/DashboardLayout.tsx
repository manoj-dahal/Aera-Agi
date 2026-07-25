import type { ReactNode } from 'react';

/** Split view: primary content plus a right-hand context pane. */
export function DashboardLayout({
  children,
  context,
}: {
  children: ReactNode;
  context?: ReactNode;
}) {
  return (
    <div className="flex min-w-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col">{children}</div>
      {context && (
        <aside className="w-[280px] shrink-0 overflow-y-auto border-l border-[var(--aera-line-default)] bg-[var(--aera-bg-raised)] p-3.5">
          {context}
        </aside>
      )}
    </div>
  );
}
