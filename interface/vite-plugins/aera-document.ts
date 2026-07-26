/**
 * Generates the two files Vite requires on disk but that we author in React.
 *
 * Vite needs a real `index.html` as its Rollup entry, and Tailwind needs a
 * real `.css` file to scan. Rather than maintain those as hand-written
 * HTML/CSS sitting outside the component tree, both are produced here from
 * TypeScript: the document shell from `src/document.ts` and the stylesheet
 * from `src/design-system/globalStyles.ts`.
 *
 * Vite bundles its own config, so importing those modules here is enough --
 * and because Vite watches config dependencies, editing either source
 * restarts the dev server and regenerates automatically.
 *
 * The emitted files are build artifacts (git-ignored). Editing them by hand
 * has no effect: they are rewritten on every build.
 */

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import type { Plugin } from 'vite';
import { renderDocument } from '../src/document';
import { renderGlobalStyles } from '../src/design-system/globalStyles';

/** Write only when the content changed, so we do not thrash the watcher. */
function writeIfChanged(path: string, content: string): void {
  try {
    if (readFileSync(path, 'utf8') === content) return;
  } catch {
    // Missing file: fall through and create it.
  }
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content, 'utf8');
}

export function aeraDocument({ root }: { root: string }): Plugin {
  function generate(): void {
    writeIfChanged(resolve(root, 'src/styles/globals.css'), renderGlobalStyles());
    writeIfChanged(resolve(root, 'index.html'), renderDocument());
  }

  return {
    name: 'aera-document',
    // Must run before Vite resolves its HTML entry point.
    enforce: 'pre',
    config() {
      generate();
    },
    buildStart() {
      generate();
    },
  };
}
