import { NavLink } from 'react-router-dom';
import {
  Activity, Bot, Boxes, Brain, Cpu, FolderTree, Puzzle, Settings, Shield,
  Sparkles, TerminalSquare, Workflow,
} from 'lucide-react';
import { cn } from '@utils/cn';
import { AvatarOrb } from '@components/hologram/AvatarOrb';

const NAV = [
  { to: '/dashboard', label: 'Dashboard', Icon: Activity },
  { to: '/memory', label: 'Memory', Icon: Brain },
  { to: '/agents', label: 'Agents', Icon: Bot },
  { to: '/workspace', label: 'Workspace', Icon: FolderTree },
  { to: '/models', label: 'Models', Icon: Cpu },
  { to: '/automation', label: 'Automation', Icon: Workflow },
  { to: '/hologram', label: 'Hologram', Icon: Sparkles },
  { to: '/terminal', label: 'Terminal', Icon: TerminalSquare },
  { to: '/docker', label: 'Docker', Icon: Boxes },
  { to: '/plugins', label: 'Plugins', Icon: Puzzle },
  { to: '/security', label: 'Security', Icon: Shield },
  { to: '/settings', label: 'Settings', Icon: Settings },
] as const;

export interface SidebarProps {
  emotion?: string;
  speaking?: boolean;
  onOpenFolder?: () => void;
  canPickFolder?: boolean;
}

export function Sidebar({ emotion, speaking, onOpenFolder, canPickFolder }: SidebarProps) {
  return (
    <nav className="flex w-[208px] shrink-0 flex-col gap-0.5 border-r border-[var(--aera-line-default)] bg-[var(--aera-bg-raised)] p-2.5">
      {NAV.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2.5 rounded-[7px] px-3 py-2 text-[13px] transition-colors',
              isActive
                ? 'bg-[var(--aera-bg-overlay)] font-medium text-[var(--aera-text-primary)]'
                : 'text-[var(--aera-text-muted)] hover:bg-[var(--aera-bg-surface)] hover:text-[var(--aera-text-primary)]',
            )
          }
        >
          <Icon size={14} strokeWidth={1.8} />
          {label}
        </NavLink>
      ))}

      <div className="flex-1" />

      {canPickFolder && (
        <button
          onClick={onOpenFolder}
          className="my-2 rounded-lg border border-dashed border-[var(--aera-line-default)] px-3 py-2.5 text-[12px] text-[var(--aera-text-muted)] transition-colors hover:border-[var(--aera-accent-primary)] hover:text-[var(--aera-text-primary)]"
        >
          Open Local Folder…
        </button>
      )}

      <div className="py-3">
        <AvatarOrb emotion={emotion} speaking={speaking} showLabel size={36} />
      </div>
    </nav>
  );
}
