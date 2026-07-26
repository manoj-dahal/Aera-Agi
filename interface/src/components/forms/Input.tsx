/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react';
import { cn } from '@utils/cn';

const FIELD =
  'w-full rounded-[7px] border border-[var(--aera-line-default)] bg-[var(--aera-bg-surface)] px-3 py-2 text-[13px] text-[var(--aera-text-primary)] placeholder:text-[var(--aera-text-disabled)] focus:border-[var(--aera-accent-primary)]';

export function Input({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(FIELD, className)} {...rest} />;
}

export function Textarea({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(FIELD, 'resize-none', className)} {...rest} />;
}

export function Select({ className, children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cn(FIELD, 'cursor-default', className)} {...rest}>
      {children}
    </select>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11.5px] text-[var(--aera-text-muted)]">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[10.5px] text-[var(--aera-text-disabled)]">{hint}</span>}
    </label>
  );
}
