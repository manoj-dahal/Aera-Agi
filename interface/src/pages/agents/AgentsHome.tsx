import { useEffect } from 'react';
import {
  Button,
  Card,
  CardGrid,
  KeyValue,
  ErrorState,
  LoadingState,
  PageHeader,
  StatCard,
  StatRow,
  StatusPill,
  Tag,
} from '@components/index';
import { useAgentStore } from '@store/index';
import { formatDuration, formatUptime } from '@utils/format';

/** Agent roster with live status and lifecycle control (docs/07-AGENTS.md). */
export function AgentsHome() {
  const { agents, summary, loading, error, load, start, stop, restart } = useAgentStore();

  useEffect(() => void load(), [load]);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Agents"
        subtitle="Specialists coordinated by the Core Agent through shared memory"
        action={
          <Button variant="ghost" onClick={() => void load()}>
            Refresh
          </Button>
        }
      />

      <StatRow>
        <StatCard label="Total" value={summary?.total ?? 0} />
        <StatCard
          label="Running"
          value={summary?.running ?? 0}
          accent="var(--aera-success)"
        />
        <StatCard label="Completed" value={summary?.tasks_completed ?? 0} />
        <StatCard
          label="Failed"
          value={summary?.tasks_failed ?? 0}
          accent={summary?.tasks_failed ? 'var(--aera-danger)' : undefined}
        />
        <StatCard label="Capabilities" value={summary?.capabilities ?? 0} />
      </StatRow>

      <CardGrid>
        {error && <ErrorState message={error} onRetry={() => void load()} />}
        {loading && !error && agents.length === 0 && <LoadingState />}
        {agents.map((agent) => (
          <Card key={agent.name}>
            <div className="mb-1 flex items-center justify-between gap-2">
              <h4 className="text-[13px] font-semibold">{agent.name}</h4>
              <StatusPill status={agent.status} />
            </div>
            <p className="mb-2 text-[12px] leading-snug text-[var(--aera-text-muted)]">
              {agent.description}
            </p>

            <KeyValue label="Completed" value={agent.tasks_completed} />
            <KeyValue label="Failed" value={agent.tasks_failed} />
            <KeyValue label="Average" value={formatDuration(agent.avg_duration_ms)} />
            <KeyValue label="Uptime" value={formatUptime(agent.uptime_seconds)} />
            {agent.last_error && (
              <p className="mt-1.5 text-[11px] text-[var(--aera-danger)]">
                {agent.last_error}
              </p>
            )}

            <div className="mt-2 flex flex-wrap gap-1">
              {agent.capabilities.map((capability) => (
                <Tag key={capability}>{capability}</Tag>
              ))}
            </div>

            <div className="mt-3 flex gap-1.5">
              {agent.status === 'stopped' ? (
                <Button size="sm" variant="primary" onClick={() => void start(agent.name)}>
                  Start
                </Button>
              ) : (
                <Button size="sm" variant="ghost" onClick={() => void stop(agent.name)}>
                  Stop
                </Button>
              )}
              <Button size="sm" variant="subtle" onClick={() => void restart(agent.name)}>
                Restart
              </Button>
            </div>
          </Card>
        ))}
      </CardGrid>
    </div>
  );
}

export default AgentsHome;
