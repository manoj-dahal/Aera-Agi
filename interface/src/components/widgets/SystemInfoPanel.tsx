import { Cpu, Gauge, HardDrive, MemoryStick, Network, Thermometer, Zap } from 'lucide-react';
import type { SystemStatus, Telemetry } from '@services/types';
import { cn } from '@utils/cn';

export interface SystemInfoPanelProps {
  telemetry: Telemetry | null;
  status: SystemStatus | null;
  activeAgent?: string;
}

/**
 * PC Information panel (docs/04-DASHBOARD.md, left column).
 *
 * Live CPU, GPU, RAM, VRAM, disk, network and temperature, plus the active
 * model and agent count. A metric the host cannot report is shown as a dash
 * rather than a fabricated zero.
 */
export function SystemInfoPanel({ telemetry, status, activeAgent }: SystemInfoPanelProps) {
  const cpu = telemetry?.cpu;
  const memory = telemetry?.memory;
  const disk = telemetry?.disk;
  const network = telemetry?.network;
  const gpu = telemetry?.gpu?.[0];

  return (
    <div className="rounded-[10px] border border-[var(--aera-line-strong)] bg-[var(--aera-bg-surface)] p-2.5">
      <div className="mb-2 flex items-center gap-1.5">
        <Gauge size={11} className="text-[var(--aera-accent-primary)]" />
        <span className="text-[9.5px] uppercase tracking-[0.14em] text-[var(--aera-text-muted)]">
          System
        </span>
        {telemetry?.source && (
          <span className="ml-auto text-[8.5px] text-[var(--aera-text-disabled)]">
            {telemetry.source}
          </span>
        )}
      </div>

      <Meter
        Icon={Cpu}
        label="CPU"
        percent={cpu?.percent ?? null}
        detail={cpu?.threads ? `${cpu.threads}t` : undefined}
      />
      <Meter
        Icon={MemoryStick}
        label="RAM"
        percent={memory?.percent ?? null}
        detail={
          memory?.used_gb != null && memory?.total_gb != null
            ? `${memory.used_gb}/${memory.total_gb}G`
            : undefined
        }
      />
      {gpu && (
        <>
          <Meter Icon={Zap} label="GPU" percent={gpu.utilization} detail={gpu.name?.slice(0, 10)} />
          <Meter
            Icon={Zap}
            label="VRAM"
            percent={
              gpu.vram_total_mb && gpu.vram_used_mb
                ? (gpu.vram_used_mb / gpu.vram_total_mb) * 100
                : null
            }
            detail={
              gpu.vram_total_mb
                ? `${Math.round((gpu.vram_used_mb ?? 0) / 1024)}/${Math.round(gpu.vram_total_mb / 1024)}G`
                : undefined
            }
          />
        </>
      )}
      <Meter
        Icon={HardDrive}
        label="Disk"
        percent={disk?.percent ?? null}
        detail={disk?.free_gb != null ? `${disk.free_gb}G free` : undefined}
      />

      <div className="my-1.5 h-px bg-[var(--aera-line-default)]" />

      <Row
        Icon={Network}
        label="Net"
        value={
          network?.down_kbps != null
            ? `↓${fmtRate(network.down_kbps)} ↑${fmtRate(network.up_kbps ?? 0)}`
            : '—'
        }
      />
      <Row
        Icon={Thermometer}
        label="Temp"
        value={
          telemetry?.temperature != null
            ? `${telemetry.temperature}°C`
            : gpu?.temperature_c != null
              ? `${gpu.temperature_c}°C`
              : '—'
        }
      />
      <Row Icon={Cpu} label="Model" value={status?.providers?.[0] ?? '—'} />
      <Row
        Icon={Zap}
        label="Agents"
        value={status ? `${status.agents.running}/${status.agents.total}` : '—'}
      />
      <Row Icon={Gauge} label="Active" value={activeAgent ?? 'core'} />
    </div>
  );
}

/** Labelled bar with a colour that shifts as the metric approaches capacity. */
function Meter({
  Icon,
  label,
  percent,
  detail,
}: {
  Icon: typeof Cpu;
  label: string;
  percent: number | null | undefined;
  detail?: string;
}) {
  const value = percent == null ? null : Math.max(0, Math.min(100, percent));
  const colour =
    value == null
      ? 'var(--aera-text-disabled)'
      : value > 85
        ? 'var(--aera-danger)'
        : value > 65
          ? 'var(--aera-warning)'
          : 'var(--aera-accent-primary)';

  return (
    <div className="mb-1.5">
      <div className="flex items-center gap-1.5 text-[10px]">
        <Icon size={9} className="shrink-0 text-[var(--aera-text-muted)]" />
        <span className="text-[var(--aera-text-muted)]">{label}</span>
        {detail && (
          <span className="ml-auto truncate text-[9px] text-[var(--aera-text-disabled)]">
            {detail}
          </span>
        )}
        <span className={cn('tabular-nums', detail ? 'ml-1.5' : 'ml-auto')} style={{ color: colour }}>
          {value == null ? '—' : `${Math.round(value)}%`}
        </span>
      </div>
      <div className="mt-[3px] h-[3px] overflow-hidden rounded-full bg-[var(--aera-bg-overlay)]">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${value ?? 0}%`, background: colour }}
        />
      </div>
    </div>
  );
}

function Row({ Icon, label, value }: { Icon: typeof Cpu; label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5 py-[2px] text-[10px]">
      <Icon size={9} className="shrink-0 text-[var(--aera-text-muted)]" />
      <span className="text-[var(--aera-text-muted)]">{label}</span>
      <span className="ml-auto max-w-[95px] truncate text-right text-[var(--aera-text-secondary)]">
        {value}
      </span>
    </div>
  );
}

function fmtRate(kbps: number): string {
  if (kbps >= 1024) return `${(kbps / 1024).toFixed(1)}M`;
  return `${Math.round(kbps)}K`;
}
