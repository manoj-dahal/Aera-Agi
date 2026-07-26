/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

/**
 * AERA colour palette.
 *
 * Dark-first, matching the desktop shell (docs/13-SETTINGS.md: theme "dark").
 * Every value is also emitted as a CSS custom property in styles/globals.css,
 * so components can use either the token or the variable.
 */

export const palette = {
  /** Background layers, darkest to lightest. */
  bg: {
    base: '#07090F',
    raised: '#0B0F17',
    surface: '#111725',
    overlay: '#1A2233',
    hover: '#202A3E',
  },
  /** Borders and dividers. */
  line: {
    subtle: '#1A2233',
    default: '#202A3E',
    strong: '#2C3A56',
  },
  /** Foreground text. */
  text: {
    primary: '#E9EEF8',
    secondary: '#B4C0D6',
    muted: '#8494B2',
    disabled: '#5A6884',
    inverse: '#07090F',
  },
  /** Brand accents, sampled from the logo mark (assets/brand/). */
  accent: {
    primary: '#40E8F0',
    secondary: '#1E9BD4',
    glow: 'rgba(64, 232, 240, 0.55)',
  },
  /** Semantic states. */
  status: {
    success: '#34D399',
    warning: '#FBBF24',
    danger: '#F87171',
    info: '#40E8F0',
    neutral: '#8494B2',
  },
} as const;

/** Agent status indicator colours (docs/07-AGENTS.md). */
export const agentStatusColors = {
  idle: palette.status.neutral,
  starting: palette.status.warning,
  running: palette.status.success,
  busy: palette.accent.primary,
  stopped: palette.text.disabled,
  error: palette.status.danger,
} as const;

/** Memory type colours, used by the graph view and memory cards. */
export const memoryTypeColors = {
  short_term: '#FBBF24',
  long_term: '#34D399',
  working: '#40E8F0',
  semantic: '#7C5CFF',
  episodic: '#F472B6',
  procedural: '#22D3EE',
} as const;

/** Emotion colours shared by the voice engine and the hologram avatar. */
export const emotionColors = {
  neutral: '#8494B2',
  happy: '#34D399',
  excited: '#FBBF24',
  calm: '#22D3EE',
  concerned: '#FB923C',
  sad: '#60A5FA',
  serious: '#F87171',
  confident: '#A78BFA',
  curious: '#40E8F0',
  thinking: '#7C5CFF',
} as const;

/** Ordered series colours for charts. */
export const chartColors = [
  '#40E8F0',
  '#7C5CFF',
  '#34D399',
  '#FBBF24',
  '#F472B6',
  '#22D3EE',
  '#FB923C',
  '#A78BFA',
] as const;

export type AgentStatus = keyof typeof agentStatusColors;
export type MemoryType = keyof typeof memoryTypeColors;
export type Emotion = keyof typeof emotionColors;
