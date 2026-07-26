/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import { describe, expect, it } from 'vitest';
import { agentStatusColors, chartColors, emotionColors, memoryTypeColors, palette } from '@design/colors';
import { darkTheme, lightTheme, themes } from '@design/themes';
import { inset, mq, space } from '@design/spacing';
import { zIndex } from '@design/tokens';

const HEX = /^#[0-9a-fA-F]{6}$/;

describe('colour tokens', () => {
  it('exposes valid hex values', () => {
    expect(palette.bg.base).toMatch(HEX);
    expect(palette.accent.primary).toMatch(HEX);
    Object.values(memoryTypeColors).forEach((c) => expect(c).toMatch(HEX));
    Object.values(emotionColors).forEach((c) => expect(c).toMatch(HEX));
    chartColors.forEach((c) => expect(c).toMatch(HEX));
  });

  it('covers every agent status the backend can report', () => {
    // Mirrors AgentStatus in aera/agents/base.py
    for (const status of ['idle', 'starting', 'running', 'busy', 'stopped', 'error']) {
      expect(agentStatusColors).toHaveProperty(status);
    }
  });

  it('covers all six memory systems', () => {
    for (const type of ['short_term', 'long_term', 'working', 'semantic', 'episodic', 'procedural']) {
      expect(memoryTypeColors).toHaveProperty(type);
    }
  });

  it('keeps the accent in the brand cyan family', () => {
    // The logo mark is cyan; a blue or violet accent visibly clashes with it.
    const [r, g, b] = rgb(palette.accent.primary);
    expect(g).toBeGreaterThan(150);
    expect(b).toBeGreaterThan(150);
    expect(r).toBeLessThan(g * 0.6);
  });
});

/** Parse '#RRGGBB' into channel values. */
function rgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as [number, number, number];
}

/** WCAG 2.1 relative luminance. */
function luminance(hex: string): number {
  const [r, g, b] = rgb(hex).map((value) => {
    const c = value / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const first = luminance(a);
  const second = luminance(b);
  const hi = Math.max(first, second);
  const lo = Math.min(first, second);
  return (hi + 0.05) / (lo + 0.05);
}

describe('accent contrast', () => {
  // Brand cyan is a light colour. White text on it is 1.5:1, which is why
  // accentInk exists: filled accent surfaces need near-black ink instead.
  it('gives readable ink on an accent fill in every theme', () => {
    for (const theme of Object.values(themes)) {
      const { accentPrimary, accentSecondary, accentInk } = theme.colors;
      expect(contrast(accentInk, accentPrimary)).toBeGreaterThanOrEqual(4.5);
      // Buttons are a gradient, so the far end must be legible too.
      expect(contrast(accentInk, accentSecondary)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it('keeps accent text legible on the page background', () => {
    for (const theme of Object.values(themes)) {
      expect(contrast(theme.colors.accentPrimary, theme.colors.bgBase)).toBeGreaterThanOrEqual(4.5);
    }
  });
});

describe('themes', () => {
  it('defines the same keys across every theme', () => {
    const reference = Object.keys(darkTheme.colors).sort();
    for (const theme of Object.values(themes)) {
      expect(Object.keys(theme.colors).sort()).toEqual(reference);
    }
  });

  it('marks light theme as a light colour scheme', () => {
    expect(lightTheme.scheme).toBe('light');
    expect(darkTheme.scheme).toBe('dark');
  });
});

describe('spacing helpers', () => {
  it('resolves tokens', () => {
    expect(space(4)).toBe('16px');
    expect(inset(2, 4)).toBe('8px 16px');
    expect(mq('lg')).toBe('@media (min-width: 1024px)');
  });
});

describe('z-index scale', () => {
  it('orders overlays above content', () => {
    expect(zIndex.modal).toBeGreaterThan(zIndex.dropdown);
    expect(zIndex.toast).toBeGreaterThan(zIndex.modal);
    expect(zIndex.boot).toBeGreaterThan(zIndex.toast);
  });
});
