import { useEffect, useState } from 'react';
import {
  Button, Card, CardGrid, KeyValue, LoadingState, PageHeader,
  StatCard, StatRow, StatusPill, Tag,
} from '@components/index';
import { models } from '@services/api';
import { formatDuration } from '@utils/format';
import type { ModelInfo, ProviderHealth } from '@services/types';

/** Local and cloud model inventory with provider health (docs/18-LOCAL-LLM.md). */
export function AIModels() {
  const [list, setList] = useState<ModelInfo[]>([]);
  const [health, setHealth] = useState<Record<string, ProviderHealth>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [modelData, healthData] = await Promise.all([models.list(), models.health()]);
      setList(modelData.models);
      setHealth(healthData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'could not load models');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => void load(), []);

  const providers = Object.entries(health);
  const localCount = list.filter((m) => m.local).length;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Models"
        subtitle="Local-first routing with automatic failover across providers"
        action={<Button variant="ghost" onClick={() => void load()}>Refresh</Button>}
      />

      <StatRow>
        <StatCard label="Models" value={list.length} />
        <StatCard label="Local" value={localCount} accent="var(--aera-success)" />
        <StatCard label="Cloud" value={list.length - localCount} />
        <StatCard label="Providers" value={providers.length} />
      </StatRow>

      {error && <p className="mb-3 text-[12px] text-[var(--aera-danger)]">{error}</p>}

      <h3 className="mb-2 text-[10.5px] uppercase tracking-[0.11em] text-[var(--aera-text-muted)]">
        Providers
      </h3>
      <CardGrid className="mb-5">
        {providers.map(([name, info]) => (
          <Card key={name}>
            <div className="mb-1.5 flex items-center justify-between">
              <h4 className="text-[13px] font-semibold">{name}</h4>
              <StatusPill status={info.healthy ? 'healthy' : 'offline'} />
            </div>
            <KeyValue label="Type" value={info.local ? 'local' : 'cloud'} />
            <KeyValue label="Requests" value={info.stats.requests} />
            <KeyValue label="Failures" value={info.stats.failures} />
            <KeyValue label="Avg latency" value={formatDuration(info.stats.avg_latency_ms)} />
            <KeyValue
              label="Tokens"
              value={`${info.stats.tokens_in} in / ${info.stats.tokens_out} out`}
            />
          </Card>
        ))}
      </CardGrid>

      <h3 className="mb-2 text-[10.5px] uppercase tracking-[0.11em] text-[var(--aera-text-muted)]">
        Available models
      </h3>
      <CardGrid>
        {loading && <LoadingState />}
        {list.map((model) => (
          <Card key={`${model.provider}-${model.id}`}>
            <div className="mb-1 flex items-start justify-between gap-2">
              <h4 className="break-all text-[12.5px] font-semibold">{model.name || model.id}</h4>
              {model.local && <Tag>local</Tag>}
            </div>
            <KeyValue label="Provider" value={model.provider} />
            <KeyValue label="Context" value={`${(model.context_length / 1000).toFixed(0)}K`} />
            {model.size && <KeyValue label="Size" value={model.size} />}
            {model.quantization && <KeyValue label="Quant" value={model.quantization} />}
          </Card>
        ))}
      </CardGrid>
    </div>
  );
}

export default AIModels;
