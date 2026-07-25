/** System status, live events and connection state. */

import { create } from 'zustand';
import { system } from '@services/api';
import type { SystemEvent, SystemStatus, Telemetry } from '@services/types';

interface SystemState {
  status: SystemStatus | null;
  telemetry: Telemetry | null;
  events: SystemEvent[];
  connected: boolean;
  loading: boolean;
  error: string | null;

  refresh: () => Promise<void>;
  pollEvents: () => Promise<void>;
  startPolling: (intervalMs?: number) => () => void;
}

const MAX_EVENTS = 60;

export const useSystemStore = create<SystemState>((set, get) => ({
  status: null,
  telemetry: null,
  events: [],
  connected: false,
  loading: false,
  error: null,

  refresh: async () => {
    set({ loading: true });
    try {
      // Status and telemetry are independent: a telemetry failure must not
      // make the app look disconnected.
      const [status, telemetry] = await Promise.all([
        system.status(),
        system.telemetry().catch(() => null),
      ]);
      set({ status, telemetry, connected: status.ready, loading: false, error: null });
    } catch (error) {
      set({
        connected: false,
        loading: false,
        error: error instanceof Error ? error.message : 'unknown error',
      });
    }
  },

  pollEvents: async () => {
    try {
      const { events } = await system.events(30);
      const known = new Set(get().events.map((e) => e.id));
      const fresh = events.filter((e) => !known.has(e.id));
      if (fresh.length === 0) return;
      set((state) => ({
        events: [...fresh.reverse(), ...state.events].slice(0, MAX_EVENTS),
      }));
    } catch {
      /* transient: the next tick retries */
    }
  },

  startPolling: (intervalMs = 4000) => {
    const { refresh, pollEvents } = get();
    void refresh();
    void pollEvents();
    const statusTimer = setInterval(() => void refresh(), intervalMs * 2);
    const eventTimer = setInterval(() => void pollEvents(), intervalMs / 2);
    return () => {
      clearInterval(statusTimer);
      clearInterval(eventTimer);
    };
  },
}));
