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
