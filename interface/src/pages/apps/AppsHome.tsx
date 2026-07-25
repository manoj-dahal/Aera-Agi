import { useEffect, useRef, useState } from 'react';
import {
  Blocks,
  Boxes,
  Code2,
  GitBranch,
  MoreVertical,
  Plus,
  RefreshCw,
  TerminalSquare,
} from 'lucide-react';
import { Button, Card, Input, PageHeader, StatusPill, Tag, useToast } from '@components/index';
import { agents as agentsApi } from '@services/api';
import { detectHost } from '@services/transport';
import { useAgentStore } from '@store/index';
import { cn } from '@utils/cn';

type Category = 'default' | 'development' | 'creative' | 'custom' | 'plugins';

interface AppEntry {
  id: string;
  name: string;
  description: string;
  category: Category;
  /** Backed by a real agent, so it can genuinely be driven. */
  agent?: string;
  /** Present in this build vs. requiring a connector. */
  connected: boolean;
  autoUpdate?: boolean;
  Icon: typeof Code2;
}

/**
 * Apps: the application and skills hub (docs/10-APPS.md, docs/ui-page/conversation.txt).
 *
 * Terminal and Git ship as default tools. Other software is added through
 * "Connect Application". Each entry has a three-dot menu carrying the update
 * actions. AI skills deliberately do not appear here — they live in Macros.
 */
export function AppsHome() {
  const { agents, load } = useAgentStore();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<Category | 'all'>('all');
  const [custom, setCustom] = useState<AppEntry[]>([]);
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const showToast = useToast((s) => s.show);
  const isDesktop = detectHost() === 'desktop';

  useEffect(() => void load(), [load]);

  const hasAgent = (name: string) => agents.some((a) => a.name === name);

  const builtIn: AppEntry[] = [
    {
      id: 'terminal',
      name: 'Terminal',
      description: 'Allowlisted shell execution through the Terminal Agent.',
      category: 'default',
      agent: 'terminal',
      connected: hasAgent('terminal'),
      autoUpdate: false,
      Icon: TerminalSquare,
    },
    {
      id: 'git',
      name: 'Git',
      description: 'Repository analysis, commit assistance and history review.',
      category: 'default',
      agent: 'git',
      connected: hasAgent('git'),
      autoUpdate: true,
      Icon: GitBranch,
    },
    {
      id: 'vscode',
      name: 'VS Code',
      description: 'Editor integration. Requires a connector.',
      category: 'development',
      connected: false,
      Icon: Code2,
    },
    {
      id: 'docker',
      name: 'Docker',
      description: 'Container management. Requires a connector.',
      category: 'development',
      connected: false,
      Icon: Boxes,
    },
    {
      id: 'blender',
      name: 'Blender',
      description: '3D modelling and rendering. Requires a connector.',
      category: 'creative',
      connected: false,
      Icon: Blocks,
    },
    {
      id: 'plugins',
      name: 'Plugin Manager',
      description:
        'Sandboxed extensions that register agents, tools and UI. Managed here, not in Settings.',
      category: 'plugins',
      connected: false,
      Icon: Blocks,
    },
  ];

  const all = [...builtIn, ...custom];
  const visible = all.filter((app) => {
    if (category !== 'all' && app.category !== category) return false;
    if (!query.trim()) return true;
    const needle = query.toLowerCase();
    return app.name.toLowerCase().includes(needle) || app.description.toLowerCase().includes(needle);
  });

  /** Connect an executable from disk (desktop only — needs a native dialog). */
  const connectApplication = async () => {
    if (!isDesktop) {
      return showToast('Connecting applications requires the desktop app', 'error');
    }
    try {
      const picked = await pickExecutable();
      if (!picked) return;
      const name = picked.split(/[\\/]/).pop() ?? picked;
      setCustom((prev) => [
        ...prev,
        {
          id: `custom-${Date.now()}`,
          name,
          description: picked,
          category: 'custom',
          connected: true,
          autoUpdate: false,
          Icon: Blocks,
        },
      ]);
      showToast(`Connected ${name}`, 'success');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'could not connect', 'error');
    }
  };

  const launch = async (app: AppEntry) => {
    if (!app.agent) {
      return showToast(`${app.name} has no connector in this build`, 'error');
    }
    try {
      const result = await agentsApi.runTask({
        agent: app.agent,
        capability: app.agent === 'git' ? 'git' : 'terminal',
        input: app.agent === 'git' ? 'Summarise the repository status' : 'echo AERA',
      });
      showToast(result.success ? `${app.name} responded` : (result.error ?? 'failed'),
        result.success ? 'success' : 'error');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'launch failed', 'error');
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Apps"
        subtitle="Connect software, manage updates and drive tools through agents"
        action={
          <div className="flex gap-2">
            <Button variant="ghost" icon={<RefreshCw size={13} />} onClick={() => void load()}>
              Rescan
            </Button>
            <Button variant="primary" icon={<Plus size={14} />} onClick={() => void connectApplication()}>
              Connect Application
            </Button>
          </div>
        }
      />

      <div className="mb-3 flex flex-wrap gap-2">
        <Input
          value={query}
          placeholder="Search applications…"
          onChange={(e) => setQuery(e.target.value)}
          className="max-w-xs"
        />
        {(['all', 'default', 'development', 'creative', 'custom', 'plugins'] as const).map((c) => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={cn(
              'rounded-md border px-2.5 py-1 text-[11.5px] capitalize transition-colors',
              category === c
                ? 'border-[var(--aera-accent-primary)] text-[var(--aera-accent-primary)]'
                : 'border-[var(--aera-line-default)] text-[var(--aera-text-muted)] hover:text-[var(--aera-text-primary)]',
            )}
          >
            {c}
          </button>
        ))}
      </div>

      <div className="grid content-start gap-2 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
        {visible.map((app) => (
          <Card key={app.id} className="relative">
            <div className="mb-1.5 flex items-start gap-2.5">
              <app.Icon
                size={17}
                strokeWidth={1.7}
                className={
                  app.connected
                    ? 'text-[var(--aera-accent-primary)]'
                    : 'text-[var(--aera-text-disabled)]'
                }
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="truncate text-[13px] font-semibold">{app.name}</h4>
                  <StatusPill
                    status={app.connected ? 'running' : 'idle'}
                    label={app.connected ? 'connected' : 'not connected'}
                  />
                </div>
              </div>
              <AppMenu
                open={menuFor === app.id}
                autoUpdate={app.autoUpdate}
                onToggle={() => setMenuFor(menuFor === app.id ? null : app.id)}
                onAction={(action) => {
                  setMenuFor(null);
                  showToast(`${action} — ${app.name}`, 'info');
                }}
              />
            </div>

            <p className="mb-2.5 text-[11.5px] leading-snug text-[var(--aera-text-muted)]">
              {app.description}
            </p>

            <div className="flex items-center gap-1.5">
              {app.category === 'default' && <Tag>default</Tag>}
              {app.autoUpdate && <Tag>auto-update</Tag>}
              <div className="ml-auto flex gap-1.5">
                <Button
                  size="sm"
                  variant={app.connected ? 'primary' : 'ghost'}
                  disabled={!app.connected}
                  onClick={() => void launch(app)}
                >
                  {app.connected ? 'Launch' : 'Connect'}
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <p className="mt-4 max-w-2xl text-[11px] leading-relaxed text-[var(--aera-text-disabled)]">
        Terminal and Git are driven by real agents. Other entries are connector
        placeholders: connecting them registers the application, but AERA cannot control
        it until a connector ships. AI skills and memory intentionally do not appear
        here — they run in the background and are visualised in Macros.
      </p>
    </div>
  );
}

/** Three-dot menu carrying the update actions from the conversation. */
function AppMenu({
  open,
  autoUpdate,
  onToggle,
  onAction,
}: {
  open: boolean;
  autoUpdate?: boolean;
  onToggle: () => void;
  onAction: (action: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const away = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) onToggle();
    };
    document.addEventListener('mousedown', away);
    return () => document.removeEventListener('mousedown', away);
  }, [open, onToggle]);

  const actions = [
    'Open',
    'Check for Updates',
    'Update Now',
    'Update All',
    autoUpdate ? 'Auto Update: On' : 'Auto Update: Off',
    'Rescan',
    'Disconnect',
  ];

  return (
    <div ref={ref} className="relative">
      <button
        onClick={onToggle}
        aria-label="Application menu"
        className="rounded p-1 text-[var(--aera-text-muted)] hover:bg-[var(--aera-bg-hover)] hover:text-[var(--aera-text-primary)]"
      >
        <MoreVertical size={14} />
      </button>
      {open && (
        <div className="absolute right-0 top-7 z-30 w-44 overflow-hidden rounded-lg border border-[var(--aera-line-strong)] bg-[var(--aera-bg-overlay)] py-1 shadow-xl">
          {actions.map((action) => (
            <button
              key={action}
              onClick={() => onAction(action)}
              className={cn(
                'block w-full px-3 py-1.5 text-left text-[11.5px] hover:bg-[var(--aera-bg-hover)]',
                action === 'Disconnect' && 'text-[var(--aera-danger)]',
              )}
            >
              {action}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** Native executable picker; resolves to null when cancelled. */
async function pickExecutable(): Promise<string | null> {
  const bridge = (window as unknown as {
    pywebview?: { api: { open_file_dialog: (m?: boolean) => Promise<{ success: boolean; data?: string[] }> } };
  }).pywebview;
  if (!bridge) return null;
  const result = await bridge.api.open_file_dialog(false);
  return result?.data?.[0] ?? null;
}

export default AppsHome;
