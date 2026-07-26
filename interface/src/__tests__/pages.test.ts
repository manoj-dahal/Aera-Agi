/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

/**
 * Structural coverage for every page.
 *
 * A browser cannot be installed in this environment, so these assert on
 * source composition rather than rendered output: every page must exist, be
 * routed, be lazily loaded, handle loading and failure, and wire each button
 * to something. That catches the class of bug this file was written after --
 * pages whose store recorded an error that was never shown.
 */

import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC = resolve(__dirname, '..');
const read = (p: string) => readFileSync(resolve(SRC, p), 'utf-8');

/** Every page component on disk, as `directory/Name`. */
function pageFiles(): string[] {
  const root = resolve(SRC, 'pages');
  return readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .flatMap((dir) =>
      readdirSync(resolve(root, dir.name))
        .filter((file) => file.endsWith('.tsx'))
        .map((file) => `${dir.name}/${file}`),
    )
    .sort();
}

const PAGES = pageFiles();
const routes = read('routes/AppRoutes.tsx');

describe('page inventory', () => {
  it('finds every page', () => {
    // A page that vanishes should fail loudly rather than shrink the suite.
    expect(PAGES.length).toBeGreaterThanOrEqual(17);
  });

  it.each(PAGES)('%s has a default export', (page) => {
    const source = read(`pages/${page}`);
    expect(source).toMatch(/export default \w+/);
  });

  it.each(PAGES)('%s is reachable from the router', (page) => {
    const component = page.split('/')[1]!.replace('.tsx', '');
    expect(routes).toContain(component);
  });

  it('lazily loads every page', () => {
    // Eager imports would pull all 17 pages into the initial bundle.
    const lazyCount = (routes.match(/lazy\(/g) ?? []).length;
    expect(lazyCount).toBeGreaterThanOrEqual(PAGES.length);
  });
});

describe('every button does something', () => {
  /**
   * Read to the closing `>` of the opening tag, tracking JSX braces.
   * Most buttons span several lines, so stopping at the first `>` would
   * look at `<Button` alone and report every one of them as dead.
   */
  function openingTags(source: string, component: string): string[] {
    const tags: string[] = [];
    const marker = `<${component}`;
    let from = source.indexOf(marker);
    while (from !== -1) {
      let i = from + marker.length;
      let depth = 0;
      while (i < source.length) {
        const ch = source[i];
        if (ch === '{') depth += 1;
        else if (ch === '}') depth -= 1;
        else if (ch === '>' && depth === 0) break;
        i += 1;
      }
      tags.push(source.slice(from + marker.length, i));
      from = source.indexOf(marker, i);
    }
    return tags;
  }

  it.each(PAGES)('%s has no handler-less Button', (page) => {
    const source = read(`pages/${page}`);
    for (const tag of openingTags(source, 'Button')) {
      const wired = /onClick|type="submit"|disabled/.test(tag);
      expect(wired, `a <Button> in ${page} has no onClick`).toBe(true);
    }
  });
});

describe('async pages report loading and failure', () => {
  /** Pages that fetch on mount, so the user waits on something. */
  const ASYNC = PAGES.filter((page) => {
    const source = read(`pages/${page}`);
    return /useEffect\(/.test(source) && /(await|\.then\(|void load|Store\(\))/.test(source);
  });

  it('most pages are async', () => {
    expect(ASYNC.length).toBeGreaterThan(8);
  });

  it.each(ASYNC)('%s shows progress while it waits', (page) => {
    const source = read(`pages/${page}`);
    const waits = /loading|Loading|busy|running|pending|priming|Spinner/.test(source);
    expect(waits, `${page} never indicates it is working`).toBe(true);
  });

  it.each(ASYNC)('%s surfaces failure rather than showing an empty page', (page) => {
    const source = read(`pages/${page}`);
    // Either the page renders an error, or it catches and toasts one.
    const reports = /error|Error|catch\s*\(|showToast/.test(source);
    expect(reports, `${page} swallows failures`).toBe(true);
  });
});

describe('store errors reach the screen', () => {
  /**
   * Regression: MemoryHome and WorkspaceHome both destructured `loading`
   * from their store but never `error`, so a failed load rendered as an
   * ordinary empty list.
   */
  const STORE_PAGES: [string, string][] = [
    ['memory/MemoryHome.tsx', 'useMemoryStore'],
    ['workspace/WorkspaceHome.tsx', 'useWorkspaceStore'],
    ['agents/AgentsHome.tsx', 'useAgentStore'],
    ['hologram/AvatarHome.tsx', 'useAvatarStore'],
  ];

  it.each(STORE_PAGES)('%s consumes the error its store records', (page, store) => {
    const source = read(`pages/${page}`);
    expect(source).toContain(store);
    expect(source, `${page} ignores store.error`).toMatch(/\berror\b/);
  });
});

describe('custom AI providers', () => {
  const api = read('services/api.ts');

  it('the models page can reach the provider endpoints', () => {
    // Adding your own model used to require editing YAML and restarting.
    expect(api).toContain('/models/providers');
  });
});
