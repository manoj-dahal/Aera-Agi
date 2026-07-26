/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

/**
 * Store behaviour with the API mocked.
 *
 * Stores own every loading flag and error message the UI renders, so a store
 * that forgets to clear `loading` on failure leaves a permanent spinner, and
 * one that drops the error leaves a blank page. Neither is visible from
 * reading a component.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@services/api', () => ({
  agents: {
    list: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
    restart: vi.fn(),
  },
  memory: { list: vi.fn(), stats: vi.fn(), search: vi.fn(), consolidate: vi.fn(), remove: vi.fn() },
  avatars: { list: vi.fn(), scan: vi.fn(), setActive: vi.fn(), upload: vi.fn(), remove: vi.fn(), importNative: vi.fn() },
  chat: { send: vi.fn(), stream: vi.fn() },
  system: { status: vi.fn(), telemetry: vi.fn(), events: vi.fn() },
  workspace: { summary: vi.fn(), open: vi.fn(), openDialog: vi.fn(), search: vi.fn(), readFile: vi.fn() },
}));

const api = await import('@services/api');
const { useAgentStore } = await import('@store/useAgentStore');
const { useMemoryStore } = await import('@store/useMemoryStore');
const { useChatStore } = await import('@store/useChatStore');

const AGENT = {
  name: 'core',
  status: 'running',
  priority: 1,
  capabilities: ['conversation'],
  description: '',
};

beforeEach(() => {
  vi.clearAllMocks();
  useAgentStore.setState({ agents: [], summary: null, capabilities: {}, loading: false, error: null });
  useMemoryStore.setState({ nodes: [], results: [], stats: null, query: '', loading: false, error: null });
  useChatStore.getState().clear();
});

describe('useAgentStore', () => {
  it('populates from the API', async () => {
    vi.mocked(api.agents.list).mockResolvedValue({
      agents: [AGENT],
      summary: { total: 1, running: 1 },
      capabilities: { conversation: ['core'] },
    } as never);

    await useAgentStore.getState().load();

    expect(useAgentStore.getState().agents).toHaveLength(1);
    expect(useAgentStore.getState().error).toBeNull();
  });

  it('clears loading when the request fails', async () => {
    // A store that leaves loading true renders a spinner that never stops.
    vi.mocked(api.agents.list).mockRejectedValue(new Error('kernel down'));

    await useAgentStore.getState().load();

    expect(useAgentStore.getState().loading).toBe(false);
    expect(useAgentStore.getState().error).toBe('kernel down');
  });

  it('clears a stale error on the next success', async () => {
    vi.mocked(api.agents.list).mockRejectedValueOnce(new Error('kernel down'));
    await useAgentStore.getState().load();

    vi.mocked(api.agents.list).mockResolvedValue({
      agents: [AGENT], summary: null, capabilities: {},
    } as never);
    await useAgentStore.getState().load();

    expect(useAgentStore.getState().error).toBeNull();
  });

  it('reloads after starting an agent, so the new status shows', async () => {
    vi.mocked(api.agents.list).mockResolvedValue({
      agents: [AGENT], summary: null, capabilities: {},
    } as never);

    await useAgentStore.getState().start('core');

    expect(api.agents.start).toHaveBeenCalledWith('core');
    expect(api.agents.list).toHaveBeenCalled();
  });

  it('finds an agent by name', async () => {
    useAgentStore.setState({ agents: [AGENT] as never });

    expect(useAgentStore.getState().byName('core')?.name).toBe('core');
    expect(useAgentStore.getState().byName('absent')).toBeUndefined();
  });
});

describe('useMemoryStore', () => {
  it('loads nodes and stats together', async () => {
    vi.mocked(api.memory.list).mockResolvedValue({ memories: [{ id: 'a' }] } as never);
    vi.mocked(api.memory.stats).mockResolvedValue({ nodes: 1 } as never);

    await useMemoryStore.getState().load();

    expect(useMemoryStore.getState().nodes).toHaveLength(1);
    expect(useMemoryStore.getState().stats).toEqual({ nodes: 1 });
  });

  it('records the failure reason', async () => {
    vi.mocked(api.memory.list).mockRejectedValue(new Error('graph unavailable'));

    await useMemoryStore.getState().load();

    expect(useMemoryStore.getState().error).toBe('graph unavailable');
    expect(useMemoryStore.getState().loading).toBe(false);
  });

  it('an empty query falls back to the full list rather than searching', async () => {
    vi.mocked(api.memory.list).mockResolvedValue({ memories: [] } as never);
    vi.mocked(api.memory.stats).mockResolvedValue({} as never);

    await useMemoryStore.getState().search('   ');

    expect(api.memory.search).not.toHaveBeenCalled();
    expect(api.memory.list).toHaveBeenCalled();
  });

  it('stores search results separately from the browse list', async () => {
    useMemoryStore.setState({ nodes: [{ id: 'browse' }] as never });
    vi.mocked(api.memory.search).mockResolvedValue({
      results: [{ node: { id: 'hit' }, score: 0.9 }],
    } as never);

    await useMemoryStore.getState().search('deploy key');

    // Browsing must survive a search, or clearing the box loses the list.
    expect(useMemoryStore.getState().nodes).toHaveLength(1);
    expect(useMemoryStore.getState().results).toHaveLength(1);
  });
});

describe('useChatStore', () => {
  it('appends a message that the model did not generate', () => {
    useChatStore.getState().append({ role: 'user', content: 'Attached notes.md' });

    const [message] = useChatStore.getState().messages;
    expect(message?.content).toBe('Attached notes.md');
    // The store owns identity and timing, not the caller.
    expect(message?.id).toBeTruthy();
    expect(message?.timestamp).toBeGreaterThan(0);
  });

  it('ignores an empty send', async () => {
    await useChatStore.getState().send('   ');

    expect(useChatStore.getState().messages).toHaveLength(0);
  });

  it('refuses a concurrent send while streaming', async () => {
    useChatStore.setState({ streaming: true });

    await useChatStore.getState().send('hello');

    expect(useChatStore.getState().messages).toHaveLength(0);
  });

  it('starts a new conversation with a fresh id', () => {
    const before = useChatStore.getState().conversationId;
    useChatStore.getState().append({ role: 'user', content: 'x' });

    useChatStore.getState().newConversation();

    expect(useChatStore.getState().messages).toHaveLength(0);
    expect(useChatStore.getState().conversationId).not.toBe(before);
  });

  it('exports a readable transcript', () => {
    useChatStore.getState().append({ role: 'user', content: 'ping' });
    useChatStore.getState().append({ role: 'assistant', content: 'pong' });

    const transcript = useChatStore.getState().transcript();

    expect(transcript).toContain('ping');
    expect(transcript).toContain('pong');
  });
});
