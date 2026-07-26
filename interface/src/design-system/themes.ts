/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

/**
 * Theme definitions.
 *
 * Dark is the default (docs/13-SETTINGS.md). Themes are applied by writing CSS
 * custom properties onto <html>, so switching is instant and framework-free.
 */

import { palette } from './colors';

export interface Theme {
  name: string;
  label: string;
  scheme: 'dark' | 'light';
  colors: {
    bgBase: string;
    bgRaised: string;
    bgSurface: string;
    bgOverlay: string;
    bgHover: string;
    lineSubtle: string;
    lineDefault: string;
    lineStrong: string;
    textPrimary: string;
    textSecondary: string;
    textMuted: string;
    textDisabled: string;
    accentPrimary: string;
    accentSecondary: string;
    /** Text colour for content sitting on an accent fill. */
    accentInk: string;
    success: string;
    warning: string;
    danger: string;
  };
}

export const darkTheme: Theme = {
  name: 'dark',
  label: 'Dark',
  scheme: 'dark',
  colors: {
    bgBase: palette.bg.base,
    bgRaised: palette.bg.raised,
    bgSurface: palette.bg.surface,
    bgOverlay: palette.bg.overlay,
    bgHover: palette.bg.hover,
    lineSubtle: palette.line.subtle,
    lineDefault: palette.line.default,
    lineStrong: palette.line.strong,
    textPrimary: palette.text.primary,
    textSecondary: palette.text.secondary,
    textMuted: palette.text.muted,
    textDisabled: palette.text.disabled,
    accentPrimary: palette.accent.primary,
    accentSecondary: palette.accent.secondary,
    // Brand cyan is light: white on it is 1.5:1, near-black is 13.3:1.
    accentInk: '#04121A',
    success: palette.status.success,
    warning: palette.status.warning,
    danger: palette.status.danger,
  },
};

/** Deeper, lower-contrast variant for OLED displays and night use. */
export const midnightTheme: Theme = {
  ...darkTheme,
  name: 'midnight',
  label: 'Midnight',
  colors: {
    ...darkTheme.colors,
    bgBase: '#000000',
    bgRaised: '#05070C',
    bgSurface: '#0A0E16',
    bgOverlay: '#121826',
  },
};

export const lightTheme: Theme = {
  name: 'light',
  label: 'Light',
  scheme: 'light',
  colors: {
    bgBase: '#F7F9FC',
    bgRaised: '#FFFFFF',
    bgSurface: '#FFFFFF',
    bgOverlay: '#EFF3F9',
    bgHover: '#E4EAF3',
    lineSubtle: '#E4EAF3',
    lineDefault: '#D3DCE9',
    lineStrong: '#B9C6D8',
    textPrimary: '#0D1421',
    textSecondary: '#33415C',
    textMuted: '#5A6884',
    textDisabled: '#98A5BC',
    accentPrimary: '#0A7A8C',
    accentSecondary: '#0B6FD4',
    // The light theme darkens the accent for contrast on white, so its
    // fills need white ink rather than the dark ink the cyan uses.
    accentInk: '#FFFFFF',
    success: '#0E9F6E',
    warning: '#B45309',
    danger: '#DC2626',
  },
};

export const themes = {
  dark: darkTheme,
  midnight: midnightTheme,
  light: lightTheme,
} as const;

export type ThemeName = keyof typeof themes;

/** camelCase token -> CSS custom property name. */
export function cssVarName(key: string): string {
  return `--aera-${key.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}`;
}

/** Apply a theme by setting custom properties on the document root. */
export function applyTheme(name: ThemeName): Theme {
  const theme = themes[name] ?? darkTheme;
  if (typeof document === 'undefined') return theme;

  const root = document.documentElement;
  for (const [key, value] of Object.entries(theme.colors)) {
    root.style.setProperty(cssVarName(key), value);
  }
  root.dataset.theme = theme.name;
  root.classList.toggle('dark', theme.scheme === 'dark');
  root.style.colorScheme = theme.scheme;
  return theme;
}
