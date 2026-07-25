import type { ReactNode } from 'react';
import { AvatarOrb } from '@components/hologram/AvatarOrb';

/**
 * Layout for authentication screens.
 *
 * Local desktop installs are single-user and unauthenticated by default; these
 * screens apply when AERA is deployed as a shared server (api.auth_enabled).
 */
export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex h-screen items-center justify-center bg-[radial-gradient(circle_at_50%_40%,#101827,var(--aera-bg-base)_70%)] p-8">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-3">
          <AvatarOrb size={44} />
          <div className="text-center">
            <h1 className="text-[18px] font-semibold tracking-[0.2em]">AERA</h1>
            <p className="mt-1 text-[13px] text-[var(--aera-text-muted)]">{title}</p>
            {subtitle && (
              <p className="mt-0.5 text-[11.5px] text-[var(--aera-text-disabled)]">{subtitle}</p>
            )}
          </div>
        </div>
        <div className="rounded-xl border border-[var(--aera-line-default)] bg-[var(--aera-bg-surface)] p-5">
          {children}
        </div>
      </div>
    </div>
  );
}
