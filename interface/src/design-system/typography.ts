/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

/** Type scale and font stacks. */

export const fontFamily = {
  sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif',
  mono: 'ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace',
} as const;

export const fontSize = {
  '2xs': '9.5px',
  xs: '10.5px',
  sm: '11.5px',
  base: '13px',
  md: '13.5px',
  lg: '15px',
  xl: '17px',
  '2xl': '20px',
  '3xl': '26px',
  '4xl': '34px',
} as const;

export const fontWeight = {
  normal: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const;

export const lineHeight = {
  none: 1,
  tight: 1.25,
  snug: 1.4,
  normal: 1.6,
  relaxed: 1.75,
} as const;

export const letterSpacing = {
  tighter: '-0.02em',
  normal: '0',
  wide: '0.05em',
  wider: '0.11em',
  widest: '0.16em',
} as const;

/** Named text styles used across pages. */
export const textStyles = {
  /** Small uppercase section heading. */
  sectionLabel: {
    fontSize: fontSize.xs,
    fontWeight: fontWeight.medium,
    letterSpacing: letterSpacing.wider,
    textTransform: 'uppercase' as const,
  },
  pageTitle: {
    fontSize: fontSize['2xl'],
    fontWeight: fontWeight.semibold,
    lineHeight: lineHeight.tight,
  },
  cardTitle: {
    fontSize: fontSize.base,
    fontWeight: fontWeight.semibold,
  },
  body: {
    fontSize: fontSize.md,
    lineHeight: lineHeight.normal,
  },
  caption: {
    fontSize: fontSize.sm,
    lineHeight: lineHeight.snug,
  },
  code: {
    fontFamily: fontFamily.mono,
    fontSize: fontSize.sm,
  },
} as const;
