/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import type { ReactNode } from 'react';

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  width?: string;
}

export function DataTable<T>({
  columns,
  rows,
  empty = 'No rows.',
  rowKey,
}: {
  columns: Column<T>[];
  rows: T[];
  empty?: string;
  rowKey: (row: T, index: number) => string;
}) {
  if (rows.length === 0) {
    return (
      <p className="px-4 py-8 text-center text-[12.5px] text-[var(--aera-text-muted)]">{empty}</p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-[9px] border border-[var(--aera-line-default)]">
      <table className="w-full border-collapse text-[12.5px]">
        <thead>
          <tr className="bg-[var(--aera-bg-surface)]">
            {columns.map((column) => (
              <th
                key={column.key}
                style={column.width ? { width: column.width } : undefined}
                className="border-b border-[var(--aera-line-default)] px-3 py-2 text-left text-[10.5px] uppercase tracking-[0.07em] text-[var(--aera-text-muted)]"
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              key={rowKey(row, index)}
              className="border-b border-[var(--aera-line-subtle)] last:border-0 hover:bg-[var(--aera-bg-surface)]"
            >
              {columns.map((column) => (
                <td key={column.key} className="px-3 py-2 align-top">
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
