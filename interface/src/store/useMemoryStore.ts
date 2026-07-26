/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

/** Memory graph browsing and search. */

import { create } from 'zustand';
import { memory } from '@services/api';
import type { MemoryNode, MemoryStats, RecallResult } from '@services/types';

interface MemoryState {
  nodes: MemoryNode[];
  results: RecallResult[];
  stats: MemoryStats | null;
  query: string;
  loading: boolean;
  error: string | null;

  load: () => Promise<void>;
  search: (query: string) => Promise<void>;
  consolidate: () => Promise<void>;
  remove: (id: string) => Promise<void>;
}

export const useMemoryStore = create<MemoryState>((set, get) => ({
  nodes: [],
  results: [],
  stats: null,
  query: '',
  loading: false,
  error: null,

  load: async () => {
    set({ loading: true });
    try {
      const [list, stats] = await Promise.all([memory.list(50), memory.stats()]);
      set({ nodes: list.memories, stats, results: [], query: '', loading: false, error: null });
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : 'failed to load memory' });
    }
  },

  search: async (query: string) => {
    set({ query, loading: true });
    if (!query.trim()) {
      await get().load();
      return;
    }
    try {
      const { results } = await memory.search(query, 40);
      set({ results, loading: false, error: null });
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : 'search failed' });
    }
  },

  consolidate: async () => {
    await memory.consolidate();
    await get().load();
  },

  remove: async (id: string) => {
    await memory.remove(id);
    set((s) => ({
      nodes: s.nodes.filter((n) => n.id !== id),
      results: s.results.filter((r) => r.node.id !== id),
    }));
  },
}));
