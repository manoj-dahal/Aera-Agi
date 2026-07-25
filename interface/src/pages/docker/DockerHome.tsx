import { useEffect, useState } from 'react';
import { Boxes, Container, HardDrive, Network } from 'lucide-react';
import { Button, Card, EmptyState, KeyValue, PageHeader, StatusPill } from '@components/index';
import { agents as agentsApi } from '@services/api';
import { useAgentStore } from '@store/index';

/**
 * Docker (docs/27-DOCKER.md).
 *
 * AERA ships a Dockerfile and Compose stack, so the platform runs containerised
 * today. Inspecting other containers needs a Docker connector, which the
 * Terminal Agent can stand in for when it is enabled.
 */
export function DockerHome() {
  const { agents, load } = useAgentStore();
  const [output, setOutput] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const terminalReady = agents.some((a) => a.name === 'terminal');

  useEffect(() => void load(), [load]);

  const probe = async () => {
    setBusy(true);
    try {
      const result = await agentsApi.runTask({
        agent: 'terminal',
        capability: 'terminal',
        input: 'docker ps',
        context: { command: 'docker ps' },
      });
      setOutput(result.output || result.error || '(no output)');
    } catch (error) {
      setOutput(error instanceof Error ? error.message : 'probe failed');
    } finally {
      setBusy(false);
    }
  };

  const sections = [
    { Icon: Container, label: 'Containers', hint: 'List, start, stop and inspect logs' },
    { Icon: Boxes, label: 'Images', hint: 'Pull, build and prune images' },
    { Icon: HardDrive, label: 'Volumes', hint: 'Inspect and clean up volumes' },
    { Icon: Network, label: 'Networks', hint: 'Inspect container networking' },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Docker"
        subtitle="Container management"
        action={
          <Button
            variant="primary"
            loading={busy}
            disabled={!terminalReady}
            onClick={() => void probe()}
          >
            Probe with Terminal Agent
          </Button>
        }
      />

      <Card title="Status" className="mb-4 max-w-2xl">
        <KeyValue
          label="Docker connector"
          value={<StatusPill status="idle" label="not implemented" />}
        />
        <KeyValue
          label="Terminal fallback"
          value={<StatusPill status={terminalReady ? 'running' : 'stopped'}
            label={terminalReady ? 'available' : 'agent disabled'} />}
        />
        <p className="mt-2 text-[11.5px] leading-relaxed text-[var(--aera-text-muted)]">
          AERA itself ships a Dockerfile and a Compose stack. There is no dedicated Docker
          API client yet, but if the Terminal Agent is enabled and <code>docker</code> is on
          its allowlist, you can query the daemon through it.
        </p>
      </Card>

      {output !== null && (
        <Card title="docker ps" className="mb-4 max-w-3xl">
          <pre className="selectable overflow-x-auto whitespace-pre-wrap font-mono text-[11px] text-[var(--aera-text-secondary)]">
            {output}
          </pre>
        </Card>
      )}

      <h3 className="mb-2 text-[10.5px] uppercase tracking-[0.11em] text-[var(--aera-text-muted)]">
        Planned sections
      </h3>
      <div className="grid max-w-3xl gap-2 [grid-template-columns:repeat(auto-fill,minmax(240px,1fr))]">
        {sections.map(({ Icon, label, hint }) => (
          <Card key={label}>
            <div className="flex items-start gap-2.5">
              <Icon size={16} strokeWidth={1.7} className="text-[var(--aera-text-disabled)]" />
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-[12.5px] font-semibold">{label}</h4>
                  <StatusPill status="idle" label="planned" />
                </div>
                <p className="mt-0.5 text-[11px] text-[var(--aera-text-muted)]">{hint}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {!terminalReady && (
        <EmptyState
          message="Enable the Terminal Agent to query the Docker daemon in the meantime."
        />
      )}
    </div>
  );
}

export default DockerHome;
