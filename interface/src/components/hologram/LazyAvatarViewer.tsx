import { Suspense, lazy } from 'react';
import type { AvatarViewerProps } from './AvatarViewer';

/**
 * Code-split wrapper around the three.js viewer.
 *
 * three.js is ~630 kB. Importing it directly pulls that into the shared chunk
 * for every user, including those who never load a model. Deferring it means
 * the orb path stays light and the renderer downloads only on first use.
 */
const AvatarViewer = lazy(() =>
  import('./AvatarViewer').then((module) => ({ default: module.AvatarViewer })),
);

export function LazyAvatarViewer(props: AvatarViewerProps) {
  const { size = 320 } = props;
  return (
    <Suspense
      fallback={
        <div
          style={{ width: size, height: size }}
          className="flex items-center justify-center text-[11.5px] text-[var(--aera-text-muted)]"
        >
          Loading renderer…
        </div>
      }
    >
      <AvatarViewer {...props} />
    </Suspense>
  );
}
