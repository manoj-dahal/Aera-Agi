# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.x (pre-release) | ✅ Best effort |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead:

1. Use GitHub's **Private Vulnerability Reporting** on this repository
   (Security tab → "Report a vulnerability"), or
2. Contact the maintainer directly through their GitHub profile.

Please include:

- A description of the vulnerability and its impact
- Steps to reproduce or a proof of concept
- Affected components (e.g., API, plugin sandbox, voice system)

You can expect an initial response within **7 days**.

## Security Design Principles

AERA follows a **Zero Trust** architecture (see `docs/21-SECURITY.md`):

- Local-first data storage — user memory never leaves the device by default
- Every agent, plugin, and API request is authenticated and authorized
- Plugins run in a sandboxed permission model
- Secrets are stored in `secrets/` and `.env` — both git-ignored
- The Ethical Hacking module (`docs/22-ETHICAL-HACKING.md`) is strictly for
  **authorized** testing of systems you own or have permission to assess
