import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const src = (p: string) => readFileSync(resolve(__dirname, '..', p), 'utf-8');

/** Guards for the animation and telemetry work from the design review. */

describe('AI Core animation states', () => {
  const sphere = src('components/hologram/ParticleSphere.tsx');

  it('defines a distinct profile for every state', () => {
    for (const state of [
      'idle', 'listening', 'thinking', 'speaking', 'processing', 'error', 'offline',
    ]) {
      expect(sphere).toContain(`${state}:`);
    }
  });

  it('gives each state different motion, not just a colour change', () => {
    // Extract the numeric spin values; they must not all be identical.
    const spins = [...sphere.matchAll(/spin: ([\d.]+)/g)].map((m) => Number(m[1]));
    expect(spins.length).toBeGreaterThanOrEqual(7);
    expect(new Set(spins).size).toBeGreaterThan(3);
  });

  it('renders orbiting energy rings', () => {
    expect(sphere).toContain('rings');
    expect(sphere).toContain('ctx.ellipse');
  });

  it('streams particles outward while active', () => {
    expect(sphere).toContain('stream');
    expect(sphere).toContain('streaming');
  });

  it('draws a voice waveform while speaking', () => {
    expect(sphere).toContain("stateRef.current === 'speaking'");
    expect(sphere).toContain('wave');
  });

  it('draws a scan line while processing', () => {
    expect(sphere).toContain('profile.scan');
    expect(sphere).toContain('sweep');
  });

  it('supports a progress arc for file processing', () => {
    expect(sphere).toContain('progressRef');
    expect(sphere).toContain('ctx.arc');
  });

  it('smooths transitions between states', () => {
    expect(sphere).toContain('smoothGlow');
    expect(sphere).toContain('smoothNoise');
  });

  it('respects reduced-motion preferences', () => {
    expect(sphere).toContain('prefers-reduced-motion');
  });
});

describe('Tap to Speak', () => {
  const tap = src('components/voice/TapToSpeak.tsx');

  it('renders a waveform while listening', () => {
    expect(tap).toContain('BARS');
    expect(tap).toContain('aera-wave');
  });

  it('shows pulse rings while active', () => {
    expect(tap).toContain('animate-ping');
  });

  it('distinguishes priming from listening', () => {
    expect(tap).toContain('Recalling');
    expect(tap).toContain('Listening');
  });
});

describe('PC information panel', () => {
  const panel = src('components/widgets/SystemInfoPanel.tsx');

  it('reports every metric named in the review', () => {
    for (const metric of ['CPU', 'RAM', 'GPU', 'VRAM', 'Disk', 'Net', 'Temp', 'Model', 'Agents']) {
      expect(panel).toContain(metric);
    }
  });

  it('shows a dash rather than a fake zero for missing metrics', () => {
    expect(panel).toContain("'—'");
    expect(panel).toContain('== null');
  });

  it('colours meters by pressure', () => {
    expect(panel).toContain('var(--aera-danger)');
    expect(panel).toContain('var(--aera-warning)');
  });
});

describe('transcript drop indicator', () => {
  const panel = src('components/voice/TranscriptPanel.tsx');

  it('shows a glowing border and Drop Here on drag', () => {
    expect(panel).toContain('Drop Here');
    expect(panel).toContain('boxShadow');
  });

  it('names the agent that will process the file', () => {
    expect(panel).toContain('activeAgent');
    expect(panel).toContain('agent processing');
  });

  it('keeps the watermark near-invisible at rest', () => {
    expect(panel).toContain('opacity-[0.06]');
  });
});

describe('navigation active state', () => {
  const nav = src('components/navigation/TopNav.tsx');

  it('glows and brightens the active page', () => {
    expect(nav).toContain('boxShadow');
    expect(nav).toContain('drop-shadow');
    expect(nav).toContain('scale-110');
  });
});

describe('ambient panel fills the empty centre', () => {
  const ambient = src('components/widgets/AmbientPanel.tsx');
  const dashboard = src('pages/dashboard/Dashboard.tsx');

  it('surfaces tasks, memory and project', () => {
    expect(ambient).toContain('Tasks');
    expect(ambient).toContain('Memory');
    expect(ambient).toContain('Project');
  });

  it('shows memory recall progress', () => {
    expect(ambient).toContain('recall');
    expect(ambient).toContain('Recalling context');
  });

  it('disappears once a conversation starts', () => {
    expect(dashboard).toContain('messages.length === 0 && (');
  });
});

describe('dashboard visual hierarchy', () => {
  const dashboard = src('pages/dashboard/Dashboard.tsx');

  it('places the hologram above Tap to Speak', () => {
    const body = dashboard.slice(dashboard.indexOf('return ('));
    expect(body.indexOf('<ParticleSphere')).toBeLessThan(body.indexOf('<TapToSpeak'));
  });

  it('routes dropped files to a matching agent', () => {
    expect(dashboard).toContain('agentForFile');
    for (const agent of ['vision', 'audio', 'document', 'coding']) {
      expect(dashboard).toContain(`'${agent}'`);
    }
  });
});
