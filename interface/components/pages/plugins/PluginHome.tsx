/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import { useEffect, useState } from 'react';
import { Blocks, ShieldCheck } from 'lucide-react';
import {
  Button, Card, ErrorState, KeyValue, LoadingState, PageHeader, StatCard, StatRow,
  StatusPill, Tag,
} from '@components/index';
import { useAgentStore } from '@store/index';

/**
 * Plugins (docs/17-PLUGIN-SYSTEM.md).
 *
 * Per the requirements, plugin management belongs to Apps rather than Settings.
 * This page shows the extension surface that exists today: every agent is a
 * registered capability provider, which is what plugins will hook into.
 */
export function PluginHome() {
  const { agents, capabilities, loading, error, load } = useAgentStore();
  const [showBuiltIn, setShowBuiltIn] = useState(true);

  useEffect(() => void load(), [load]);

  const capabilityCount = Object.keys(capabilities).length;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Plugins"
        subtitle="Sandboxed extensions. Managed here and in Apps, never in Settings."
        action={
          <Button variant="ghost" onClick={() => setShowBuiltIn((v) => !v)}>
            {showBuiltIn ? 'Hide built-ins' : 'Show built-ins'}
          </Button>
        }
      />

      {error && <ErrorState message={error} onRetry={() => void load()} />}
      {loading && !error && agents.length === 0 && <LoadingState />}

      <StatRow>
        <StatCard label="Installed" value={0} />
        <StatCard label="Built-in providers" value={agents.length} />
        <StatCard label="Capabilities" value={capabilityCount} />
      </StatRow>

      <Card title="Extension model" className="mb-4 max-w-2xl">
        <p className="mb-2 text-[12px] leading-relaxed text-[var(--aera-text-muted)]">
          A plugin registers one or more agents against existing capabilities. The registry
          already supports runtime registration and capability routing, which is the hook
          plugins will use. Manifest loading, permission prompts and sandbox enforcement
          are not built yet, so no third-party plugin can be installed today.
        </p>
        <div className="flex items-center gap-2 text-[11.5px] text-[var(--aera-text-secondary)]">
          <ShieldCheck size={13} className="text-[var(--aera-success)]" />
          Permission primitives and the audit log already exist in the security layer.
        </div>
      </Card>

      {showBuiltIn && (
        <>
          <h3 className="mb-2 text-[10.5px] uppercase tracking-[0.11em] text-[var(--aera-text-muted)]">
            Registered capability providers
          </h3>
          <div className="grid content-start gap-2 [grid-template-columns:repeat(auto-fill,minmax(260px,1fr))]">
            {agents.map((agent) => (
              <Card key={agent.name}>
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2">
                    <Blocks size={14} className="text-[var(--aera-accent-primary)]" />
                    <h4 className="text-[12.5px] font-semibold">{agent.name}</h4>
                  </span>
                  <StatusPill status={agent.status} />
                </div>
                <KeyValue label="Priority" value={agent.priority} />
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {agent.capabilities.map((c) => (
                    <Tag key={c}>{c}</Tag>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default PluginHome;
