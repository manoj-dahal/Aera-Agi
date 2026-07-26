/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import { useEffect, useState } from 'react';
import {
  Button, Card, CardGrid, EmptyState, KeyValue, PageHeader,
  StatusPill, Tag, useToast,
} from '@components/index';
import { automation } from '@services/api';
import { formatDuration, timeAgo } from '@utils/format';
import type { WorkflowInfo, WorkflowRun } from '@services/types';

/** Workflow registry and run history (docs/20-AUTOMATION.md). */
export function AutomationHome() {
  const [workflows, setWorkflows] = useState<WorkflowInfo[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const showToast = useToast((s) => s.show);

  const load = async () => {
    const [list, history] = await Promise.all([
      automation.list().catch(() => ({ workflows: [], count: 0 })),
      automation.runs().catch(() => ({ runs: [] })),
    ]);
    setWorkflows(list.workflows);
    setRuns(history.runs.slice().reverse());
  };

  useEffect(() => void load(), []);

  const run = async (workflow: WorkflowInfo) => {
    setBusy(workflow.id);
    try {
      const result = await automation.run(workflow.id);
      showToast(`${workflow.name}: ${result.status}`, result.status === 'success' ? 'success' : 'error');
      void load();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'run failed', 'error');
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Automation"
        subtitle="Event, schedule and manually triggered workflows"
        action={<Button variant="ghost" onClick={() => void load()}>Refresh</Button>}
      />

      <CardGrid>
        {workflows.length === 0 ? (
          <EmptyState
            title="No workflows"
            message="Register workflows through the automation API to run multi-step jobs across agents, memory and models."
          />
        ) : (
          workflows.map((workflow) => (
            <Card key={workflow.id}>
              <div className="mb-1 flex items-center justify-between gap-2">
                <h4 className="text-[13px] font-semibold">{workflow.name}</h4>
                <StatusPill status={workflow.enabled ? 'running' : 'idle'}
                  label={workflow.enabled ? 'enabled' : 'disabled'} />
              </div>
              <p className="mb-2 text-[12px] text-[var(--aera-text-muted)]">
                {workflow.description || 'No description'}
              </p>
              <KeyValue label="Actions" value={workflow.actions} />
              <div className="mt-2 flex flex-wrap gap-1">
                {workflow.triggers.map((trigger) => (
                  <Tag key={trigger}>{trigger}</Tag>
                ))}
              </div>
              <Button
                size="sm"
                variant="primary"
                className="mt-3"
                loading={busy === workflow.id}
                disabled={!workflow.enabled}
                onClick={() => void run(workflow)}
              >
                Run
              </Button>
            </Card>
          ))
        )}
      </CardGrid>

      <h3 className="mb-2 mt-6 text-[10.5px] uppercase tracking-[0.11em] text-[var(--aera-text-muted)]">
        Recent runs
      </h3>
      <CardGrid>
        {runs.length === 0 ? (
          <p className="text-[12.5px] text-[var(--aera-text-muted)]">No runs yet.</p>
        ) : (
          runs.map((run) => (
            <Card key={run.id}>
              <div className="mb-1 flex items-center justify-between gap-2">
                <h4 className="text-[13px] font-semibold">{run.workflow_name}</h4>
                <StatusPill status={run.status} />
              </div>
              <KeyValue label="Steps" value={run.steps.length} />
              <KeyValue label="Duration" value={formatDuration(run.duration_ms)} />
              <KeyValue label="Started" value={timeAgo(run.started_at)} />
              {run.error && (
                <p className="mt-1.5 text-[11px] text-[var(--aera-danger)]">{run.error}</p>
              )}
            </Card>
          ))
        )}
      </CardGrid>
    </div>
  );
}

export default AutomationHome;
