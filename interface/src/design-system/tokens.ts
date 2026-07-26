/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

/**
 * Design tokens: spacing, radii, shadows, motion and z-index.
 *
 * Single source of truth for layout rhythm across the interface.
 */

/** 4px base scale. */
export const spacing = {
  0: '0',
  px: '1px',
  0.5: '2px',
  1: '4px',
  1.5: '6px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
  20: '80px',
  24: '96px',
} as const;

export const radius = {
  none: '0',
  sm: '4px',
  md: '6px',
  lg: '9px',
  xl: '12px',
  '2xl': '16px',
  full: '9999px',
} as const;

export const shadow = {
  none: 'none',
  sm: '0 1px 2px rgba(0, 0, 0, 0.35)',
  md: '0 4px 12px rgba(0, 0, 0, 0.4)',
  lg: '0 10px 30px rgba(0, 0, 0, 0.5)',
  glow: '0 0 24px rgba(64, 232, 240, 0.45)',
  glowStrong: '0 0 40px rgba(124, 92, 255, 0.6)',
} as const;

export const motion = {
  duration: {
    instant: '0ms',
    fast: '120ms',
    normal: '200ms',
    slow: '320ms',
    slower: '500ms',
  },
  easing: {
    standard: 'cubic-bezier(0.4, 0, 0.2, 1)',
    decelerate: 'cubic-bezier(0, 0, 0.2, 1)',
    accelerate: 'cubic-bezier(0.4, 0, 1, 1)',
    spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  },
} as const;

/** Stacking order. Keep every overlay registered here to avoid z-index drift. */
export const zIndex = {
  base: 0,
  raised: 10,
  sticky: 20,
  dropdown: 30,
  overlay: 40,
  modal: 50,
  popover: 60,
  toast: 70,
  tooltip: 80,
  boot: 100,
} as const;

/** Fixed chrome dimensions used by the layouts. */
export const layout = {
  sidebarWidth: '208px',
  sidebarCollapsed: '60px',
  statusBarHeight: '38px',
  contextPaneWidth: '280px',
  maxContentWidth: '1440px',
} as const;

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;
