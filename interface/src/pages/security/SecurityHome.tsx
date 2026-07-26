/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import { useEffect, useState } from 'react';
import {
  Button,
  Card,
  DataTable,
  LoadingState,
  PageHeader,
  StatCard,
  StatRow,
  type Column,
} from '@components/index';
import { system } from '@services/api';
import { formatTime } from '@utils/format';
import type { AuditEntry } from '@services/types';

/** Audit trail and posture overview (docs/21-SECURITY.md). */
export function SecurityHome() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const { entries: rows } = await system.audit(100);
      setEntries(rows.slice().reverse());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'could not load the audit log');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => void load(), []);

  const allowed = entries.filter((e) => e.outcome === 'allowed').length;

  const columns: Column<AuditEntry>[] = [
    { key: 'time', header: 'Time', width: '110px', render: (r) => formatTime(r.timestamp) },
    { key: 'action', header: 'Action', render: (r) => <span className="font-mono text-[11.5px]">{r.action}</span> },
    { key: 'principal', header: 'Principal', render: (r) => r.principal },
    {
      key: 'outcome',
      header: 'Outcome',
      width: '100px',
      render: (r) => (
        <span style={{ color: r.outcome === 'allowed' ? 'var(--aera-success)' : 'var(--aera-danger)' }}>
          {r.outcome}
        </span>
      ),
    },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Security"
        subtitle="Zero-trust permissions, encrypted secrets and the audit trail"
        action={<Button variant="ghost" onClick={() => void load()}>Refresh</Button>}
      />

      {loading && <LoadingState label="Reading the audit log…" />}

      <StatRow>
        <StatCard label="Audit entries" value={entries.length} />
        <StatCard label="Allowed" value={allowed} accent="var(--aera-success)" />
        <StatCard
          label="Denied"
          value={entries.length - allowed}
          accent={entries.length - allowed ? 'var(--aera-danger)' : undefined}
        />
      </StatRow>

      <Card title="Posture" className="mb-4">
        <p className="text-[12px] leading-relaxed text-[var(--aera-text-muted)]">
          Secrets are encrypted at rest with a machine-local key. Terminal execution is
          disabled by default and restricted to an allowlist when enabled. Workspace reads
          are sandboxed to the opened project root.
        </p>
      </Card>

      {error ? (
        <p className="text-[12px] text-[var(--aera-danger)]">{error}</p>
      ) : (
        <DataTable
          columns={columns}
          rows={entries}
          rowKey={(row, i) => `${row.timestamp}-${i}`}
          empty="No audit entries recorded yet."
        />
      )}
    </div>
  );
}

export default SecurityHome;
