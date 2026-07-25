import { useEffect, useState } from 'react';
import { Card, LoadingState, StatCard, StatRow } from '@components/index';
import { MemoryGraphCanvas } from '@components/charts/MemoryGraphCanvas';
import { SkillPanel } from '@components/widgets/SkillPanel';
import { useMemoryStore } from '@store/index';
import { skills as skillsApi } from '@services/api';
import type { SkillState, SkillSummary } from '@services/types';
import { memoryTypeColors } from '@design/colors';

const MEMORY_SYSTEMS = [
  ['short_term', 'Short-Term Memory'],
  ['long_term', 'Long-Term Memory'],
  ['working', 'Working Memory'],
  ['semantic', 'Semantic Memory'],
  ['episodic', 'Episodic Memory'],
  ['procedural', 'Procedural Memory'],
] as const;

/**
 * Macros: the memory intelligence centre (docs/05-MACROS.md).
 *
 * Neural memory graph on the left, memory system breakdown on the right.
 */
export function MacrosHome() {
  const { stats, nodes, loading, load } = useMemoryStore();
  const [skillList, setSkillList] = useState<SkillState[]>([]);
  const [skillSummary, setSkillSummary] = useState<SkillSummary | null>(null);

  useEffect(() => void load(), [load]);

  // AI skills live here, not in Apps: they run in the background and are
  // visualised alongside the memory graph.
  useEffect(() => {
    void skillsApi
      .list()
      .then((data) => {
        setSkillList(data.skills);
        setSkillSummary(data.summary);
      })
      .catch(() => {});
  }, []);

  const byType = stats?.by_memory_type ?? {};

  return (
    <div className="flex min-h-0 flex-1 gap-4 px-4 pb-3">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="mb-2 text-[10.5px] uppercase tracking-[0.14em] text-[var(--aera-text-muted)]">
          Neural Memory Graph
        </div>
        <div className="relative min-h-0 flex-1 overflow-hidden rounded-[10px] border border-[var(--aera-line-strong)] bg-[var(--aera-bg-raised)]">
          {loading && nodes.length === 0 ? (
            <LoadingState />
          ) : (
            <MemoryGraphCanvas nodes={nodes} />
          )}
        </div>
      </div>

      <div className="flex w-[262px] shrink-0 flex-col gap-2.5 overflow-y-auto">
        <StatRow>
          <StatCard label="Nodes" value={stats?.nodes ?? 0} />
          <StatCard label="Edges" value={stats?.edges ?? 0} />
        </StatRow>

        <Card title="Memory Panel">
          {MEMORY_SYSTEMS.map(([key, label]) => (
            <div key={key} className="flex items-center gap-2 py-[3px] text-[11.5px]">
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ background: memoryTypeColors[key] }}
              />
              <span className="flex-1 text-[var(--aera-text-muted)]">{label}</span>
              <span>{byType[key] ?? 0}</span>
            </div>
          ))}
        </Card>

        <Card>
          <SkillPanel skills={skillList} summary={skillSummary} loading={loading} />
        </Card>

        <Card title="Background Engines">
          {['Memory Engine', 'Relationship Engine', 'Context Engine', 'Recall Engine', 'Compression Engine'].map(
            (engine) => (
              <div key={engine} className="flex items-center gap-2 py-[3px] text-[11.5px]">
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ background: 'var(--aera-success)', boxShadow: '0 0 5px var(--aera-success)' }}
                />
                <span className="text-[var(--aera-text-muted)]">{engine}</span>
              </div>
            ),
          )}
        </Card>
      </div>
    </div>
  );
}

export default MacrosHome;
