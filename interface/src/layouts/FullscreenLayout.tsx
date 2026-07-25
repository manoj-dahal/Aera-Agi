import type { ReactNode } from 'react';

/** Centred, chrome-free layout for onboarding and boot screens. */
export function FullscreenLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 bg-[radial-gradient(circle_at_50%_45%,#101827,var(--aera-bg-base)_70%)] p-8">
      {children}
    </div>
  );
}
