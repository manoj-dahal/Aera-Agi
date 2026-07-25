/** Active project, file search and preview state. */

import { create } from 'zustand';
import { workspace } from '@services/api';
import { detectHost } from '@services/transport';
import type { FileContent, FileMatch, ProjectSummary } from '@services/types';

interface WorkspaceState {
  project: ProjectSummary | null;
  results: FileMatch[];
  selected: FileContent | null;
  query: string;
  loading: boolean;
  error: string | null;

  refresh: () => Promise<void>;
  openDialog: () => Promise<void>;
  open: (path: string) => Promise<void>;
  reindex: () => Promise<void>;
  search: (query: string) => Promise<void>;
  select: (path: string) => Promise<void>;
  canPickFolder: () => boolean;
}

function asProject(value: ProjectSummary | Record<string, never> | null): ProjectSummary | null {
  return value && 'name' in value ? (value as ProjectSummary) : null;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  project: null,
  results: [],
  selected: null,
  query: '',
  loading: false,
  error: null,

  canPickFolder: () => detectHost() === 'desktop',

  refresh: async () => {
    try {
      set({ project: asProject(await workspace.summary()), error: null });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'failed to load workspace' });
    }
  },

  openDialog: async () => {
    set({ loading: true, error: null });
    try {
      const project = await workspace.openDialog();
      set({ project: project ?? get().project, loading: false });
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : 'dialog failed' });
    }
  },

  open: async (path: string) => {
    set({ loading: true, error: null });
    try {
      set({ project: await workspace.open(path), loading: false, results: [], selected: null });
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : 'could not open folder' });
    }
  },

  reindex: async () => {
    const current = get().project;
    if (!current) return;
    set({ loading: true });
    try {
      await workspace.open(current.root);
      await get().refresh();
    } finally {
      set({ loading: false });
    }
  },

  search: async (query: string) => {
    set({ query });
    if (!query.trim()) {
      set({ results: [] });
      return;
    }
    try {
      const { results } = await workspace.search(query, 40);
      set({ results, error: null });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'search failed' });
    }
  },

  select: async (path: string) => {
    try {
      set({ selected: await workspace.readFile(path), error: null });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'could not read file' });
    }
  },
}));
