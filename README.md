# AERA AGI

> **A**rtificial **E**nhanced **R**easoning **A**ssistant — a next-generation AI Operating System.

AERA combines persistent memory, multi-agent intelligence, natural voice interaction, a holographic avatar, workflow automation, and local + cloud AI models into a single, privacy-first platform.

---

## ✨ Core Principles

- **Local First** — runs on your machine; the cloud is optional
- **Privacy First** — your data and memory stay with you
- **AI Native** — every feature is enhanced by AI
- **Memory First** — a shared Memory Graph connects everything
- **Modular** — agents, plugins, and services are independent and extensible

## 🧠 Major Modules

| Module | Description |
|---|---|
| Dashboard | Central workspace with AI Core, hologram, and transcript |
| Memory Graph | Persistent knowledge graph shared by all agents |
| Agents | 20+ specialized AI agents (coding, research, planning, …) |
| Voice System | STT → LLM → Emotion Engine → TTS pipeline |
| Hologram | Real-time animated avatar synced to voice and emotion |
| Workspace | AI-aware project and file environment |
| Automation | Event-driven workflow engine |
| Local / Cloud AI | Intelligent model routing (Ollama, OpenAI, Claude, Gemini, …) |

## 📁 Repository Layout

```text
AERA-agi/
├── src/          # Frontend application (TypeScript + Vite)
├── services/     # Backend services (Python)
├── shared/       # Shared types, schemas, utilities
├── config/       # System, agent, model, and voice configuration
├── prompts/      # Agent and system prompt templates
├── plugins/      # Sandboxed plugin ecosystem
├── extensions/   # Editor/app extensions
├── database/     # Migrations and schema
├── docker/       # Container definitions and compose fragments
├── scripts/      # Dev, build, and ops scripts
├── tools/        # CLI and maintenance tooling
├── tests/        # Test suites
├── docs/         # Full design specification (MkDocs)
├── models/       # Local AI models (git-ignored)
├── data/         # Local databases (git-ignored)
├── storage/      # Vector stores and blobs (git-ignored)
└── workspace/    # User project workspace (git-ignored)
```

## 🚀 Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/manoj-dahal/Aera-Agi.git
cd Aera-Agi
cp .env.example .env

# 2. Install dependencies
make install          # or: npm install && pip install -r requirements.txt

# 3. Run in development
make dev              # frontend + backend

# 4. Or run everything with Docker
docker compose up -d
```

## 📚 Documentation

The complete design specification lives in [`docs/`](docs/) — 30 core chapters plus deep-dives on agents, memory, voice, hologram, API, and Docker.

```bash
make docs   # serve docs locally with MkDocs
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), our [Code of Conduct](CODE_OF_CONDUCT.md), and the [Security Policy](SECURITY.md).

## 📄 License

Released under the [MIT License](LICENSE).
