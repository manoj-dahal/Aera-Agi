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
