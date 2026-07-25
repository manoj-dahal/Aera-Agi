import { Activity, Brain, FolderTree, Lightbulb, Loader2 } from 'lucide-react';
import type { ProjectSummary, SystemEvent, SystemStatus } from '@services/types';
import { timeAgo } from '@utils/format';

export interface AmbientPanelProps {
  status: SystemStatus | null;
  project: ProjectSummary | null;
  events: SystemEvent[];
  busy: boolean;
  /** Text describing what the tap-to-memory workflow recalled. */
  recall?: string | null;
  onSuggestion: (text: string) => void;
}

const SUGGESTIONS = [
  'Write a Python function to parse JSON safely',
  'Plan a migration from SQLite to PostgreSQL',
  'What do you remember about this project?',
];

/**
 * Ambient status panel shown beneath the AI Core while the conversation is
 * empty (docs/04-DASHBOARD.md: the centre should not sit blank).
 *
 * Surfaces running tasks, active agents, the current project, memory recall
 * progress and suggestions — then gets out of the way once a conversation
 * starts.
 */
export function AmbientPanel({
  status,
  project,
  events,
  busy,
  recall,
  onSuggestion,
}: AmbientPanelProps) {
  const running = events
    .filter((e) => e.topic === 'agent.task.started')
    .slice(0, 3);

  return (
    <div className="w-full max-w-[560px] animate-rise">
      {/* Memory recall progress, shown while the tap workflow runs. */}
      {(busy || recall) && (
        <div className="mb-2.5 flex items-center gap-2 rounded-lg border border-[var(--aera-line-default)] bg-[var(--aera-bg-surface)] px-3 py-2">
          {busy ? (
            <Loader2 size={12} className="animate-spin-slow text-[var(--aera-accent-primary)]" />
          ) : (
            <Brain size={12} className="text-[var(--aera-accent-primary)]" />
          )}
          <span className="text-[11.5px] text-[var(--aera-text-secondary)]">
            {recall ?? 'Recalling context…'}
          </span>
        </div>
      )}

      <div className="mb-3 grid grid-cols-3 gap-2">
        <Tile
          Icon={Activity}
          label="Tasks"
          value={running.length > 0 ? String(running.length) : 'idle'}
          hint={running.length > 0 ? String(running[0]?.payload.agent ?? '') : 'none running'}
        />
        <Tile
          Icon={Brain}
          label="Memory"
          value={String(status?.memory?.nodes ?? 0)}
          hint={`${status?.memory?.edges ?? 0} links`}
        />
        <Tile
          Icon={FolderTree}
          label="Project"
          value={project?.name ?? 'none'}
          hint={project ? `${project.files} files` : 'open a folder'}
        />
      </div>

      {events.length > 0 && (
        <div className="mb-3 flex flex-wrap justify-center gap-1.5">
          {events.slice(0, 4).map((event) => (
            <span
              key={event.id}
              className="rounded-full border border-[var(--aera-line-default)] bg-[var(--aera-bg-surface)] px-2.5 py-[3px] font-mono text-[9.5px] text-[var(--aera-text-muted)]"
            >
              {event.topic}
              <span className="ml-1.5 text-[var(--aera-text-disabled)]">
                {timeAgo(event.timestamp)}
              </span>
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-1.5">
        <Lightbulb size={11} className="shrink-0 text-[var(--aera-text-disabled)]" />
        <div className="flex flex-1 flex-wrap gap-1.5">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => onSuggestion(suggestion)}
              className="rounded-full border border-[var(--aera-line-default)] bg-[var(--aera-bg-surface)] px-3 py-[5px] text-[11px] text-[var(--aera-text-muted)] transition-colors hover:border-[var(--aera-accent-primary)] hover:text-[var(--aera-text-primary)]"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function Tile({
  Icon,
  label,
  value,
  hint,
}: {
  Icon: typeof Activity;
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--aera-line-default)] bg-[var(--aera-bg-surface)] px-3 py-2">
      <div className="flex items-center gap-1.5 text-[9.5px] uppercase tracking-[0.1em] text-[var(--aera-text-muted)]">
        <Icon size={9} />
        {label}
      </div>
      <div className="mt-0.5 truncate text-[13px] font-medium" title={value}>
        {value}
      </div>
      <div className="truncate text-[9.5px] text-[var(--aera-text-disabled)]">{hint}</div>
    </div>
  );
}
