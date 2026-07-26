import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { resolve } from 'node:path';
import { aeraDocument } from './vite-plugins/aera-document';

const root = __dirname;

// The interface is served by the AERA desktop shell from local files, so the
// build emits relative asset URLs rather than absolute ones.
export default defineConfig({
  plugins: [
    // Generates index.html and globals.css from TypeScript. Must come first:
    // Vite resolves its HTML entry during config.
    aeraDocument({ root }),
    // Tailwind as a first-class Vite plugin rather than via a separate
    // postcss.config.js, so the whole pipeline lives in this one file.
    tailwindcss(),
    react(),
  ],
  base: './',
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
  build: {
    outDir: '../aera/desktop/ui-react',
    emptyOutDir: true,
    sourcemap: false,
    chunkSizeWarningLimit: 900,
  },
  server: {
    port: 5173,
    // `npm run dev` proxies to a headless `aera serve` for hot reloading.
    proxy: {
      '/api': { target: 'http://localhost:8080', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8080', ws: true },
    },
  },
});
