import { useEffect, useState } from 'react';
import {
  Button,
  Card,
  CardGrid,
  EmptyState,
  Input,
  LoadingState,
  PageHeader,
  StatCard,
  StatRow,
  Tag,
} from '@components/index';
import { useMemoryStore } from '@store/index';
import { memoryTypeColors, type MemoryType } from '@design/colors';
import { timeAgo, truncate } from '@utils/format';
import type { MemoryNode } from '@services/types';

/** Browse and search the shared Memory Graph (docs/06-MEMORY-GRAPH.md). */
export function MemoryHome() {
  const { nodes, results, stats, loading, load, search, consolidate } = useMemoryStore();
  const [query, setQuery] = useState('');

  useEffect(() => void load(), [load]);

  const items: Array<MemoryNode & { score?: number }> = query.trim()
    ? results.map((r) => ({ ...r.node, score: r.score }))
    : nodes;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Memory"
        subtitle="Hybrid semantic and keyword recall across the knowledge graph"
        action={
          <Button variant="ghost" onClick={() => void consolidate()}>
            Consolidate
          </Button>
        }
      />

      <div className="mb-3.5 flex gap-2">
        <Input
          value={query}
          placeholder="Search the memory graph…"
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void search(query)}
        />
        <Button variant="primary" onClick={() => void search(query)}>
          Search
        </Button>
        <Button
          variant="ghost"
          onClick={() => {
            setQuery('');
            void load();
          }}
        >
          Show all
        </Button>
      </div>

      <StatRow>
        <StatCard label="Nodes" value={stats?.nodes ?? 0} />
        <StatCard label="Edges" value={stats?.edges ?? 0} />
        <StatCard label="Tags" value={stats?.tags ?? 0} />
        <StatCard label="Conversations" value={stats?.conversations ?? 0} />
        <StatCard label="Dimensions" value={stats?.embedding_dimensions ?? 0} />
      </StatRow>

      <CardGrid>
        {loading && <LoadingState />}
        {!loading && items.length === 0 && (
          <EmptyState
            title="No memories yet"
            message="Start a conversation — AERA records every exchange as linked nodes in the graph."
          />
        )}
        {!loading &&
          items.map((node) => (
            <Card key={node.id}>
              <div className="mb-1 flex items-start justify-between gap-2">
                <h4 className="text-[13px] font-semibold leading-snug">{node.title}</h4>
                {node.score !== undefined && (
                  <Tag className="shrink-0">{node.score.toFixed(2)}</Tag>
                )}
              </div>
              <p className="selectable text-[12px] text-[var(--aera-text-muted)]">
                {truncate(node.content || node.description, 165)}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <Tag>{node.type}</Tag>
                <span
                  className="rounded-[4px] px-1.5 py-[2px] text-[9.5px]"
                  style={{
                    color: memoryTypeColors[node.memory_type as MemoryType],
                    background: `${memoryTypeColors[node.memory_type as MemoryType]}22`,
                  }}
                >
                  {node.memory_type}
                </span>
                {node.tags.slice(0, 3).map((tag) => (
                  <Tag key={tag}>{tag}</Tag>
                ))}
                <span className="ml-auto text-[9.5px] text-[var(--aera-text-disabled)]">
                  {timeAgo(node.updated_at)}
                </span>
              </div>
            </Card>
          ))}
      </CardGrid>
    </div>
  );
}

export default MemoryHome;
