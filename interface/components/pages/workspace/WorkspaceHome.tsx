/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import { useEffect, useState } from 'react';
import { WorkspaceLayout } from '@layouts/WorkspaceLayout';
import {
  BarMeter,
  Button,
  Card,
  CodeViewer,
  EmptyState,
  ErrorState,
  Input,
  StatCard,
  StatRow,
  Tag,
} from '@components/index';
import { useWorkspaceStore } from '@store/index';
import { chartColors } from '@design/colors';

/** Project explorer backed by the workspace indexer (docs/14-WORKSPACE.md). */
export function WorkspaceHome() {
  const {
    project, results, selected, loading, error, canPickFolder,
    refresh, openDialog, open, reindex, search, select,
  } = useWorkspaceStore();

  const [query, setQuery] = useState('');
  const [path, setPath] = useState('');

  useEffect(() => void refresh(), [refresh]);

  const languages = Object.entries(project?.languages ?? {});
  const totalFiles = project?.files ?? 0;

  const toolbar = (
    <>
      <div className="mb-3 flex flex-wrap gap-2">
        {canPickFolder() ? (
          <Button variant="primary" onClick={() => void openDialog()} loading={loading}>
            Open Local Folder…
          </Button>
        ) : (
          <>
            <Input
              value={path}
              placeholder="/path/to/your/project"
              onChange={(e) => setPath(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void open(path)}
            />
            <Button variant="primary" onClick={() => void open(path)} loading={loading}>
              Open
            </Button>
          </>
        )}
        <Button variant="ghost" onClick={() => void reindex()} disabled={!project}>
          Re-index
        </Button>
      </div>

      {project && (
        <StatRow>
          <StatCard label="Project" value={project.name} />
          <StatCard label="Files" value={project.files} />
          <StatCard label="Lines" value={project.total_lines.toLocaleString()} />
          <StatCard label="Symbols" value={project.symbols ?? 0} />
          <StatCard label="Skipped" value={project.skipped} />
        </StatRow>
      )}

      <div className="mb-3 flex gap-2">
        <Input
          value={query}
          placeholder="Search files and symbols…"
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void search(query)}
          disabled={!project}
        />
        <Button variant="ghost" onClick={() => void search(query)} disabled={!project}>
          Search
        </Button>
      </div>
    </>
  );

  if (!project) {
    return (
      <div className="flex min-h-0 flex-1 flex-col p-4">
        {toolbar}
        {/* A failed open must not look the same as never having opened one. */}
        {error ? (
          <ErrorState message={error} onRetry={() => void refresh()} />
        ) : (
        <EmptyState
          title="No project open"
          message={
            canPickFolder()
              ? 'Choose a folder to index. AERA builds a symbol index and writes the project into the memory graph.'
              : 'Enter a project path above. AERA builds a symbol index and writes the project into the memory graph.'
          }
        />
        )}
      </div>
    );
  }

  return (
    <WorkspaceLayout
      toolbar={toolbar}
      list={
        <div className="flex flex-col gap-2">
          {results.length === 0 ? (
            <Card>
              <h4 className="mb-2 text-[12px] uppercase tracking-wide text-[var(--aera-text-muted)]">
                Languages
              </h4>
              {languages.map(([language, count], index) => (
                <BarMeter
                  key={language}
                  label={language}
                  value={count}
                  total={totalFiles}
                  color={chartColors[index % chartColors.length]}
                />
              ))}
              <div className="mt-2 flex flex-wrap gap-1">
                {project.kinds.map((kind) => (
                  <Tag key={kind}>{kind}</Tag>
                ))}
              </div>
            </Card>
          ) : (
            results.map((file) => (
              <Card
                key={file.path}
                interactive
                onClick={() => void select(file.path)}
                className={
                  selected?.path === file.path
                    ? 'border-[var(--aera-accent-primary)]'
                    : undefined
                }
              >
                <h4 className="break-all font-mono text-[11.5px]">{file.path}</h4>
                <div className="mt-1 flex justify-between text-[11px] text-[var(--aera-text-muted)]">
                  <span>{file.language}</span>
                  <span>{file.lines} lines</span>
                </div>
                {file.symbols.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {file.symbols.slice(0, 5).map((symbol) => (
                      <Tag key={`${file.path}-${symbol.name}-${symbol.line}`}>
                        {symbol.name}
                      </Tag>
                    ))}
                  </div>
                )}
              </Card>
            ))
          )}
        </div>
      }
      detail={
        <CodeViewer
          content={selected?.content}
          emptyMessage={
            results.length === 0
              ? 'Search for a file to preview it.'
              : 'Select a file to preview it.'
          }
        />
      }
    />
  );
}

export default WorkspaceHome;
