/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import { useEffect, useRef, useState } from 'react';
import {
  ChevronRight, Folder, FolderOpen, FolderPlus, MoreVertical,
  RefreshCw, Search,
} from 'lucide-react';
import { cn } from '@utils/cn';
import type { FileMatch, ProjectSummary } from '@services/types';

export interface WorkspacePanelProps {
  project: ProjectSummary | null;
  files: string[];
  results: FileMatch[];
  canPickFolder: boolean;
  onOpenFolder: () => void;
  onRefresh: () => void;
  onSearch: (query: string) => void;
  onSelect: (path: string) => void;
  onReveal?: () => void;
}

/**
 * Workspace panel (docs/04-DASHBOARD.md, left column).
 *
 * Header actions: open local folder, search, refresh. Below, the project
 * explorer tree.
 */
export function WorkspacePanel({
  project,
  files,
  results,
  canPickFolder,
  onOpenFolder,
  onRefresh,
  onSearch,
  onSelect,
  onReveal,
}: WorkspacePanelProps) {
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close the overflow menu on an outside click.
  useEffect(() => {
    if (!menuOpen) return;
    const away = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', away);
    return () => document.removeEventListener('mousedown', away);
  }, [menuOpen]);

  const listed = results.length > 0 ? results.map((r) => r.path) : files;

  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-[10px] border border-[var(--aera-line-strong)] bg-[var(--aera-bg-surface)]">
      <div className="flex items-center gap-1.5 border-b border-[var(--aera-line-default)] px-2.5 py-2">
        <Folder size={13} className="text-[var(--aera-accent-primary)]" />
        <span className="flex-1 truncate text-[10.5px] uppercase tracking-[0.1em]">
          {project?.name ?? 'Workspace'}
        </span>
        <button
          onClick={() => setSearching((v) => !v)}
          title="Search workspace"
          className="rounded p-[3px] text-[var(--aera-text-muted)] hover:bg-[var(--aera-bg-hover)] hover:text-[var(--aera-text-primary)]"
        >
          <Search size={12} />
        </button>
        <button
          onClick={onRefresh}
          title="Refresh workspace"
          className="rounded p-[3px] text-[var(--aera-text-muted)] hover:bg-[var(--aera-bg-hover)] hover:text-[var(--aera-text-primary)]"
        >
          <RefreshCw size={12} />
        </button>
        {canPickFolder && (
          <button
            onClick={onOpenFolder}
            title="Open local folder"
            className="rounded p-[3px] text-[var(--aera-text-muted)] hover:bg-[var(--aera-bg-hover)] hover:text-[var(--aera-text-primary)]"
          >
            <FolderPlus size={12} />
          </button>
        )}
        <div ref={menuRef} className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            title="More"
            aria-label="Workspace menu"
            className="rounded p-[3px] text-[var(--aera-text-muted)] hover:bg-[var(--aera-bg-hover)] hover:text-[var(--aera-text-primary)]"
          >
            <MoreVertical size={12} />
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-6 z-30 w-40 overflow-hidden rounded-lg border border-[var(--aera-line-strong)] bg-[var(--aera-bg-overlay)] py-1 shadow-xl">
              {[
                ['Open Local Folder', onOpenFolder],
                ['Refresh Index', onRefresh],
                ['Search Workspace', () => setSearching(true)],
                ['Reveal in Files', () => onReveal?.()],
              ].map(([label, action]) => (
                <button
                  key={String(label)}
                  onClick={() => {
                    setMenuOpen(false);
                    (action as () => void)();
                  }}
                  className="block w-full px-3 py-1.5 text-left text-[11px] hover:bg-[var(--aera-bg-hover)]"
                >
                  {String(label)}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {searching && (
        <input
          autoFocus
          value={query}
          placeholder="Search files…"
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch(query)}
          className="selectable m-2 rounded border border-[var(--aera-line-default)] bg-[var(--aera-bg-raised)] px-2 py-1 text-[11.5px] focus:border-[var(--aera-accent-primary)]"
        />
      )}

      <div className="min-h-0 flex-1 overflow-y-auto p-1.5">
        {!project ? (
          <button
            onClick={canPickFolder ? onOpenFolder : undefined}
            className={cn(
              'flex w-full items-center gap-1.5 rounded px-2 py-1.5 text-left text-[11.5px] text-[var(--aera-text-muted)]',
              canPickFolder && 'hover:bg-[var(--aera-bg-hover)] hover:text-[var(--aera-text-primary)]',
            )}
          >
            <ChevronRight size={11} />
            <Folder size={12} />
            Default
          </button>
        ) : (
          <>
            <button
              onClick={() => setExpanded((v) => !v)}
              className="flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-[11.5px] hover:bg-[var(--aera-bg-hover)]"
            >
              <ChevronRight
                size={11}
                className={cn('transition-transform', expanded && 'rotate-90')}
              />
              {expanded ? (
                <FolderOpen size={12} className="text-[var(--aera-accent-primary)]" />
              ) : (
                <Folder size={12} className="text-[var(--aera-accent-primary)]" />
              )}
              <span className="truncate">{project.name}</span>
              <span className="ml-auto text-[9.5px] text-[var(--aera-text-disabled)]">
                {project.files}
              </span>
            </button>

            {expanded &&
              listed.slice(0, 300).map((path) => (
                <button
                  key={path}
                  onClick={() => onSelect(path)}
                  title={path}
                  className="flex w-full items-center gap-1 rounded py-[2px] pl-6 pr-2 text-left font-mono text-[10.5px] text-[var(--aera-text-muted)] hover:bg-[var(--aera-bg-hover)] hover:text-[var(--aera-text-primary)]"
                >
                  <span className="truncate">{path}</span>
                </button>
              ))}
          </>
        )}
      </div>
    </div>
  );
}
