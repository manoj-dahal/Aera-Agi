# 03 - FILE STRUCTURE

Version: 1.0.0

Status: Project Structure Specification

---

# Overview

The AERA project follows a modular architecture. Every major subsystem has its own directory, making the project scalable, maintainable, and easy to extend.

The source code, AI services, documentation, configuration, and deployment files are separated into dedicated modules.

---

# Root Structure

```text
AERA/
│
├── app/
├── backend/
├── agents/
├── ai/
├── memory/
├── models/
├── services/
├── workspace/
├── voice/
├── hologram/
├── apps/
├── gallery/
├── phone/
├── settings/
├── automation/
├── security/
├── api/
├── database/
├── config/
├── docker/
├── docs/
├── scripts/
├── tests/
├── assets/
├── plugins/
├── logs/
├── cache/
├── storage/
├── temp/
├── .github/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── README.md
└── LICENSE
```

---

# app/

Frontend application.

```text
app/
│
├── dashboard/
├── macros/
├── workspace/
├── apps/
├── gallery/
├── phone/
├── settings/
├── widgets/
├── navigation/
├── themes/
├── animations/
├── shared/
└── main.dart
```

Responsibilities

- UI
- Navigation
- Theme
- Widgets
- Animations

---

# backend/

Business logic.

```text
backend/
│
├── core/
├── routers/
├── middleware/
├── services/
├── websocket/
├── scheduler/
├── startup.py
└── main.py
```

---

# agents/

All AI agents.

```text
agents/
│
├── core/
├── coding/
├── memory/
├── voice/
├── planning/
├── reasoning/
├── research/
├── automation/
├── terminal/
├── git/
├── vision/
├── audio/
├── document/
├── translation/
├── workspace/
├── gallery/
├── device/
├── security/
├── network/
├── update/
├── learning/
└── notification/
```

---

# ai/

AI orchestration.

```text
ai/
│
├── router/
├── providers/
├── prompts/
├── embeddings/
├── inference/
├── tokenizer/
└── utils/
```

Responsibilities

- Model routing
- Prompt management
- AI inference
- Embeddings

---

# memory/

Persistent memory system.

```text
memory/
│
├── graph/
├── short_term/
├── long_term/
├── semantic/
├── episodic/
├── procedural/
├── recall/
├── compression/
├── backup/
└── sync/
```

---

# models/

AI models.

```text
models/
│
├── local/
├── cloud/
├── embeddings/
├── configs/
└── downloads/
```

---

# services/

Background services.

```text
services/
│
├── memory_engine/
├── context_engine/
├── scheduler/
├── updater/
├── performance/
├── monitoring/
├── logging/
├── diagnostics/
├── notifications/
├── cache/
└── security/
```

These services run in the background.

---

# workspace/

Project management.

```text
workspace/
│
├── explorer/
├── indexer/
├── parser/
├── analyzer/
├── search/
├── context/
└── projects/
```

---

# voice/

Voice engine. A flat set of modules rather than nested directories: the
layout below is what exists. This section previously described stt/, tts/,
emotion/, conversation/, recognition/, synthesis/, wakeword/ and utils/
directories, none of which has ever been created.

```text
voice/
│
├── engine.py        session state, wake word, the speak pipeline
├── expression.py    mood, negation-aware emotion, per-word prosody
├── personas.py      anime-g and anime-b, per-emotion acoustics, formant synth
├── backends.py      Piper and system TTS, probing and fallback
├── languages.py     35 language packs, per-language number reading
├── packs_western.py Europe and the Americas
├── packs_asia.py    South Asia, East Asia, Middle East, Africa
├── scripts.py       writing systems and the mouth shapes each implies
├── phonetics.py     spoken-form normalisation, viseme tracks
└── music.py         syllables, metre, rhyme, tempo, scales, singing
```

---

# hologram/

3D avatar.

```text
hologram/
│
├── avatar/
├── animation/
├── emotions/
├── lipsync/
├── gestures/
├── eye_tracking/
├── shaders/
└── renderer/
```

---

# apps/

Desktop integration.

```text
apps/
│
├── terminal/
├── git/
├── vscode/
├── blender/
├── photoshop/
├── premiere/
├── davinci/
├── browser/
├── custom/
└── manager/
```

---

# gallery/

Media manager.

```text
gallery/
│
├── images/
├── videos/
├── preview/
├── browser/
├── analysis/
└── cache/
```

---

# phone/

Phone integration.

```text
phone/
│
├── android/
├── ios/
├── calls/
├── messages/
├── notifications/
└── sync/
```

---

# settings/

System configuration.

```text
settings/
│
├── ai/
├── voice/
├── system/
├── themes/
├── language/
└── backup/
```

---

# automation/

Automation workflows.

```text
automation/
│
├── workflows/
├── macros/
├── scheduler/
├── triggers/
└── actions/
```

---

# security/

Security modules.

```text
security/
│
├── encryption/
├── permissions/
├── authentication/
├── audit/
├── scanner/
└── sandbox/
```

---

# api/

API layer.

```text
api/
│
├── rest/
├── websocket/
├── authentication/
├── middleware/
└── schemas/
```

---

# database/

Data storage.

```text
database/
│
├── sqlite/
├── postgres/
├── chromadb/
├── migrations/
└── backups/
```

---

# config/

Configuration.

```text
config/
│
├── app.yaml
├── ai.yaml
├── models.yaml
├── memory.yaml
├── voice.yaml
├── workspace.yaml
├── security.yaml
├── settings.yaml
└── docker.yaml
```

---

# docker/

Deployment.

```text
docker/
│
├── Dockerfile.api
├── Dockerfile.ai
├── Dockerfile.voice
├── docker-compose.yml
├── compose.dev.yml
├── compose.prod.yml
└── nginx.conf
```

---

# docs/

Documentation.

```text
docs/
├── README.md
├── 00-INTRODUCTION.md
├── 01-VISION.md
├── 02-SYSTEM-ARCHITECTURE.md
├── ...
└── agents/
```

---

# assets/

```text
assets/
├── icons/
├── images/
├── hologram/
├── voices/
├── fonts/
└── animations/
```

---

# plugins/

```text
plugins/
├── installed/
├── marketplace/
├── custom/
└── manifests/
```

---

# logs/

```text
logs/
├── system/
├── ai/
├── agents/
├── errors/
└── updates/
```

---

# storage/

Persistent user data.

```text
storage/
├── memories/
├── conversations/
├── downloads/
├── projects/
└── backups/
```

---

# scripts/

Automation scripts.

```text
scripts/
├── install.sh
├── update.sh
├── build.sh
├── run.sh
└── clean.sh
```

---

# tests/

```text
tests/
├── unit/
├── integration/
├── ui/
├── performance/
└── security/
```

---

# Design Principles

- Modular architecture
- Single responsibility per module
- Independent background services
- Shared memory system
- Local-first AI
- Plugin-ready
- Cross-platform compatibility
- Production-ready deployment

---

# Summary

The AERA project structure separates the user interface, AI core, agents, memory system, background services, application integrations, and deployment infrastructure into clearly defined modules. This organization supports maintainability, scalability, testing, and future feature expansion while keeping responsibilities isolated.