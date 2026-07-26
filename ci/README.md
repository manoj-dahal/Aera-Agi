# Continuous integration

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
