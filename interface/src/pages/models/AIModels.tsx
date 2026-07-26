/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import { useEffect, useState } from 'react';
import {
  Button, Card, CardGrid, ErrorState, Field, Input, KeyValue, LoadingState,
  PageHeader, StatCard, StatRow, StatusPill, Tag, useToast,
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
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState({ name: '', base_url: '', model: '', api_key: '' });
  const showToast = useToast((s) => s.show);

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

  /**
   * Register a user-supplied model server.
   *
   * Anything speaking the OpenAI chat-completions contract works, which is
   * most self-hosted options, so only a base URL is genuinely required.
   */
  const addProvider = async () => {
    if (!draft.name.trim() || !draft.base_url.trim()) {
      showToast('A name and a base URL are required', 'error');
      return;
    }
    setBusy(true);
    try {
      const result = await models.addProvider({
        name: draft.name.trim(),
        type: 'custom',
        base_url: draft.base_url.trim(),
        model: draft.model.trim() || undefined,
        api_key: draft.api_key.trim() || undefined,
      });
      // An unreachable endpoint is still registered; say so rather than
      // implying it is ready to use.
      showToast(
        result.warning ?? `Added ${draft.name}`,
        result.warning ? 'error' : 'success',
      );
      setDraft({ name: '', base_url: '', model: '', api_key: '' });
      setAdding(false);
      await load();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'could not add the provider', 'error');
    } finally {
      setBusy(false);
    }
  };

  const testProvider = async (name: string) => {
    try {
      const result = await models.testProvider(name);
      showToast(
        result.healthy ? `${name}: ${result.models.length} model(s)` : `${name} is not responding`,
        result.healthy ? 'success' : 'error',
      );
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'test failed', 'error');
    }
  };

  const providers = Object.entries(health);
  const localCount = list.filter((m) => m.local).length;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Models"
        subtitle="Local-first routing with automatic failover across providers"
        action={
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => void load()}>Refresh</Button>
            <Button variant="primary" onClick={() => setAdding((v) => !v)}>
              {adding ? 'Cancel' : 'Add Model'}
            </Button>
          </div>
        }
      />

      {error && <ErrorState message={error} onRetry={() => void load()} />}

      {adding && (
        <Card title="Add your own model" className="mb-4 max-w-2xl">
          <p className="mb-3 text-[11.5px] leading-relaxed text-[var(--aera-text-muted)]">
            Any OpenAI-compatible server works — vLLM, llama.cpp, LM Studio, LiteLLM
            or a company gateway. Only the name and base URL are required.
          </p>
          <div className="grid gap-2 [grid-template-columns:repeat(auto-fit,minmax(220px,1fr))]">
            <Field label="Name">
              <Input
                value={draft.name}
                placeholder="my-server"
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              />
            </Field>
            <Field label="Base URL">
              <Input
                value={draft.base_url}
                placeholder="http://localhost:8000/v1"
                onChange={(e) => setDraft({ ...draft, base_url: e.target.value })}
              />
            </Field>
            <Field label="Model (optional)">
              <Input
                value={draft.model}
                placeholder="llama-3"
                onChange={(e) => setDraft({ ...draft, model: e.target.value })}
              />
            </Field>
            <Field label="API key (optional)">
              <Input
                type="password"
                value={draft.api_key}
                placeholder="leave blank if unauthenticated"
                onChange={(e) => setDraft({ ...draft, api_key: e.target.value })}
              />
            </Field>
          </div>
          <div className="mt-3">
            <Button variant="primary" loading={busy} onClick={() => void addProvider()}>
              Connect
            </Button>
          </div>
        </Card>
      )}

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
            <div className="mt-2 flex gap-1.5">
              <Button size="sm" variant="ghost" onClick={() => void testProvider(name)}>
                Test
              </Button>
              {/* builtin is the offline fallback and cannot be removed. */}
              {name !== 'builtin' && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={async () => {
                    try {
                      await models.removeProvider(name);
                      showToast(`Removed ${name}`, 'success');
                      await load();
                    } catch (err) {
                      showToast(err instanceof Error ? err.message : 'remove failed', 'error');
                    }
                  }}
                >
                  Remove
                </Button>
              )}
            </div>
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
