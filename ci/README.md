# Continuous integration

## Current state on GitHub — Node.js CI is red

Two workflows are live on `main`, both added from GitHub's default templates:

| Workflow | Status |
|---|---|
| **Docker** | passing on pull requests; the `main` push runs failed |
| **Node.js CI** | **failing on every run**, since it was added |

### Why Node.js CI fails

Not `npm ci` erroring — it never reaches that step. Every run dies at step 3
of 6, `Use Node.js`, with the other two matrix legs cancelling each other:

```
1. Set up job                    success
2. actions/checkout@v4           success
3. Use Node.js 22.x              failure     <-- here
4. npm ci                        skipped
5. npm run build --if-present    skipped
6. npm test                      skipped
```

`actions/setup-node` with `cache: 'npm'` searches for a lockfile starting at
the repository root. **There is no `package.json` or lockfile at the root of
this project** — the Node application is the React interface, and its manifest
is at `interface/package.json`. The cache step finds nothing and fails during
setup.

The template is correct for a repository whose Node project is at the top
level. This one is a Python package with a front end inside it.

### The fix

`github-actions-node.yml` in this directory. Two changes:

- `cache-dependency-path: interface/package-lock.json`
- `defaults.run.working-directory: interface`

Plus three corrections found while checking it:

- The matrix tested Node 18, 20 and 22. Vite 7 declares
  `engines: ^20.19.0 || >=22.12.0`, so 18 is unsupported outright and a bare
  `20.x` can resolve below 20.19. Testing a version the project cannot run on
  is not coverage, it is a red cross nobody can act on. Pinned to `20.19` and
  `22.x`.
- `npm run build --if-present` silently passes when there is no build script.
  The build is not optional here, so it runs unconditionally.
- `npm run typecheck` was not run at all, and the build output was never
  checked. The build writes into `aera/desktop/ui-react`, which the
  PyInstaller spec refuses to package without, so CI now verifies it exists.

Every command in the replacement was run locally first: `npm ci`,
`npm run typecheck`, `npm test` and `npm run build` all pass.

### To apply it

I cannot. Pushing anything under `.github/workflows/` is rejected:

```
! [remote rejected] refusing to allow a GitHub App to create or update
  workflow `.github/workflows/node.js.yml` without `workflows` permission
```

That was tested against the live remote, not assumed. You need to replace the
file yourself:

```bash
cp ci/github-actions-node.yml .github/workflows/node.js.yml
git add .github/workflows/node.js.yml
git commit -m "Fix Node CI: the interface is not at the repository root"
git push
```


`github-actions-ci.yml` is a ready-to-use GitHub Actions workflow for this
project. It was placed here rather than in `.github/workflows/` because the
GitHub App used to push this branch does not hold the `workflows` permission.

To enable it:

```bash
mkdir -p .github/workflows
git mv ci/github-actions-ci.yml .github/workflows/ci.yml
git commit -m "Enable CI workflow"
git push
```

## What it runs

| Job | Steps |
|---|---|
| `test` | matrix over Python 3.10 / 3.11 / 3.12 — `ruff check`, `pytest -q`, then boots the server and probes `/health` and `POST /api/v1/chat` |
| `docker` | builds the image, runs the container and waits for the health check to report ready |

The suite is fully offline: no API keys, no model downloads, no network calls.

---

## `github-actions-desktop.yml`

Builds the standalone desktop application for **Linux, macOS and Windows**,
verifies each bundle contains the UI assets and configuration, launches the
frozen binary on all three platforms, and attaches the archives to the run.
Pushing a `v*` tag also publishes a GitHub release.

### Status: written and validated, never executed

**No run of this workflow has ever happened.** It cannot be enabled from here:
pushing a file under `.github/workflows/` is rejected outright —

```
! [remote rejected] refusing to allow a GitHub App to create or update
  workflow `.github/workflows/desktop.yml` without `workflows` permission
```

That was tested, not assumed. Until someone with the permission moves the file,
no Windows binary exists and none has been launched.

What *has* been verified, by `tests/test_documentation.py::TestDesktopBuildWorkflow`:

| Check | Why it matters |
|---|---|
| Windows, macOS and Linux are all in the matrix | |
| The job shell is `bash` on every runner | GitHub defaults Windows to PowerShell, where a multi-line `run` block **continues after a failed command** — `npm ci` could fail and `npm run build` would still run, producing a green build with no interface in it |
| PowerShell steps opt in with `shell: pwsh` | `Compress-Archive` and `Start-Process` are cmdlets and cannot run under bash |
| Every platform starts the binary | Windows previously built the `.exe`, listed its contents and zipped it **without ever launching it** |
| The Windows smoke test throws when the app exits early | A check that cannot fail is not a check |
| `AERA.exe` and the `_internal` layout are asserted | PyInstaller 6 puts data under `_internal`; the spec requires 6 |
| `installer/icon.ico` is a real ICO with images | PyInstaller only rejects a mislabelled icon **on Windows**, so a placeholder would pass Linux and fail the Windows job |
| The `[package]` extra provides PyInstaller | |
| Every `npm` script the workflow calls is defined | Read from the step, so a call to a missing script is caught |
| `interface/package-lock.json` exists | `npm ci` fails outright without one |

Building it here is impossible for a second, unrelated reason: this sandbox has
no `libpython3.11.so.1.0`, so PyInstaller refuses to start. That was confirmed
by running it.

```bash
mkdir -p .github/workflows
git mv ci/github-actions-desktop.yml .github/workflows/desktop.yml
git commit -m "Enable desktop build workflow"
git push --tags
```

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
