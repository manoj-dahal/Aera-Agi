/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

/** Agent roster and control. */

import { create } from 'zustand';
import { agents } from '@services/api';
import type { AgentInfo, AgentSummary } from '@services/types';

interface AgentState {
  agents: AgentInfo[];
  summary: AgentSummary | null;
  capabilities: Record<string, string[]>;
  loading: boolean;
  error: string | null;

  load: () => Promise<void>;
  start: (name: string) => Promise<void>;
  stop: (name: string) => Promise<void>;
  restart: (name: string) => Promise<void>;
  byName: (name: string) => AgentInfo | undefined;
}

export const useAgentStore = create<AgentState>((set, get) => ({
  agents: [],
  summary: null,
  capabilities: {},
  loading: false,
  error: null,

  load: async () => {
    set({ loading: true });
    try {
      const data = await agents.list();
      set({
        agents: data.agents,
        summary: data.summary,
        capabilities: data.capabilities,
        loading: false,
        error: null,
      });
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : 'failed to load agents' });
    }
  },

  start: async (name) => { await agents.start(name); await get().load(); },
  stop: async (name) => { await agents.stop(name); await get().load(); },
  restart: async (name) => { await agents.restart(name); await get().load(); },

  byName: (name) => get().agents.find((a) => a.name === name),
}));
