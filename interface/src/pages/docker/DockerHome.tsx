/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import { useCallback, useEffect, useState } from 'react';
import { Boxes, Container, HardDrive, Network, RotateCw, Square, Play } from 'lucide-react';
import {
  Button,
  Card,
  EmptyState,
  KeyValue,
  PageHeader,
  StatusPill,
} from '@components/index';
import { docker as dockerApi } from '@services/api';
import type {
  DockerContainer,
  DockerImage,
  DockerInfo,
  DockerNetwork,
  DockerStatus,
  DockerVolume,
} from '@services/types';

/**
 * Docker (docs/27-DOCKER.md).
 *
 * Talks to the Engine API over its Unix socket. Reads are always allowed;
 * start/stop/restart return 403 unless `security.allow_docker_control` is
 * enabled, so the controls are shown disabled rather than hidden — hiding
 * them would leave no clue that the capability exists.
 */

type Tab = 'containers' | 'images' | 'volumes' | 'networks';

const TABS: { id: Tab; label: string; Icon: typeof Container }[] = [
  { id: 'containers', label: 'Containers', Icon: Container },
  { id: 'images', label: 'Images', Icon: Boxes },
  { id: 'volumes', label: 'Volumes', Icon: HardDrive },
  { id: 'networks', label: 'Networks', Icon: Network },
];

/** Docker reports bytes; the CLI shows human units. */
function formatBytes(bytes: number | null): string {
  if (bytes === null || Number.isNaN(bytes)) return '—';
  const units = ['B', 'kB', 'MB', 'GB', 'TB'];
  let value = bytes;
  let unit = 0;
  while (value >= 1000 && unit < units.length - 1) {
    value /= 1000;
    unit += 1;
  }
  return `${value.toFixed(value < 10 && unit > 0 ? 1 : 0)} ${units[unit]}`;
}

function stateStatus(state: string): 'running' | 'error' | 'idle' | 'stopped' {
  if (state === 'running') return 'running';
  if (state === 'exited' || state === 'dead') return 'error';
  if (state === 'paused') return 'idle';
  return 'stopped';
}

export function DockerHome() {
  const [status, setStatus] = useState<DockerStatus | null>(null);
  const [info, setInfo] = useState<DockerInfo | null>(null);
  const [containers, setContainers] = useState<DockerContainer[]>([]);
  const [images, setImages] = useState<DockerImage[]>([]);
  const [volumes, setVolumes] = useState<DockerVolume[]>([]);
  const [networks, setNetworks] = useState<DockerNetwork[]>([]);
  const [tab, setTab] = useState<Tab>('containers');
  const [logs, setLogs] = useState<{ name: string; text: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const current = await dockerApi.status();
      setStatus(current);
      if (!current.available) return;

      // Fetched together so a slow daemon does not stagger the page.
      const [i, c, im, v, n] = await Promise.all([
        dockerApi.info(),
        dockerApi.containers(true),
        dockerApi.images(),
        dockerApi.volumes(),
        dockerApi.networks(),
      ]);
      setInfo(i);
      setContainers(c.containers);
      setImages(im.images);
      setVolumes(v.volumes);
      setNetworks(n.networks);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'could not reach Docker');
    }
  }, []);

  useEffect(() => void load(), [load]);

  const act = async (
    action: 'start' | 'stop' | 'restart',
    name: string,
  ) => {
    setBusy(`${action}:${name}`);
    setError(null);
    try {
      await dockerApi[action](name);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `${action} failed`);
    } finally {
      setBusy(null);
    }
  };

  const showLogs = async (name: string) => {
    setBusy(`logs:${name}`);
    try {
      const { logs: text } = await dockerApi.logs(name, 200);
      setLogs({ name, text: text || '(no output)' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'could not read logs');
    } finally {
      setBusy(null);
    }
  };

  // Docker absent: say why, and stop. Rendering empty tables would imply
  // there is simply nothing running, which is a different thing entirely.
  if (status && !status.available) {
    return (
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
        <PageHeader title="Docker" subtitle="Container management" />
        <Card title="Not connected" className="max-w-2xl">
          <KeyValue
            label="Docker Engine"
            value={<StatusPill status="stopped" label="unavailable" />}
          />
          <p className="mt-2 text-[11.5px] leading-relaxed text-[var(--aera-text-muted)]">
            {status.reason}
          </p>
          <p className="mt-2 text-[11.5px] leading-relaxed text-[var(--aera-text-muted)]">
            AERA talks to the Engine over its Unix socket, so the Docker CLI is not
            required — only a running daemon.
          </p>
          <div className="mt-3">
            <Button variant="secondary" onClick={() => void load()}>
              Check again
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  const counts: Record<Tab, number> = {
    containers: containers.length,
    images: images.length,
    volumes: volumes.length,
    networks: networks.length,
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Docker"
        subtitle={
          info?.version.version
            ? `Engine ${info.version.version} · API ${info.version.api_version}`
            : 'Container management'
        }
        action={
          <Button variant="secondary" onClick={() => void load()}>
            Refresh
          </Button>
        }
      />

      {error && (
        <Card className="mb-3 max-w-3xl border-[var(--aera-danger)]">
          <p className="text-[11.5px] text-[var(--aera-danger)]">{error}</p>
        </Card>
      )}

      {info && (
        <div className="mb-4 grid max-w-4xl gap-2 [grid-template-columns:repeat(auto-fill,minmax(190px,1fr))]">
          <Card>
            <KeyValue label="Host" value={info.info.name ?? '—'} />
            <KeyValue label="Driver" value={info.info.driver ?? '—'} />
          </Card>
          <Card>
            <KeyValue label="Running" value={String(info.info.containers_running ?? 0)} />
            <KeyValue label="Stopped" value={String(info.info.containers_stopped ?? 0)} />
          </Card>
          <Card>
            <KeyValue label="CPUs" value={String(info.info.cpus ?? '—')} />
            <KeyValue label="Memory" value={formatBytes(info.info.memory_total)} />
          </Card>
          <Card>
            <KeyValue
              label="Control"
              value={
                <StatusPill
                  status={status?.control_enabled ? 'running' : 'idle'}
                  label={status?.control_enabled ? 'enabled' : 'read-only'}
                />
              }
            />
            <KeyValue label="Platform" value={`${info.version.os ?? '?'}/${info.version.arch ?? '?'}`} />
          </Card>
        </div>
      )}

      <div className="mb-3 flex items-center gap-1.5">
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 rounded-[7px] border px-3 py-[6px] text-[12px] transition-colors ${
              tab === id
                ? 'border-[var(--aera-accent-primary)] text-[var(--aera-text-primary)]'
                : 'border-[var(--aera-line-default)] text-[var(--aera-text-muted)]'
            }`}
          >
            <Icon size={14} strokeWidth={1.7} />
            {label}
            <span className="text-[var(--aera-text-disabled)]">{counts[id]}</span>
          </button>
        ))}
      </div>

      {tab === 'containers' &&
        (containers.length === 0 ? (
          <EmptyState message="No containers on this host." />
        ) : (
          <div className="grid max-w-4xl gap-2">
            {containers.map((c) => (
              <Card key={c.id}>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill status={stateStatus(c.state)} label={c.state} />
                  <span className="text-[12.5px] font-semibold">{c.name || c.id}</span>
                  <span className="font-mono text-[10.5px] text-[var(--aera-text-disabled)]">
                    {c.id}
                  </span>
                  <span className="text-[11px] text-[var(--aera-text-muted)]">{c.image}</span>

                  <div className="ml-auto flex items-center gap-1.5">
                    <Button
                      variant="ghost"
                      loading={busy === `logs:${c.name}`}
                      onClick={() => void showLogs(c.name || c.id)}
                    >
                      Logs
                    </Button>
                    {c.state === 'running' ? (
                      <>
                        <Button
                          variant="ghost"
                          icon={<RotateCw size={13} />}
                          disabled={!status?.control_enabled}
                          loading={busy === `restart:${c.name}`}
                          onClick={() => void act('restart', c.name || c.id)}
                        >
                          Restart
                        </Button>
                        <Button
                          variant="ghost"
                          icon={<Square size={13} />}
                          disabled={!status?.control_enabled}
                          loading={busy === `stop:${c.name}`}
                          onClick={() => void act('stop', c.name || c.id)}
                        >
                          Stop
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="ghost"
                        icon={<Play size={13} />}
                        disabled={!status?.control_enabled}
                        loading={busy === `start:${c.name}`}
                        onClick={() => void act('start', c.name || c.id)}
                      >
                        Start
                      </Button>
                    )}
                  </div>
                </div>

                <div className="mt-1 flex flex-wrap gap-3 text-[11px] text-[var(--aera-text-muted)]">
                  <span>{c.status}</span>
                  {c.ports
                    .filter((p) => p.public)
                    .map((p) => (
                      <span key={`${p.private}-${p.public}`} className="font-mono">
                        {p.public}→{p.private}/{p.type}
                      </span>
                    ))}
                </div>
              </Card>
            ))}
          </div>
        ))}

      {tab === 'images' &&
        (images.length === 0 ? (
          <EmptyState message="No images on this host." />
        ) : (
          <div className="grid max-w-4xl gap-2">
            {images.map((image) => (
              <Card key={image.id}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[12.5px] font-semibold">
                    {/* Untagged images show as <none> in the CLI too. */}
                    {image.tags.length ? image.tags.join(', ') : '<none>'}
                  </span>
                  <span className="font-mono text-[10.5px] text-[var(--aera-text-disabled)]">
                    {image.id}
                  </span>
                  <span className="ml-auto text-[11px] text-[var(--aera-text-muted)]">
                    {formatBytes(image.size)}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        ))}

      {tab === 'volumes' &&
        (volumes.length === 0 ? (
          <EmptyState message="No volumes on this host." />
        ) : (
          <div className="grid max-w-4xl gap-2">
            {volumes.map((v) => (
              <Card key={v.name}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[12.5px] font-semibold">{v.name}</span>
                  <span className="text-[11px] text-[var(--aera-text-muted)]">{v.driver}</span>
                  <span className="ml-auto font-mono text-[10.5px] text-[var(--aera-text-disabled)]">
                    {v.mountpoint}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        ))}

      {tab === 'networks' &&
        (networks.length === 0 ? (
          <EmptyState message="No networks on this host." />
        ) : (
          <div className="grid max-w-4xl gap-2">
            {networks.map((n) => (
              <Card key={n.id}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[12.5px] font-semibold">{n.name}</span>
                  <span className="text-[11px] text-[var(--aera-text-muted)]">
                    {n.driver} · {n.scope}
                  </span>
                  <span className="ml-auto font-mono text-[10.5px] text-[var(--aera-text-disabled)]">
                    {n.id}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        ))}

      {logs && (
        <Card title={`Logs — ${logs.name}`} className="mt-4 max-w-4xl">
          <pre className="selectable max-h-80 overflow-auto whitespace-pre-wrap font-mono text-[11px] text-[var(--aera-text-secondary)]">
            {logs.text}
          </pre>
          <div className="mt-2">
            <Button variant="ghost" onClick={() => setLogs(null)}>
              Close
            </Button>
          </div>
        </Card>
      )}

      {status && !status.control_enabled && (
        <p className="mt-4 max-w-3xl text-[11px] leading-relaxed text-[var(--aera-text-muted)]">
          Container controls are read-only. Set{' '}
          <code>security.allow_docker_control</code> to enable start, stop and restart —
          it is off by default so AERA cannot change container state unasked.
        </p>
      )}
    </div>
  );
}

export default DockerHome;
