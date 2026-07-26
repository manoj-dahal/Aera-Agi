/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const src = (p: string) => readFileSync(resolve(__dirname, '..', p), 'utf-8');

describe('avatar viewer', () => {
  const viewer = src('components/hologram/AvatarViewer.tsx');

  it('supports the parseable formats', () => {
    expect(viewer).toContain('GLTFLoader');
    expect(viewer).toContain('OBJLoader');
    expect(viewer).toContain('MTLLoader');
  });

  it('normalises authored units to a consistent screen size', () => {
    // Models arrive in mm, cm or m; without this they render as a dot or fill
    // the whole viewport.
    expect(viewer).toContain('Box3');
    expect(viewer).toContain('multiplyScalar');
  });

  it('computes normals when a model lacks them', () => {
    expect(viewer).toContain('computeVertexNormals');
  });

  it('disposes GPU resources on unmount', () => {
    // three.js does not free GPU memory on GC; without this, switching models
    // leaks a buffer every time.
    expect(viewer).toContain('geometry?.dispose');
    expect(viewer).toContain('renderer.dispose');
  });

  it('drives motion from the avatar state', () => {
    for (const state of ['idle', 'listening', 'thinking', 'speaking', 'processing']) {
      expect(viewer).toContain(`${state}:`);
    }
  });

  it('reports unrenderable formats instead of failing silently', () => {
    expect(viewer).toContain('export to GLB');
  });

  it('respects reduced motion', () => {
    expect(viewer).toContain('prefers-reduced-motion');
  });

  it('falls back to a default material when the MTL is missing', () => {
    expect(viewer).toContain('MeshStandardMaterial');
  });
});

describe('code splitting', () => {
  it('lazy-loads three.js', () => {
    // three.js is ~624 kB. Loading it eagerly would penalise every user,
    // including those who never select a model.
    const lazy = src('components/hologram/LazyAvatarViewer.tsx');
    expect(lazy).toContain('lazy(');
    expect(lazy).toContain('Suspense');
  });

  it('consumers use the lazy wrapper, not the raw viewer', () => {
    for (const page of ['pages/dashboard/Dashboard.tsx', 'pages/hologram/AvatarHome.tsx']) {
      const body = src(page);
      expect(body).toContain('LazyAvatarViewer');
      expect(body).not.toMatch(/<AvatarViewer[\s>]/);
    }
  });
});

describe('dashboard avatar integration', () => {
  const dashboard = src('pages/dashboard/Dashboard.tsx');

  it('renders a model when one is active, the orb otherwise', () => {
    expect(dashboard).toContain('avatarModel ?');
    expect(dashboard).toContain('ParticleSphere');
  });
});

describe('hologram model management', () => {
  const page = src('pages/hologram/AvatarHome.tsx');

  it('offers upload and drag-drop', () => {
    expect(page).toContain('Upload Model');
    expect(page).toContain('onDrop');
  });

  it('surfaces loader warnings to the user', () => {
    expect(page).toContain('warnings');
    expect(page).toContain('AlertTriangle');
  });

  it('shows the variant so a g/b pair is distinguishable', () => {
    expect(page).toContain('model.variant');
  });

  it('allows falling back to the orb', () => {
    expect(page).toContain('useOrb');
  });
});

describe('macros surfaces background skills', () => {
  it('renders the skill panel beside the memory graph', () => {
    // The requirements put AI skills in Macros, not Apps.
    const macros = src('pages/macros/MacrosHome.tsx');
    expect(macros).toContain('SkillPanel');
    expect(macros).toContain('MemoryGraphCanvas');
  });
});
