/** User-supplied avatar models. */

import { create } from 'zustand';
import { avatars } from '@services/api';
import type { AvatarModelInfo } from '@services/types';

interface AvatarState {
  models: AvatarModelInfo[];
  active: AvatarModelInfo | null;
  loading: boolean;
  error: string | null;
  /** Name of the file currently uploading, or null when idle. */
  uploading: string | null;
  /** 0..1 for the file in flight. */
  progress: number;

  load: () => Promise<void>;
  scan: () => Promise<void>;
  select: (modelId: string) => Promise<void>;
  upload: (file: File) => Promise<AvatarModelInfo | null>;
  /** Desktop: copy files from disk without going through the browser. */
  importNative: (paths: string[]) => Promise<boolean>;
  remove: (modelId: string) => Promise<void>;
  /** Clear the selection so the particle orb renders instead. */
  useOrb: () => void;
}

export const useAvatarStore = create<AvatarState>((set, get) => ({
  models: [],
  active: null,
  loading: false,
  error: null,
  uploading: null,
  progress: 0,

  load: async () => {
    set({ loading: true });
    try {
      const [list, current] = await Promise.all([
        avatars.list(),
        avatars.active().catch(() => ({ active: null })),
      ]);
      set({ models: list.avatars, active: current.active, loading: false, error: null });
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : 'could not load avatars',
      });
    }
  },

  scan: async () => {
    set({ loading: true });
    try {
      const { avatars: found } = await avatars.scan();
      set({ models: found, loading: false, error: null });
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : 'scan failed' });
    }
  },

  select: async (modelId) => {
    try {
      set({ active: await avatars.setActive(modelId), error: null });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'could not select model' });
    }
  },

  upload: async (file) => {
    set({ uploading: file.name, progress: 0, error: null });
    try {
      const result = await avatars.upload(file, (fraction) => set({ progress: fraction }));
      await get().load();
      set({ uploading: null, progress: 0 });
      // An archive may hold several models; report the first for the toast.
      return result.model ?? result.models?.[0] ?? null;
    } catch (error) {
      set({
        uploading: null,
        progress: 0,
        error: error instanceof Error ? error.message : 'upload failed',
      });
      return null;
    }
  },

  importNative: async (paths) => {
    set({ loading: true, error: null });
    try {
      await avatars.importNative(paths);
      await get().load();
      set({ loading: false });
      return true;
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : 'import failed' });
      return false;
    }
  },

  remove: async (modelId) => {
    await avatars.remove(modelId).catch(() => {});
    if (get().active?.id === modelId) set({ active: null });
    await get().load();
  },

  useOrb: () => set({ active: null }),
}));
