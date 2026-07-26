/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

/**
 * Spacing re-exports.
 *
 * The canonical scale lives in tokens.ts; this module exposes it under the
 * name the interface structure expects, plus a few helpers.
 */

import { breakpoints, layout, radius, spacing } from './tokens';

export { spacing, radius, layout, breakpoints };

export type SpacingKey = keyof typeof spacing;

/** Resolve a spacing token to its px value. */
export function space(key: SpacingKey): string {
  return spacing[key];
}

/** Build a CSS shorthand from spacing tokens: inset(2, 4) -> "8px 16px". */
export function inset(...keys: SpacingKey[]): string {
  return keys.map((k) => spacing[k]).join(' ');
}

/** Media query helper: mq('lg') -> "@media (min-width: 1024px)". */
export function mq(key: keyof typeof breakpoints): string {
  return `@media (min-width: ${breakpoints[key]})`;
}
