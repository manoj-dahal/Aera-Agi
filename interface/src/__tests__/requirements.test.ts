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

/**
 * Guards for the explicit corrections in docs/ui-page/conversation.txt.
 * Each test quotes the instruction it protects.
 */

describe('Settings: "reduce the number of buttons to maximum three"', () => {
  const settings = src('pages/settings/SettingsHome.tsx');

  it('defines exactly three top-level sections', () => {
    const ids = [...settings.matchAll(/id: '(ai|voice|system)'/g)].map((m) => m[1]);
    expect(ids).toEqual(['ai', 'voice', 'system']);
  });

  it('does not promote subsystem pages to the top level', () => {
    // The landing view must render SECTIONS only.
    const landing = settings.slice(
      settings.indexOf('if (section === null)'),
      settings.indexOf('const back ='),
    );
    expect(landing).toContain('SECTIONS.map');
    expect(landing).not.toContain('/memory');
    expect(landing).not.toContain('/agents');
  });

  it('nests advanced pages inside a section', () => {
    expect(settings).toContain('NestedLink');
  });
});

describe('Settings: "remove plugin updates and plugin connection, keep them only in Apps"', () => {
  it('does not manage plugins in Settings', () => {
    const settings = src('pages/settings/SettingsHome.tsx');
    expect(settings).not.toContain('/plugins');
    expect(settings.toLowerCase()).not.toContain('plugin manager');
  });

  it('manages plugins in Apps', () => {
    const apps = src('pages/apps/AppsHome.tsx');
    expect(apps).toContain('Plugin Manager');
    expect(apps).toContain("category: 'plugins'");
  });
});

describe('AI settings: "if no local LLM is running, the button should not appear"', () => {
  const settings = src('pages/settings/SettingsHome.tsx');

  it('renders a status line rather than a connect button', () => {
    const card = settings.slice(settings.indexOf('function LocalModelCard'));
    expect(card).toContain('Not connected');
    expect(card).toContain('Connected');
    // No actionable connect control in either branch.
    expect(card).not.toContain('<Button');
  });
});

describe('Apps: default tools and the three-dot update menu', () => {
  const apps = src('pages/apps/AppsHome.tsx');

  it('ships Terminal and Git as defaults', () => {
    expect(apps).toContain("id: 'terminal'");
    expect(apps).toContain("id: 'git'");
    expect(apps).toContain("category: 'default'");
  });

  it('offers Connect Application', () => {
    expect(apps).toContain('Connect Application');
  });

  it('carries the update actions in the three-dot menu', () => {
    for (const action of ['Check for Updates', 'Update Now', 'Update All', 'Auto Update', 'Rescan']) {
      expect(apps).toContain(action);
    }
  });

  it('keeps AI skills out of Apps — they live in Macros', () => {
    expect(apps).not.toContain('Memory Graph');
    expect(apps).toContain('visualised in Macros');
  });
});

describe('Gallery: "add a small browsing feature, opened only with a button"', () => {
  const gallery = src('pages/gallery/GalleryHome.tsx');

  it('hides the browser behind a Browse toggle', () => {
    expect(gallery).toContain('browserOpen');
    expect(gallery).toContain('Browse');
  });

  it('targets online downloads, not local browsing', () => {
    expect(gallery).toContain('Download from the web');
    expect(gallery).toContain('https://');
  });
});

describe('Phone: "drag and drop should be removed from the Phone page"', () => {
  it('has no drop handling', () => {
    const phone = src('pages/phone/PhoneHome.tsx');
    expect(phone).not.toContain('onDrop');
    expect(phone).not.toContain('dataTransfer');
  });

  it('keeps drag and drop on the transcript watermark', () => {
    const transcript = src('components/voice/TranscriptPanel.tsx');
    expect(transcript).toContain('onDrop');
    expect(transcript).toContain('dragging');
  });
});

describe('Tap to Speak: "trigger a tap-to-memory workflow in the background first"', () => {
  const dashboard = src('pages/dashboard/Dashboard.tsx');

  it('primes memory before enabling listening', () => {
    expect(dashboard).toContain('tapToMemory');
    const tap = dashboard.slice(dashboard.indexOf('const handleTap'));
    expect(tap.indexOf('tapToMemory')).toBeLessThan(tap.indexOf('setListening(true)'));
  });

  it('surfaces a priming state on the button', () => {
    expect(dashboard).toContain('priming');
    expect(src('components/voice/TapToSpeak.tsx')).toContain('Recalling');
  });
});

describe('Macros: "keep only one graph memory and show types in one side panel"', () => {
  const macros = src('pages/macros/MacrosHome.tsx');

  it('renders a single graph', () => {
    // Count JSX usages only; the import line mentions the name twice.
    const body = macros.slice(macros.indexOf('return ('));
    expect(body.match(/<MemoryGraphCanvas/g)?.length).toBe(1);
  });

  it('lists the memory types in a side panel', () => {
    expect(macros).toContain('Memory Panel');
    expect(macros).toContain('MEMORY_SYSTEMS');
  });
});

describe('Docker: a real Engine connector, not a status panel', () => {
  const page = src('pages/docker/DockerHome.tsx');
  const api = src('services/api.ts');

  it('no longer advertises itself as unimplemented', () => {
    // The page used to render "not implemented" and four "planned" cards.
    expect(page).not.toContain('not implemented');
    expect(page).not.toContain('planned');
  });

  it('calls the Docker API rather than shelling out to the terminal agent', () => {
    expect(page).toContain("from '@services/api'");
    expect(page).not.toContain("input: 'docker ps'");
  });

  it('exposes every Engine resource the page renders', () => {
    for (const method of ['containers', 'images', 'volumes', 'networks', 'logs']) {
      expect(api).toContain(`${method}:`);
    }
  });

  it('checks availability before issuing any other call', () => {
    // status() is the only call that succeeds without a daemon.
    expect(page.indexOf('dockerApi.status()')).toBeLessThan(page.indexOf('dockerApi.info()'));
  });

  it('explains why Docker is unavailable instead of showing empty tables', () => {
    expect(page).toContain('status.reason');
  });

  it('disables rather than hides the controls when they are read-only', () => {
    // Hiding them would leave no clue the capability exists.
    expect(page).toContain('disabled={!status?.control_enabled}');
    expect(page).toContain('allow_docker_control');
  });
});

describe('Avatar upload: getting a model in from the user side', () => {
  const page = src('pages/hologram/AvatarHome.tsx');
  const api = src('services/api.ts');
  const store = src('store/useAvatarStore.ts');

  it('accepts the archive marketplaces actually hand out', () => {
    // A Sketchfab download is a .zip; rejecting it makes the file unusable.
    expect(page).toContain('.zip');
  });

  it('reports upload progress', () => {
    // fetch() cannot report progress, so a large model looked like a hang.
    expect(api).toContain('XMLHttpRequest');
    expect(api).toContain('upload.onprogress');
    expect(store).toContain('progress');
  });

  it('shows the progress bar and the failure reason', () => {
    expect(page).toContain('Uploading {uploading}');
    expect(page).toContain('{error}');
  });

  it('surfaces upload failures instead of swallowing them', () => {
    // upload() resolves to null on failure; that used to be ignored.
    expect(page).toContain('could not upload');
  });

  it('copies from disk on the desktop rather than through the browser', () => {
    expect(page).toContain("detectHost() === 'desktop'");
    expect(api).toContain('import_avatar_files');
  });

  it('tells the user archives are unpacked', () => {
    expect(page).toContain('unpacked automatically');
  });
});

describe('Dashboard drop: files are uploaded, not just named', () => {
  const dashboard = src('pages/dashboard/Dashboard.tsx');
  const panel = src('components/voice/TranscriptPanel.tsx');
  const api = src('services/api.ts');

  it('hands over File objects, not filenames', () => {
    // A browser cannot expose a usable path, so names were unopenable.
    expect(panel).toContain('onDropFiles?: (files: File[]) => void');
    expect(panel).not.toContain('.path ?? file.name');
  });

  it('uploads the bytes before asking an agent', () => {
    expect(dashboard).toContain('uploadsApi.send');
    expect(dashboard).toContain('uploadsApi.analyse');
  });

  it('no longer sends the filename as chat text', () => {
    expect(dashboard).not.toContain('Analyse this dropped file');
  });

  it('shows real transfer progress, not a timer', () => {
    // The bar used to be driven by setInterval regardless of the transfer.
    expect(dashboard).toContain('uploadsApi.send(file, setProgress)');
    expect(dashboard).not.toContain('Math.min(0.95, p + 0.12)');
  });

  it('offers a file picker as well as drag and drop', () => {
    // Drag & drop is undiscoverable, and a touch screen cannot drag at all.
    expect(dashboard).toContain('Attach a file');
    expect(dashboard).toContain("type=\"file\"");
  });

  it('exposes the routing table the drop indicator claims to use', () => {
    expect(api).toContain('/uploads/routing');
  });
});
