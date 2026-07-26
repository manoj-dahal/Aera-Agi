/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import type { ReactNode } from 'react';
import { cn } from '@utils/cn';

export function SectionTitle({
  children,
  action,
  className,
}: {
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('mb-2.5 mt-4 flex items-center justify-between first:mt-0', className)}>
      <h3 className="text-[10.5px] uppercase tracking-[0.11em] text-[var(--aera-text-muted)]">
        {children}
      </h3>
      {action}
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <div>
        <h2 className="text-[20px] font-semibold leading-tight">{title}</h2>
        {subtitle && (
          <p className="mt-0.5 text-[12.5px] text-[var(--aera-text-muted)]">{subtitle}</p>
        )}
      </div>
      {action}
    </div>
  );
}
