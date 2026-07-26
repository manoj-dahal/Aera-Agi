/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import { useEffect, useMemo } from 'react';
import { Outlet } from 'react-router-dom';
import { TopNav } from '@components/navigation/TopNav';
import { StatusFooter } from '@components/widgets/StatusFooter';
import { ToastHost } from '@components/notifications/Toast';
import { useMenuActions } from '@hooks/useMenuActions';
import { useSystemStore, useWorkspaceStore } from '@store/index';

/**
 * Application shell (docs/04-DASHBOARD.md).
 *
 * Grouped top navigation, routed content, and a bottom status bar. Owns the
 * polling loops that keep system state fresh.
 */
export function MainLayout() {
  const { status, connected, startPolling } = useSystemStore();
  const refreshWorkspace = useWorkspaceStore((s) => s.refresh);

  // Native menu items dispatch into the router and stores.
  useMenuActions();

  useEffect(() => startPolling(), [startPolling]);
  useEffect(() => void refreshWorkspace(), [refreshWorkspace]);

  const activeAgent = useMemo(
    () => (status?.agents?.running ? 'core' : undefined),
    [status?.agents?.running],
  );

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TopNav />
      <main className="flex min-h-0 flex-1">
        <Outlet />
      </main>
      <StatusFooter status={status} connected={connected} activeAgent={activeAgent} />
      <ToastHost />
    </div>
  );
}
