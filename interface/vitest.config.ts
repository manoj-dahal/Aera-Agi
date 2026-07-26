/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

/**
 * Vitest configuration.
 *
 * Kept separate from vite.config.ts because the app build runs the
 * aera-document plugin, which writes index.html and globals.css. Tests do not
 * need that, and running it on every test invocation would rewrite files as a
 * side effect of checking them.
 *
 * Two environments are in play: most suites analyse source text and need no
 * DOM, while component tests render React and do. jsdom is set globally and
 * costs little for the text-only suites.
 */

import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';

const root = __dirname;

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(root, 'src'),
      '@components': resolve(root, 'src/components'),
      '@pages': resolve(root, 'src/pages'),
      '@layouts': resolve(root, 'src/layouts'),
      '@design': resolve(root, 'src/design-system'),
      '@hooks': resolve(root, 'src/hooks'),
      '@store': resolve(root, 'src/store'),
      '@services': resolve(root, 'src/services'),
      '@utils': resolve(root, 'src/utils'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: false,
    setupFiles: [resolve(root, 'src/__tests__/setup.ts')],
    // Component tests mount real React trees; give them room without
    // letting a genuine hang run forever.
    testTimeout: 10_000,
  },
});
