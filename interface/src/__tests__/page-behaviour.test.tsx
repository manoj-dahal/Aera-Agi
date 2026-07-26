/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

/**
 * Pages rendered end to end against a mocked API.
 *
 * This is the layer that catches the bug the source-analysis suite was
 * written after: a page whose store recorded an error that never reached the
 * screen. Reading the source tells you `error` is destructured; only
 * rendering tells you it is displayed.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { ReactElement } from 'react';

vi.mock('@services/api', () => ({
  agents: { list: vi.fn(), start: vi.fn(), stop: vi.fn(), restart: vi.fn() },
  memory: {
    list: vi.fn(), stats: vi.fn(), search: vi.fn(), consolidate: vi.fn(), remove: vi.fn(),
  },
  models: {
    list: vi.fn(), health: vi.fn(), addProvider: vi.fn(), testProvider: vi.fn(),
    removeProvider: vi.fn(), providerTypes: vi.fn(),
  },
  system: { audit: vi.fn(), status: vi.fn(), settings: vi.fn(), secrets: vi.fn() },
  avatars: {
    list: vi.fn(), scan: vi.fn(), setActive: vi.fn(), upload: vi.fn(), remove: vi.fn(),
    importNative: vi.fn(),
  },
  workspace: { summary: vi.fn(), open: vi.fn(), search: vi.fn(), readFile: vi.fn() },
  uploads: { list: vi.fn(), send: vi.fn(), analyse: vi.fn() },
  chat: { send: vi.fn() },
  voice: { speak: vi.fn(), tapToMemory: vi.fn() },
  hologram: { status: vi.fn() },
  automation: { list: vi.fn() },
  skills: { list: vi.fn(), summary: vi.fn() },
}));

const api = await import('@services/api');
const { AgentsHome } = await import('@pages/agents/AgentsHome');
const { MemoryHome } = await import('@pages/memory/MemoryHome');
const { AIModels } = await import('@pages/models/AIModels');
const { useAgentStore } = await import('@store/useAgentStore');
const { useMemoryStore } = await import('@store/useMemoryStore');

const wrap = (ui: ReactElement) => render(<MemoryRouter>{ui}</MemoryRouter>);

beforeEach(() => {
  vi.clearAllMocks();
  useAgentStore.setState({
    agents: [], summary: null, capabilities: {}, loading: false, error: null,
  });
  useMemoryStore.setState({
    nodes: [], results: [], stats: null, query: '', loading: false, error: null,
  });
});

describe('AgentsHome', () => {
  const AGENT = {
    name: 'core', status: 'running', priority: 1,
    capabilities: ['conversation'], description: 'The main agent',
  };

  it('renders the roster once loaded', async () => {
    vi.mocked(api.agents.list).mockResolvedValue({
      agents: [AGENT], summary: { total: 1, running: 1 }, capabilities: {},
    } as never);

    wrap(<AgentsHome />);

    expect(await screen.findByText('core')).toBeInTheDocument();
  });

  it('shows the failure reason instead of an empty roster', async () => {
    // The regression this file exists for: the store recorded the error and
    // the page rendered nothing at all.
    vi.mocked(api.agents.list).mockRejectedValue(new Error('kernel is not reachable'));

    wrap(<AgentsHome />);

    expect(await screen.findByText('kernel is not reachable')).toBeInTheDocument();
  });

  it('retries when asked', async () => {
    vi.mocked(api.agents.list).mockRejectedValueOnce(new Error('kernel down'));
    wrap(<AgentsHome />);
    await screen.findByText('kernel down');

    vi.mocked(api.agents.list).mockResolvedValue({
      agents: [AGENT], summary: null, capabilities: {},
    } as never);
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText('core')).toBeInTheDocument();
  });

  it('starts an agent when its button is pressed', async () => {
    vi.mocked(api.agents.list).mockResolvedValue({
      agents: [{ ...AGENT, status: 'stopped' }], summary: null, capabilities: {},
    } as never);
    vi.mocked(api.agents.start).mockResolvedValue({} as never);
    wrap(<AgentsHome />);
    await screen.findByText('core');

    await userEvent.click(screen.getByRole('button', { name: 'Start' }));

    await waitFor(() => expect(api.agents.start).toHaveBeenCalledWith('core'));
  });
});

describe('MemoryHome', () => {
  it('lists memories', async () => {
    vi.mocked(api.memory.list).mockResolvedValue({
      memories: [
        { id: '1', title: 'Deploy key in the vault', memory_type: 'long_term', tags: [] },
      ],
    } as never);
    vi.mocked(api.memory.stats).mockResolvedValue({ nodes: 1, edges: 0 } as never);

    wrap(<MemoryHome />);

    expect(await screen.findByText('Deploy key in the vault')).toBeInTheDocument();
  });

  it('reports a failed load rather than looking empty', async () => {
    vi.mocked(api.memory.list).mockRejectedValue(new Error('graph unavailable'));

    wrap(<MemoryHome />);

    expect(await screen.findByText('graph unavailable')).toBeInTheDocument();
  });
});

describe('AIModels: adding a custom provider', () => {
  beforeEach(() => {
    vi.mocked(api.models.list).mockResolvedValue({
      models: [], count: 0, providers: ['builtin'],
    } as never);
    vi.mocked(api.models.health).mockResolvedValue({
      builtin: {
        healthy: true, local: true,
        stats: { requests: 0, failures: 0, avg_latency_ms: 0, tokens_in: 0, tokens_out: 0 },
      },
    } as never);
  });

  it('reveals the form on demand', async () => {
    wrap(<AIModels />);
    await screen.findByText('builtin');

    await userEvent.click(screen.getByRole('button', { name: 'Add Model' }));

    expect(screen.getByPlaceholderText('http://localhost:8000/v1')).toBeInTheDocument();
  });

  it('submits what the user typed', async () => {
    vi.mocked(api.models.addProvider).mockResolvedValue({
      name: 'my-server', healthy: true, warning: null,
    } as never);
    wrap(<AIModels />);
    await screen.findByText('builtin');
    await userEvent.click(screen.getByRole('button', { name: 'Add Model' }));

    await userEvent.type(screen.getByPlaceholderText('my-server'), 'my-server');
    await userEvent.type(
      screen.getByPlaceholderText('http://localhost:8000/v1'),
      'http://localhost:8000/v1',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Connect' }));

    await waitFor(() =>
      expect(api.models.addProvider).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'my-server',
          base_url: 'http://localhost:8000/v1',
          type: 'custom',
        }),
      ),
    );
  });

  it('refuses to submit without a base URL', async () => {
    wrap(<AIModels />);
    await screen.findByText('builtin');
    await userEvent.click(screen.getByRole('button', { name: 'Add Model' }));

    await userEvent.type(screen.getByPlaceholderText('my-server'), 'incomplete');
    await userEvent.click(screen.getByRole('button', { name: 'Connect' }));

    expect(api.models.addProvider).not.toHaveBeenCalled();
  });

  it('does not offer to remove the builtin fallback', async () => {
    // Removing it would leave a failed cloud call with nowhere to land.
    wrap(<AIModels />);
    await screen.findByText('builtin');

    expect(screen.queryByRole('button', { name: 'Remove' })).toBeNull();
  });

  it('tests a provider on request', async () => {
    vi.mocked(api.models.testProvider).mockResolvedValue({
      provider: 'builtin', healthy: true, models: ['echo'], error: null,
    } as never);
    wrap(<AIModels />);
    await screen.findByText('builtin');

    await userEvent.click(screen.getByRole('button', { name: 'Test' }));

    await waitFor(() => expect(api.models.testProvider).toHaveBeenCalledWith('builtin'));
  });
});
