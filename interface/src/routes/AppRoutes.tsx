import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { MainLayout } from '@layouts/MainLayout';
import { LoadingState } from '@components/widgets/EmptyState';

// Route-level code splitting keeps the initial desktop paint fast.
const Dashboard = lazy(() => import('@pages/dashboard/Dashboard'));
const MemoryHome = lazy(() => import('@pages/memory/MemoryHome'));
const AgentsHome = lazy(() => import('@pages/agents/AgentsHome'));
const WorkspaceHome = lazy(() => import('@pages/workspace/WorkspaceHome'));
const AIModels = lazy(() => import('@pages/models/AIModels'));
const AutomationHome = lazy(() => import('@pages/automation/AutomationHome'));
const AvatarHome = lazy(() => import('@pages/hologram/AvatarHome'));
const TerminalHome = lazy(() => import('@pages/terminal/TerminalHome'));
const DockerHome = lazy(() => import('@pages/docker/DockerHome'));
const PluginHome = lazy(() => import('@pages/plugins/PluginHome'));
const SecurityHome = lazy(() => import('@pages/security/SecurityHome'));
const SettingsHome = lazy(() => import('@pages/settings/SettingsHome'));
const SystemInfo = lazy(() => import('@pages/system/SystemInfo'));

export function AppRoutes() {
  return (
    <Suspense fallback={<LoadingState />}>
      <Routes>
        <Route element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/memory" element={<MemoryHome />} />
          <Route path="/agents" element={<AgentsHome />} />
          <Route path="/workspace" element={<WorkspaceHome />} />
          <Route path="/models" element={<AIModels />} />
          <Route path="/automation" element={<AutomationHome />} />
          <Route path="/hologram" element={<AvatarHome />} />
          <Route path="/terminal" element={<TerminalHome />} />
          <Route path="/docker" element={<DockerHome />} />
          <Route path="/plugins" element={<PluginHome />} />
          <Route path="/security" element={<SecurityHome />} />
          <Route path="/settings" element={<SettingsHome />} />
          <Route path="/system" element={<SystemInfo />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

export default AppRoutes;
