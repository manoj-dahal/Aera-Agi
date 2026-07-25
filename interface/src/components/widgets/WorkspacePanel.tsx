import { useState } from 'react';
import { ChevronRight, Folder, FolderOpen, FolderPlus, RefreshCw, Search } from 'lucide-react';
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
}: WorkspacePanelProps) {
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [expanded, setExpanded] = useState(true);

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
