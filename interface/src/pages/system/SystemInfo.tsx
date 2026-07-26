/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import { useEffect, useState } from 'react';
import { Button, Card, CardGrid, KeyValue, PageHeader, StatCard, StatRow } from '@components/index';
import { system } from '@services/api';
import { useSystemStore } from '@store/index';
import { formatNumber, formatUptime, titleCase } from '@utils/format';

/** Runtime information and live counters (docs/23-PERFORMANCE.md). */
export function SystemInfo() {
  const { status, refresh } = useSystemStore();
  const [info, setInfo] = useState<Record<string, string | boolean>>({});

  useEffect(() => {
    void system.info().then(setInfo).catch(() => {});
  }, []);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="System"
        subtitle="Runtime, resource and subsystem status"
        action={<Button variant="ghost" onClick={() => void refresh()}>Refresh</Button>}
      />

      <StatRow>
        <StatCard label="Uptime" value={formatUptime(status?.uptime_seconds ?? 0)} />
        <StatCard label="Agents" value={`${status?.agents.running ?? 0}/${status?.agents.total ?? 0}`} />
        <StatCard label="Memories" value={formatNumber(status?.memory?.nodes ?? 0)} />
        <StatCard label="Edges" value={formatNumber(status?.memory?.edges ?? 0)} />
        <StatCard label="Events" value={formatNumber(status?.events_published ?? 0)} />
      </StatRow>

      <CardGrid>
        <Card title="Runtime">
          {Object.entries(info).map(([key, value]) => (
            <KeyValue key={key} label={titleCase(key)} value={String(value)} />
          ))}
        </Card>

        <Card title="Memory graph">
          {Object.entries(status?.memory?.by_memory_type ?? {}).map(([key, value]) => (
            <KeyValue key={key} label={titleCase(key)} value={value} />
          ))}
        </Card>

        <Card title="Node types">
          {Object.entries(status?.memory?.by_type ?? {}).map(([key, value]) => (
            <KeyValue key={key} label={titleCase(key)} value={value} />
          ))}
        </Card>

        <Card title="Voice">
          <KeyValue label="Enabled" value={String(status?.voice?.enabled ?? false)} />
          <KeyValue label="State" value={status?.voice?.state ?? '—'} />
          <KeyValue label="Wake word" value={status?.voice?.wake_word ?? '—'} />
          <KeyValue label="STT" value={status?.voice?.stt_backend ?? '—'} />
          <KeyValue label="TTS" value={status?.voice?.tts_backend ?? '—'} />
        </Card>

        <Card title="Providers">
          {(status?.providers ?? []).map((provider) => (
            <KeyValue key={provider} label={provider} value="registered" />
          ))}
        </Card>
      </CardGrid>
    </div>
  );
}

export default SystemInfo;
