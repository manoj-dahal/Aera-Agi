import { NavLink } from 'react-router-dom';
import {
  Brain,
  FolderClosed,
  Images,
  LayoutGrid,
  Phone,
  Settings,
} from 'lucide-react';
import { cn } from '@utils/cn';

/**
 * Primary navigation (docs/04-DASHBOARD.md).
 *
 * Two grouped clusters, matching the specified layout: the working set on the
 * left and the device/system set on the right.
 */
const PRIMARY = [
  { to: '/dashboard', label: 'Dashboard', Icon: LayoutGrid },
  { to: '/macros', label: 'Macros', Icon: Brain },
  { to: '/apps', label: 'Apps', Icon: FolderClosed },
] as const;

const SECONDARY = [
  { to: '/gallery', label: 'Gallery', Icon: Images },
  { to: '/phone', label: 'Phone', Icon: Phone },
  { to: '/settings', label: 'Settings', Icon: Settings },
] as const;

function NavGroup({ items }: { items: readonly { to: string; label: string; Icon: typeof LayoutGrid }[] }) {
  return (
    <div className="flex items-center overflow-hidden rounded-[9px] border border-[var(--aera-line-strong)] bg-[var(--aera-bg-surface)]">
      {items.map(({ to, label, Icon }, index) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              'relative flex items-center gap-2 px-3.5 py-[7px] text-[13px] transition-all duration-200',
              index > 0 && 'border-l border-[var(--aera-line-default)]',
              isActive
                ? 'bg-[color-mix(in_srgb,var(--aera-accent-primary)_14%,transparent)] font-medium text-[var(--aera-text-primary)]'
                : 'text-[var(--aera-text-secondary)] hover:bg-[var(--aera-bg-hover)] hover:text-[var(--aera-text-primary)]',
            )
          }
          style={({ isActive }) =>
            isActive
              ? {
                  boxShadow:
                    'inset 0 -2px 0 var(--aera-accent-primary), 0 0 18px color-mix(in srgb, var(--aera-accent-primary) 30%, transparent)',
                }
              : undefined
          }
        >
          {({ isActive }) => (
            <>
              <Icon
                size={15}
                strokeWidth={isActive ? 2.2 : 1.9}
                className={cn('transition-all duration-200', isActive && 'scale-110')}
                style={
                  isActive
                    ? {
                        color: 'var(--aera-accent-primary)',
                        filter: 'drop-shadow(0 0 5px var(--aera-accent-primary))',
                      }
                    : undefined
                }
              />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </div>
  );
}

export function TopNav() {
  return (
    <header className="flex shrink-0 items-center gap-4 px-4 py-2.5">
      <NavLink
        to="/dashboard"
        className="rounded-[9px] border border-[var(--aera-line-strong)] bg-[var(--aera-bg-surface)] px-3.5 py-[7px] text-[13px] font-semibold tracking-[0.06em]"
      >
        <span className="text-gradient">AERA</span> Agent
      </NavLink>

      <div className="flex flex-1 items-center justify-center gap-8">
        <NavGroup items={PRIMARY} />
        <NavGroup items={SECONDARY} />
      </div>
    </header>
  );
}
