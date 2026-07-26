/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { AlertTriangle, TerminalSquare } from 'lucide-react';
import { Button, Card, PageHeader, StatusPill, Tag } from '@components/index';
import { agents as agentsApi, system } from '@services/api';
import { useAgentStore } from '@store/index';
import { cn } from '@utils/cn';

interface Line {
  id: number;
  kind: 'command' | 'output' | 'error' | 'notice';
  text: string;
}

/**
 * Terminal (docs/15-TERMINAL.md).
 *
 * Drives the Terminal Agent, which enforces an allowlist server-side. The agent
 * is disabled by default; when it is off this page says so instead of offering
 * a prompt that cannot work.
 */
export function TerminalHome() {
  const { agents, load } = useAgentStore();
  const [lines, setLines] = useState<Line[]>([]);
  const [command, setCommand] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [running, setRunning] = useState(false);
  const [allowlist, setAllowlist] = useState<string[]>([]);
  const endRef = useRef<HTMLDivElement>(null);
  const counter = useRef(0);

  const enabled = agents.some((a) => a.name === 'terminal');

  useEffect(() => void load(), [load]);

  useEffect(() => {
    void system
      .settings()
      .then((s) => {
        const security = (s as { security?: { terminal_allowlist?: string[] } }).security;
        if (security?.terminal_allowlist) setAllowlist(security.terminal_allowlist);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' });
  }, [lines]);

  const push = (kind: Line['kind'], text: string) => {
    counter.current += 1;
    setLines((prev) => [...prev, { id: counter.current, kind, text }]);
  };

  const execute = async () => {
    const trimmed = command.trim();
    if (!trimmed || running) return;

    setCommand('');
    setHistory((prev) => [...prev, trimmed]);
    setHistoryIndex(-1);
    push('command', trimmed);

    if (trimmed === 'clear') {
      setLines([]);
      return;
    }

    setRunning(true);
    try {
      const result = await agentsApi.runTask({
        agent: 'terminal',
        capability: 'terminal',
        input: trimmed,
        context: { command: trimmed },
      });
      const stdout = (result.data as { stdout?: string; stderr?: string }).stdout;
      const stderr = (result.data as { stderr?: string }).stderr;
      if (stdout) push('output', stdout.trimEnd());
      if (stderr) push('error', stderr.trimEnd());
      if (!stdout && !stderr) push('output', result.output || '(no output)');
      if (!result.success && result.error) push('error', result.error);
    } catch (error) {
      push('error', error instanceof Error ? error.message : 'execution failed');
    } finally {
      setRunning(false);
    }
  };

  /** Up/down arrows walk the command history, like a real shell. */
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') return void execute();
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      const next = historyIndex < 0 ? history.length - 1 : Math.max(0, historyIndex - 1);
      if (history[next] !== undefined) {
        setHistoryIndex(next);
        setCommand(history[next]!);
      }
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (historyIndex < 0) return;
      const next = historyIndex + 1;
      if (next >= history.length) {
        setHistoryIndex(-1);
        setCommand('');
      } else {
        setHistoryIndex(next);
        setCommand(history[next]!);
      }
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col p-4">
      <PageHeader
        title="Terminal"
        subtitle="Allowlisted shell execution through the Terminal Agent"
        action={
          <div className="flex items-center gap-2">
            <StatusPill status={enabled ? 'running' : 'stopped'}
              label={enabled ? 'agent active' : 'agent disabled'} />
            <Button variant="ghost" size="sm" onClick={() => setLines([])}>
              Clear
            </Button>
          </div>
        }
      />

      {!enabled && (
        <Card className="mb-3 max-w-3xl border-[var(--aera-warning)]">
          <div className="flex gap-2.5">
            <AlertTriangle size={16} className="mt-0.5 shrink-0 text-[var(--aera-warning)]" />
            <div>
              <h4 className="mb-1 text-[13px] font-semibold">Terminal execution is disabled</h4>
              <p className="text-[11.5px] leading-relaxed text-[var(--aera-text-muted)]">
                Running shell commands is off by default. Set{' '}
                <code className="rounded bg-[var(--aera-bg-overlay)] px-1">agents.terminal: true</code>{' '}
                in <code className="rounded bg-[var(--aera-bg-overlay)] px-1">config/agents.yaml</code>{' '}
                and{' '}
                <code className="rounded bg-[var(--aera-bg-overlay)] px-1">
                  security.allow_terminal: true
                </code>{' '}
                in <code className="rounded bg-[var(--aera-bg-overlay)] px-1">config/security.yaml</code>,
                then restart AERA. Only allowlisted binaries will run.
              </p>
            </div>
          </div>
        </Card>
      )}

      {allowlist.length > 0 && (
        <div className="mb-2 flex flex-wrap items-center gap-1.5">
          <span className="text-[10.5px] uppercase tracking-[0.1em] text-[var(--aera-text-muted)]">
            Allowlist
          </span>
          {allowlist.map((binary) => (
            <Tag key={binary}>{binary}</Tag>
          ))}
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[10px] border border-[var(--aera-line-strong)] bg-[#05070c]">
        <div className="flex-1 overflow-y-auto p-3.5 font-mono text-[11.5px] leading-relaxed">
          {lines.length === 0 && (
            <p className="text-[var(--aera-text-disabled)]">
              {enabled
                ? 'Type an allowlisted command and press Enter. Use the arrow keys for history.'
                : 'Enable the Terminal Agent to run commands.'}
            </p>
          )}
          {lines.map((line) => (
            <div
              key={line.id}
              className={cn(
                'selectable whitespace-pre-wrap break-words',
                line.kind === 'command' && 'text-[var(--aera-accent-primary)]',
                line.kind === 'error' && 'text-[var(--aera-danger)]',
                line.kind === 'notice' && 'text-[var(--aera-warning)]',
                line.kind === 'output' && 'text-[var(--aera-text-secondary)]',
              )}
            >
              {line.kind === 'command' ? `$ ${line.text}` : line.text}
            </div>
          ))}
          {running && <div className="animate-pulse-slow text-[var(--aera-text-muted)]">…</div>}
          <div ref={endRef} />
        </div>

        <div className="flex items-center gap-2 border-t border-[var(--aera-line-default)] px-3.5 py-2">
          <TerminalSquare size={13} className="shrink-0 text-[var(--aera-accent-primary)]" />
          <input
            value={command}
            disabled={!enabled || running}
            placeholder={enabled ? 'command…' : 'terminal agent disabled'}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={onKeyDown}
            className="selectable flex-1 bg-transparent font-mono text-[11.5px] outline-none placeholder:text-[var(--aera-text-disabled)] disabled:opacity-50"
          />
          <Button
            size="sm"
            variant="primary"
            disabled={!enabled || running || !command.trim()}
            onClick={() => void execute()}
          >
            Run
          </Button>
        </div>
      </div>

      <p className="mt-2 text-[10.5px] text-[var(--aera-text-disabled)]">
        Commands are validated against the allowlist inside the agent, so the restriction
        holds even if this page is bypassed. There is no interactive PTY: each command runs
        once and returns its output.
      </p>
    </div>
  );
}

export default TerminalHome;
