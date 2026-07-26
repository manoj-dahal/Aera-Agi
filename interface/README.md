# AERA Interface

React + TypeScript front end for the AERA AI Operating System.

The same build runs in two hosts:

| Host | How it loads | Transport |
|---|---|---|
| **Desktop** (default) | The native window loads `aera/desktop/ui-react/index.html` from disk | `window.pywebview.api` — a direct in-process call into the Python kernel |
| **Browser** | Served by `aera serve` | REST + server-sent events |

`src/services/transport.ts` detects the host at runtime; nothing above that
layer knows the difference.

---

## Development

```bash
cd interface
npm install

# Terminal 1 — headless backend
aera serve

# Terminal 2 — hot-reloading UI at http://localhost:5173
npm run dev
```

Vite proxies `/api` and `/ws` to `localhost:8080`, so the dev server behaves
like the packaged app.

## Build

```bash
npm run build      # type-check, then emit to ../aera/desktop/ui-react/
```

Both the desktop shell and `aera serve` load that directory. It is the only
UI, so the app will not start until it has been built once.

```bash
npm run typecheck  # tsc --noEmit
npm test           # vitest
```

---

## Structure

```
src/
├── index.tsx            entry point + boot gate
├── routes/              lazy-loaded route table
├── layouts/             Main, Dashboard, Workspace, Auth, Fullscreen
├── pages/               one directory per feature area
├── components/          shared UI, grouped by kind
├── design-system/       colours, typography, spacing, themes, tokens
├── store/               Zustand stores (system, chat, memory, agents, workspace)
├── services/            typed API client, transport, backend contracts
├── hooks/               polling, debounce, native menu binding
├── context/             host/environment context
├── utils/               formatting, safe markdown, class names
└── styles/              Tailwind v4 entry and global CSS
```

### Design system

Colour, type and spacing tokens live in `design-system/` and are mirrored as
CSS custom properties (`--aera-*`) written by `applyTheme()`. Switching themes
rewrites those variables, so it costs no re-render.

Three themes ship: `dark` (default), `midnight` (OLED) and `light`.

### State

Five Zustand stores, each owning one slice:

- `useSystemStore` — status polling and the live event feed
- `useChatStore` — messages and the streaming lifecycle
- `useMemoryStore` — graph browsing and recall
- `useAgentStore` — roster and lifecycle control
- `useWorkspaceStore` — active project, search and file preview

### Safety

Model output is rendered by `utils/markdown.ts`, which escapes all HTML
**before** re-introducing a small set of constructs (fenced code, inline code,
bold, italics, headings). There is no `dangerouslySetInnerHTML` path that
receives unescaped input; this is covered by tests.

---

## Dashboard layout

The Dashboard follows `docs/04-DASHBOARD.md` exactly:

```
┌─────────────────────────────────────────────────────────────────────┐
│ AERA Agent   [Dashboard Macros Apps]   [Gallery Phone Settings]     │
├─────────────┬───────────────────────────────┬───────────────────────┤
│ Hologram    │                               │   Transcript          │
│ System Info │         Particle Sphere       │   (drag & drop,       │
│             │                               │    watermark)         │
│ Workspace   │         TAP TO SPEAK          │                       │
├─────────────┴───────────────────────────────┴───────────────────────┤
│ Model · Agent · Agents · Memory · Events · Uptime      ● Connected   │
└─────────────────────────────────────────────────────────────────────┘
```

- **Particle sphere** — 1,400 points on a Fibonacci lattice, canvas-rendered
  with perspective depth. Rotation, turbulence and glow follow the avatar state
  (`idle` · `listening` · `thinking` · `speaking` · `processing` · `error` ·
  `offline`); colour follows detected emotion.
- **Transcript** — angled HUD frame drawn in SVG. The AERA watermark sits at 6%
  opacity and lights up during a drag, per the spec's drop workflow.
- **Workspace panel** — open folder, search and refresh in the header, with the
  project tree beneath.

## Page status

Every page is built against live backend data:

`Dashboard` · `Macros` · `Apps` · `Gallery` · `Phone` · `Settings` ·
`Memory` · `Agents` · `Workspace` · `Models` · `Automation` · `Hologram` ·
`Terminal` · `Docker` · `Plugins` · `Security` · `System`

Where a capability genuinely does not exist yet — Docker's API client, media
download, device pairing — the page reports it at the point of use instead of
offering a control that fails silently. Terminal drives the real agent and
explains how to enable it when the agent is off.

The top bar carries the six destinations the spec names. Settings holds exactly
three sections — AI, Voice and System — and the remaining subsystem pages nest
inside them. Plugin management lives in Apps, never in Settings.

The directory scaffold also reserves space for `auth/` and `onboarding/`
flows. Local desktop installs are single-user and unauthenticated by default
(`api.auth_enabled: false`), so those screens are only needed for shared-server
deployments; `AuthLayout` is in place for when they are built.

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
