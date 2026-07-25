import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const src = (p: string) => readFileSync(resolve(__dirname, '..', p), 'utf-8');

/**
 * Structural checks against the specified dashboard layout
 * (docs/04-DASHBOARD.md). These guard the arrangement, not the pixels.
 */
describe('dashboard layout', () => {
  const dashboard = src('pages/dashboard/Dashboard.tsx');

  it('renders the three specified columns', () => {
    expect(dashboard).toContain('HologramBadge');      // left
    expect(dashboard).toContain('SystemInfoPanel');    // left: live PC metrics
    expect(dashboard).toContain('WorkspacePanel');     // left
    expect(dashboard).toContain('ParticleSphere');     // centre
    expect(dashboard).toContain('TapToSpeak');         // centre
    expect(dashboard).toContain('TranscriptPanel');    // right
  });

  it('orders the columns left, centre, right', () => {
    // Compare positions in the JSX body only; the import block lists these
    // components alphabetically and would give a false reading.
    const body = dashboard.slice(dashboard.indexOf('return ('));
    const left = body.indexOf('WorkspacePanel');
    const centre = body.indexOf('ParticleSphere');
    const right = body.indexOf('TranscriptPanel');
    expect(left).toBeGreaterThan(-1);
    expect(left).toBeLessThan(centre);
    expect(centre).toBeLessThan(right);
  });

  it('drives the hologram from the conversation lifecycle', () => {
    for (const state of ['offline', 'listening', 'speaking', 'thinking', 'idle']) {
      expect(dashboard).toContain(`'${state}'`);
    }
  });

  it('supports drag and drop, which the spec confines to the dashboard', () => {
    expect(dashboard).toContain('onDropFiles');
    expect(src('components/voice/TranscriptPanel.tsx')).toContain('onDrop');
  });
});

describe('top navigation', () => {
  const nav = src('components/navigation/TopNav.tsx');

  it('lists the six specified destinations in order', () => {
    const labels = [...nav.matchAll(/label: '([^']+)'/g)].map((m) => m[1]);
    expect(labels).toEqual(['Dashboard', 'Macros', 'Apps', 'Gallery', 'Phone', 'Settings']);
  });

  it('splits them into two clusters', () => {
    expect(nav).toContain('PRIMARY');
    expect(nav).toContain('SECONDARY');
  });

  it('shows the AERA Agent badge', () => {
    expect(nav).toContain('Agent');
  });
});

describe('transcript panel', () => {
  const panel = src('components/voice/TranscriptPanel.tsx');

  it('shows a watermark that reacts to dragging', () => {
    expect(panel).toContain('AERA');
    expect(panel).toContain('dragging');
    expect(panel).toContain('Drop Here');
    expect(panel).toContain('activeAgent'); // names the agent that will process it
  });

  it('escapes model output rather than injecting raw HTML', () => {
    expect(panel).toContain('renderMarkdown');
  });
});

describe('status footer', () => {
  it('reports the metrics named in the spec', () => {
    const footer = src('components/widgets/StatusFooter.tsx');
    for (const label of ['Model', 'Agent', 'Memory', 'Uptime']) {
      expect(footer).toContain(`'${label}'`);
    }
  });
});

describe('particle sphere', () => {
  const sphere = src('components/hologram/ParticleSphere.tsx');

  it('defines a profile for every avatar state in the spec', () => {
    for (const state of [
      'idle', 'listening', 'thinking', 'speaking', 'processing', 'error', 'offline',
    ]) {
      expect(sphere).toContain(`${state}:`);
    }
  });

  it('respects reduced-motion preferences', () => {
    expect(sphere).toContain('prefers-reduced-motion');
  });
});

describe('macros page', () => {
  it('lists all six memory systems', () => {
    const macros = src('pages/macros/MacrosHome.tsx');
    for (const system of [
      'short_term', 'long_term', 'working', 'semantic', 'episodic', 'procedural',
    ]) {
      expect(macros).toContain(system);
    }
  });
});
