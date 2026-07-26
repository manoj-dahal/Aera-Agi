/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

/**
 * The AERA mark.
 *
 * An eye inside a neon ring, ringed by signal arcs: perception plus
 * listening. Previously this was an inline SVG string pasted into three
 * separate hand-written shells, where it drifted out of sync. It is now one
 * component, and `tests/test_brand.py` asserts its geometry still matches
 * `tools/brand/generate.py`, which renders the PNG icon set.
 *
 * Coordinates are in a 0-100 viewBox, so `size` is purely presentational.
 */

import { cn } from '@utils/cn';

/** Signal arcs, outermost first. Geometry mirrors VERTICAL/HORIZONTAL_ARCS. */
const ARCS = [
  'M38.76 33.95A19.60 19.60 0 0 1 61.24 33.95',
  'M61.24 66.05A19.60 19.60 0 0 1 38.76 66.05',
  'M41.93 37.57A14.82 14.82 0 0 1 58.07 37.57',
  'M58.07 62.43A14.82 14.82 0 0 1 41.93 62.43',
  'M26.44 64.16A27.48 27.48 0 0 1 26.44 35.84',
  'M73.56 35.84A27.48 27.48 0 0 1 73.56 64.16',
  'M31.64 59.76A20.79 20.79 0 0 1 31.64 40.24',
  'M68.36 40.24A20.79 20.79 0 0 1 68.36 59.76',
] as const;

/** The eye: a vesica built from two circular arcs, so the tips stay pointed. */
const EYE = 'M32.31 50A22.48 22.48 0 0 1 67.69 50A22.48 22.48 0 0 1 32.31 50Z';

export interface MarkProps {
  size?: number;
  /**
   * Signal arcs become illegible when the mark is small, matching the
   * threshold `make_icon()` uses for the raster icons.
   */
  arcs?: boolean;
  /** Adds a soft outer glow, for hero placements. */
  glow?: boolean;
  className?: string;
  title?: string;
}

export function Mark({
  size = 24,
  arcs,
  glow = false,
  className,
  title = 'AERA',
}: MarkProps) {
  const showArcs = arcs ?? size >= 28;

  return (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      fill="none"
      stroke="var(--aera-accent-primary)"
      strokeWidth={1.48}
      strokeLinecap="round"
      role="img"
      aria-label={title}
      className={cn('shrink-0', className)}
      style={glow ? { filter: 'drop-shadow(0 0 6px var(--aera-accent-primary))' } : undefined}
    >
      <circle cx="50" cy="50" r="47.80" strokeWidth={1.72} />
      {showArcs && ARCS.map((d) => <path key={d} d={d} />)}
      <path d={EYE} />
      <circle cx="50" cy="50" r="7.98" />
      {/* The pupil is the one white element; everything else is accent. */}
      <circle cx="50" cy="50" r="3.15" fill="#FFFFFF" stroke="none" />
    </svg>
  );
}
