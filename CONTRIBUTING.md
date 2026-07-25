# Contributing to AERA AGI

Thank you for your interest in contributing! 🎉

## Getting Started

1. **Fork** the repository and clone your fork
2. Copy the environment template: `cp .env.example .env`
3. Install dependencies: `make install`
4. Create a feature branch: `git checkout -b feat/my-feature`

## Development Workflow

```bash
make dev      # run frontend + backend in dev mode
make test     # run all tests
make lint     # lint and format check
make docs     # preview documentation
```

## Project Areas

| Area | Location | Stack |
|---|---|---|
| Frontend | `src/` | TypeScript, Vite |
| Backend services | `services/` | Python |
| Shared code | `shared/` | TS / Python |
| Agents & prompts | `prompts/`, `config/` | Markdown, YAML/JSON |
| Documentation | `docs/` | MkDocs |
| Infrastructure | `docker/`, `scripts/` | Docker, Bash |

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add memory recall endpoint
fix: correct websocket reconnect logic
docs: update voice system spec
chore: bump dependencies
```

## Pull Requests

- Keep PRs focused — one logical change per PR
- Add or update tests for behavior changes
- Update documentation in `docs/` when specs change
- Ensure `make lint` and `make test` pass

## Reporting Issues

- Use the issue templates in `.github/ISSUE_TEMPLATE/`
- For security vulnerabilities, follow [SECURITY.md](SECURITY.md) — do **not** open a public issue

## Code of Conduct

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).
