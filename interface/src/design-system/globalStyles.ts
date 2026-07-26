/**
 * Global stylesheet, authored in TypeScript.
 *
 * This used to be a hand-maintained `styles/globals.css` whose `:root` block
 * restated every theme colour, so a token could drift from `themes.ts`
 * without anything failing. Here the custom properties are derived from the
 * theme objects themselves, which makes that class of drift impossible.
 *
 * `vite-plugins/aera-document.ts` writes the result to `src/styles/globals.css`
 * before Tailwind scans it; the emitted file is a build artifact, not source.
 */

import { darkTheme, cssVarName } from './themes';
import { palette } from './colors';

/** Tailwind v4 reads its design tokens from an `@theme` block. */
function themeBlock(): string {
  const entries: [string, string][] = [
    ['--color-bg-base', palette.bg.base],
    ['--color-bg-raised', palette.bg.raised],
    ['--color-bg-surface', palette.bg.surface],
    ['--color-bg-overlay', palette.bg.overlay],
    ['--color-bg-hover', palette.bg.hover],
    ['--color-line-subtle', palette.line.subtle],
    ['--color-line-default', palette.line.default],
    ['--color-line-strong', palette.line.strong],
    ['--color-text-primary', palette.text.primary],
    ['--color-text-secondary', palette.text.secondary],
    ['--color-text-muted', palette.text.muted],
    ['--color-text-disabled', palette.text.disabled],
    ['--color-accent', palette.accent.primary],
    ['--color-accent-2', palette.accent.secondary],
    ['--color-success', palette.status.success],
    ['--color-warning', palette.status.warning],
    ['--color-danger', palette.status.danger],
    ['--font-sans', "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Roboto, sans-serif"],
    ['--font-mono', "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace"],
  ];
  return `@theme {\n${entries.map(([k, v]) => `  ${k}: ${v};`).join('\n')}\n}`;
}

/**
 * Boot defaults for the runtime custom properties.
 *
 * `applyTheme()` overwrites these on mount, but they must exist beforehand or
 * the first paint is unstyled. Generated from the dark theme so the two can
 * never disagree.
 */
function rootBlock(): string {
  const lines = Object.entries(darkTheme.colors).map(
    ([key, value]) => `  ${cssVarName(key)}: ${value};`,
  );
  return `:root {\n  /* Written from darkTheme; applyTheme() overwrites at runtime. */\n${lines.join('\n')}\n}`;
}

/** Element resets, host-conditional affordances, scrollbars and animation. */
const BASE = `
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html,
body,
#root {
  height: 100%;
}

body {
  background: var(--aera-bg-base);
  color: var(--aera-text-primary);
  font-family: var(--font-sans);
  font-size: 13.5px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  overflow: hidden;
}

/* Desktop-app feel: text is selectable only where it carries content. */
body[data-host='desktop'] {
  user-select: none;
  cursor: default;
}
body[data-host='desktop'] .selectable,
body[data-host='desktop'] input,
body[data-host='desktop'] textarea,
body[data-host='desktop'] pre,
body[data-host='desktop'] code {
  user-select: text;
  cursor: text;
}

a {
  color: var(--aera-accent-primary);
  text-decoration: none;
}

button {
  font: inherit;
  color: inherit;
  cursor: pointer;
  border: 0;
  background: none;
}
body[data-host='desktop'] button {
  cursor: default;
}
button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

input,
textarea,
select {
  font: inherit;
  color: inherit;
  outline: none;
}

:focus-visible {
  outline: 2px solid var(--aera-accent-primary);
  outline-offset: 2px;
}

/* ---------- scrollbars ---------- */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--aera-bg-overlay);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--aera-line-strong);
}

/* ---------- animation ---------- */
@keyframes aera-rise {
  from {
    opacity: 0;
    transform: translateY(5px);
  }
}
@keyframes aera-spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes aera-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
@keyframes aera-wave {
  0%,
  100% {
    transform: scaleY(0.55);
  }
  50% {
    transform: scaleY(1);
  }
}
@keyframes aera-scan {
  0% {
    transform: translateY(-100%);
  }
  100% {
    transform: translateY(100%);
  }
}
@keyframes aera-glow {
  0%,
  100% {
    box-shadow: 0 0 12px color-mix(in srgb, var(--aera-accent-primary) 25%, transparent);
  }
  50% {
    box-shadow: 0 0 26px color-mix(in srgb, var(--aera-accent-primary) 55%, transparent);
  }
}
@keyframes aera-breathe {
  to {
    transform: scale(1.22);
    /* Follows the accent rather than a hard-coded colour, which is how this
       kept its old violet glow after the palette moved to cyan. */
    box-shadow: 0 0 38px color-mix(in srgb, var(--aera-accent-primary) 80%, transparent);
  }
}

.animate-rise {
  animation: aera-rise 0.2s ease;
}
.animate-spin-slow {
  animation: aera-spin 10s linear infinite;
}
.animate-pulse-slow {
  animation: aera-pulse 3s ease-in-out infinite;
}
.animate-breathe {
  animation: aera-breathe 0.55s ease-in-out infinite alternate;
}
.animate-scan {
  animation: aera-scan 1.6s linear infinite;
}
.animate-glow {
  animation: aera-glow 2.4s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* ---------- utilities ---------- */
.text-gradient {
  background: linear-gradient(135deg, var(--aera-accent-primary), var(--aera-accent-secondary));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.surface {
  background: var(--aera-bg-surface);
  border: 1px solid var(--aera-line-default);
}
`;

/** The complete stylesheet, ready to be written next to the entry module. */
export function renderGlobalStyles(): string {
  return [
    '/* Generated by vite-plugins/aera-document.ts from',
    ' * src/design-system/globalStyles.ts. Do not edit: your changes will be',
    ' * overwritten on the next build. */',
    "@import 'tailwindcss';",
    '',
    themeBlock(),
    '',
    rootBlock(),
    BASE,
  ].join('\n');
}
