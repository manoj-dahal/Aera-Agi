import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar, StatusBar, ToastHost, useToast } from '@components/index';
import { useSystemStore, useWorkspaceStore } from '@store/index';
import { useMenuActions } from '@hooks/useMenuActions';

/**
 * The primary application shell: status bar, sidebar and routed content.
 * Owns the polling loops that keep system state fresh.
 */
export function MainLayout() {
  const { status, connected, startPolling } = useSystemStore();
  const { openDialog, canPickFolder, refresh } = useWorkspaceStore();
  const showToast = useToast((s) => s.show);

  // Native menu items dispatch into the router and stores.
  useMenuActions();

  useEffect(() => startPolling(), [startPolling]);
  useEffect(() => void refresh(), [refresh]);

  const handleOpenFolder = async () => {
    await openDialog();
    const project = useWorkspaceStore.getState().project;
    if (project) showToast(`Opened ${project.name}`, 'success');
  };

  return (
    <div className="flex h-screen flex-col">
      <StatusBar status={status} connected={connected} />
      <div className="flex min-h-0 flex-1">
        <Sidebar
          emotion={status?.hologram?.emotion}
          speaking={status?.hologram?.speaking}
          onOpenFolder={handleOpenFolder}
          canPickFolder={canPickFolder()}
        />
        <main className="flex min-w-0 flex-1">
          <Outlet />
        </main>
      </div>
      <ToastHost />
    </div>
  );
}
