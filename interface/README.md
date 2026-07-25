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

The desktop shell prefers that directory when it exists and falls back to the
dependency-free UI in `aera/desktop/ui/` otherwise — so the app still runs if
Node was never installed.

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

## Page status

Wired to a live backend:

`Dashboard` · `Memory` · `Agents` · `Workspace` · `Models` · `Automation` ·
`Hologram` · `Security` · `Settings` · `System`

Rendered as an explicit "not implemented yet" panel, because the backend for
them is partial or absent:

`Terminal` · `Docker` · `Plugins`

Those screens state what already works and what is still missing rather than
presenting controls that do nothing.

The directory scaffold also reserves space for `auth/` and `onboarding/`
flows. Local desktop installs are single-user and unauthenticated by default
(`api.auth_enabled: false`), so those screens are only needed for shared-server
deployments; `AuthLayout` is in place for when they are built.
