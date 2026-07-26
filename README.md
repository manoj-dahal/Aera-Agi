<div align="center">

<img src="assets/brand/banner.png" alt="AERA" width="820" />

</div>

# AERA

**Artificial Enhanced Reasoning Assistant** — a native desktop AI Operating System
with a persistent memory graph, multi-agent orchestration and local-first model
routing.

[![tests](https://img.shields.io/badge/tests-1965%20passing-brightgreen)]()
[![python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![desktop](https://img.shields.io/badge/desktop-Windows%20%7C%20macOS%20%7C%20Linux-7c5cff)]()
[![license](https://img.shields.io/badge/license-MIT-lightgrey)]()

AERA is not a chatbot wrapper. It is a desktop runtime: requests enter through a
Core Agent that detects intent, recalls relevant memory, delegates to a
specialist agent, and writes the outcome back into a shared knowledge graph that
every other agent can read.

Everything runs on your machine. The kernel executes in-process inside the
application — no web server, no bound port, no browser.

**[REQUIREMENTS.md](REQUIREMENTS.md)** records what is built, what is built with
a stated limit, and what is not built at all. Nothing in this repository fakes a
capability it does not have; where something is missing, the call that would use
it says so.

---

## Quick start

```bash
git clone https://github.com/manoj-dahal/Aera-Agi.git
cd Aera-Agi
./scripts/install.sh

source .venv/bin/activate
aera                      # launches the desktop application
```

**No API keys required.** AERA ships with a built-in offline reasoner, so the
full stack — memory, agents, routing, automation, voice pipeline — runs with
zero configuration and zero network access. Add a local or cloud model when you
want production-grade generation.

### Standalone executable

Build a self-contained app that needs no Python on the target machine:

```bash
./scripts/build-desktop.sh          # builds the interface, then the executable
```

Node 20 or newer is required: the script builds the React interface first,
because the PyInstaller spec refuses to package without it.

| Platform | Output | Webview runtime |
|---|---|---|
| Windows | `dist/AERA/AERA.exe` | WebView2 (ships with Windows 11) |
| macOS | `dist/AERA.app` | WebKit (built in) |
| Linux | `dist/AERA/AERA` | WebKit2GTK (`libwebkit2gtk-4.1-0`) |

### Headless server (optional)

For remote or multi-user deployments, AERA also runs without a window:

```bash
aera serve      # REST API + WebSocket + browser dashboard on :8080
```

### Docker

```bash
docker compose up -d                      # core only, offline
docker compose --profile local-ai up -d   # + Ollama for local LLMs
docker compose --profile full up -d       # + PostgreSQL and Redis
```

### Command line

```bash
aera                          # desktop application (default)
aera serve                    # headless API server
aera repl                     # interactive terminal session
aera chat "explain CQRS"      # one-shot query
aera index ~/projects/my-app  # index a codebase into memory
aera memory search "docker"   # query the memory graph
aera agents                   # list agents and their state
aera status                   # full system snapshot
```

---

## Architecture

```
              Native window (WebKit / WebView2)  ·  React interface
                                     │
                        Python bridge  ·  REST  ·  WebSocket
                                     │
                                 Core Agent
                  intent → recall → plan → delegate → respond
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
  Agent Registry              Memory Engine                 Model Router
  15 specialists          hybrid recall + graph        local-first + failover
        │                            │                            │
        └────────────────────────────┼────────────────────────────┘
                                     ▼
                                 Event Bus
              workspace · automation · voice · hologram · security
```

Every subsystem communicates over the event bus — no module reaches into
another directly.

### Request lifecycle

1. **Intent detection** — the Core Agent classifies the request into one of 23 capabilities.
2. **Memory recall** — hybrid semantic + keyword search, expanded across graph relationships.
3. **Agent selection** — the highest-priority agent advertising that capability wins.
4. **Execution** — the specialist runs, with the recalled context injected into its prompt.
5. **Memory update** — the exchange is written back as linked episodic nodes.

---

## Memory graph

The core differentiator. Memories are nodes in a typed, weighted graph rather
than rows in a chat log.

- **Six memory systems** — short-term, long-term, working, semantic, episodic, procedural
- **23 node types** — conversation, project, file, task, agent, decision, workflow, …
- **10 relationship types** — parent, depends-on, references, similar-to, …
- **Hybrid recall** — semantic similarity (45%), keyword overlap (25%), importance (15%), recency (10%), frequency (5%)
- **Graph expansion** — top hits pull in their neighbours, with score decay per hop
- **Consolidation** — valuable short-term memories are promoted; stale ones pruned

Embeddings use a deterministic hashing embedder by default, so semantic search
works offline with no model download. Swap in any provider behind the same
interface.

```python
from aera.memory import MemoryEngine

memory = MemoryEngine()
await memory.store("Postgres migration", "moving from sqlite", tags=["db"])
results = await memory.recall("database changes")   # finds it semantically
context = await memory.build_context("deployment")  # prompt-ready block
```

---

## Agents

31 agents implement the full specified roster; 26 are enabled by default. Each
declares the capabilities the router uses to reach it.

| Agent | Capabilities |
|---|---|
| `core` | orchestration, intent detection, delegation |
| `memory` | store, recall, consolidate, graph maintenance |
| `coding` | code generation across 16 languages |
| `code_review` | correctness, security, performance, style |
| `debug` | stack-trace analysis and fixes |
| `reasoning` | structured analysis and explanation |
| `planning` | goal decomposition with dependencies |
| `research` | knowledge gathering and synthesis |
| `writing` | documentation and technical prose |
| `translation` | 20+ languages |
| `workspace` | project structure and file analysis |
| `git` | repository analysis, commit assistance |
| `terminal` | allowlisted shell execution *(off by default)* |
| `security` | defensive review and hardening |
| `performance` | live metrics and optimisation |
| `notification` | dashboard alerts |
| `conversation` | natural dialogue with cross-session continuity |
| `document` | reads and summarises text documents |
| `network` | local diagnostics: resolve, reachability, host status |
| `device` | host machine facts and device pairing |
| `personalization` | learns and applies user preferences |
| `collaboration` | plans multi-agent handoffs |
| `learning` | detects patterns across the memory graph |
| `monitoring` | subsystem health and anomaly reporting |
| `scheduler` · `automation` | workflow design and scheduled jobs |
| `backup` · `update` | snapshots and version reporting |
| `ethical_hacking` | authorised defensive security work only |
| `vision` · `ocr` · `audio` · `web` | capability-gated (see below) |

**Capability-gated agents.** `vision`, `ocr`, `audio` and `web` need a backend
AERA does not bundle — a multimodal model, Tesseract, a speech-to-text engine,
network permission. They are implemented and registered, but detect the missing
backend and say so precisely instead of fabricating a result. `audio` and `web`
are off by default; `web` additionally requires `security.allow_network`, and
refuses loopback, private and link-local addresses even when enabled.

Adding an agent is a subclass and a registration:

```python
from aera.agents import Agent, Capability, TaskResult

class SQLAgent(Agent):
    name = "sql"
    capabilities = (Capability.CODING,)
    priority = 9          # outranks the generic coding agent

    async def handle(self, task):
        response = await self.think(task.input)
        return TaskResult(task_id=task.id, agent=self.name, output=response.content)

registry.register_class(SQLAgent)
```

---

## Model routing

| Provider | Type | Notes |
|---|---|---|
| `builtin` | offline | always available, zero config, final fallback |
| `ollama` | local | auto-detected at `localhost:11434` |
| `lmstudio` | local | OpenAI-compatible server |
| `openai` | cloud | also drives vLLM and any compatible endpoint |
| `claude` | cloud | Anthropic Messages API |
| `gemini` | cloud | Google Generative Language API |
| `openrouter` | cloud | multi-model gateway |

Seven routing modes — `local_first` (default), `cloud_first`, `automatic`,
`performance`, `privacy`, `offline`, `manual` — with **automatic failover**:
an unhealthy or erroring provider is skipped and the next candidate tried, so a
request never dies because one backend is down.

Tasks route independently, so reasoning can hit Claude while coding stays local:

```yaml
# config/models.yaml
models:
  routing_mode: local_first
  coding: local
  reasoning: claude
```

---

## Interface

React 19 + TypeScript, built with Vite and Tailwind. The same bundle runs in
both hosts, detected at runtime:

| Host | Loads from | Transport |
|---|---|---|
| Desktop | local files in the native window | direct Python bridge, in-process |
| Browser | `aera serve` | REST + server-sent events |

```bash
cd interface
npm install
npm run build     # emits to aera/desktop/ui-react/, picked up automatically

npm run dev       # hot reload against a running `aera serve`
```

The Dashboard follows `docs/04-DASHBOARD.md`: grouped top navigation, hologram
and workspace on the left, a canvas particle sphere over **Tap to Speak** in the
centre, and a HUD transcript panel on the right that accepts drag & drop.

Every page is now built against live backend data. Settings holds exactly three
sections — AI, Voice, System — with advanced pages nested inside them, and
plugin management lives in Apps. Where a capability genuinely does not exist
(media download, device pairing) the page says so at the point of use rather
than offering a control that fails silently.

React is the only UI. There was once a dependency-free HTML/CSS/JS fallback
in `aera/desktop/ui/` and a second hand-written dashboard in `aera/web/`, but
three copies of the same screens drifted apart — a palette or logo change had
to be made in three places and one was always stale. Both are gone; `aera` and
`aera serve` load the same built bundle, so the interface must be built first:

```bash
cd interface && npm install && npm run build
```

---

## API

128 REST operations plus a WebSocket gateway. Every response uses a consistent
envelope.

```http
POST /api/v1/chat                 main conversational entry point
POST /api/v1/memory/search        hybrid semantic + graph recall
POST /api/v1/memory/graph         node/edge slice for visualisation
GET  /api/v1/agents               roster, status and capability map
POST /api/v1/agents/task          dispatch to a specific agent
POST /api/v1/workspace/open       open and index a project
POST /api/v1/automation/run       execute a workflow
POST /api/v1/voice/speak          TTS with emotion + viseme timing
POST /api/v1/voice/sing           lyrics -> note plan (pitch, beat, bar)
POST /api/v1/voice/music/analyse  metre, rhyme, structure, syllables
GET  /api/v1/system/status        full system snapshot
WS   /ws                          token streaming and live events
```

```bash
curl -X POST localhost:8080/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "write a python retry decorator"}'
```

```json
{
  "success": true,
  "message": "Response generated",
  "data": {
    "agent": "coding",
    "output": "...",
    "data": { "intent": "coding", "confidence": 0.85, "routed_to": "coding" },
    "conversation_id": "a3f9c2b18e04"
  }
}
```

Set `"stream": true` for server-sent events, or use the WebSocket for
bidirectional streaming with live agent/memory events.

---

## Automation

Declarative workflows with variables, conditionals, bounded loops and manual,
scheduled or event-driven triggers.

```python
engine.create(
    name="document-on-commit",
    triggers=[Trigger(type=TriggerType.EVENT, value="git.commit")],
    actions=[
        Action(type=ActionType.AGENT_TASK,
               params={"capability": "documentation", "input": "document the changes"},
               store_as="docs"),
        Action(type=ActionType.MEMORY_STORE,
               params={"title": "Changelog", "content": "{{ docs }}"}),
        Action(type=ActionType.NOTIFY, params={"message": "Docs updated"}),
    ],
)
```

Conditions are evaluated structurally — there is no `eval()` anywhere in the
execution path.

---

## Configuration

Layered, with each layer overriding the last:

```
defaults  →  config/*.yaml  →  AERA_* env vars  →  explicit overrides
```

```bash
AERA_API__PORT=9000
AERA_MODELS__ROUTING_MODE=cloud_first
AERA_LOGGING__LEVEL=DEBUG
```

Every section is a validated Pydantic model, so a bad value fails at startup
with a precise message instead of at first use. See `config/` for annotated
defaults covering system, api, models, memory, agents, voice, workspace,
security, settings, database and logging.

---

## Security

- **Encrypted vault** — Fernet-encrypted API keys, `0600` master key outside the repo
- **Zero-trust permissions** — 6 roles, 12 permissions, per-principal grant/revoke
- **Sandboxed filesystem** — workspace reads cannot escape the project root
- **Terminal allowlist** — shell execution disabled by default; only allowlisted binaries when enabled
- **Auth + rate limiting** — bearer/API-key auth, 100 req/min default
- **Audit log** — append-only record of security-relevant events

Secrets are never returned by the API: `/system/secrets` responds with masked
values only.

---

## Testing

```bash
./scripts/test.sh                    # 1,965 Python tests, then ruff
cd interface && npm test             # 25 TypeScript tests
pytest tests/test_memory.py -v       # one module
```

| Module | Tests | Covers |
|---|---|---|
| `test_memory.py` | 38 | graph CRUD, traversal, ranking, persistence |
| `test_core.py` | 36 | config layering, event bus, vault, permissions |
| `test_agents.py` | 50 | intent routing, lifecycle, sandboxing |
| `test_ai.py` | 33 | provider adapters, failover, routing modes |
| `test_api.py` | 66 | all endpoints, auth, rate limits, WebSocket |
| `test_subsystems.py` | 63 | workspace, automation, voice, hologram, kernel |
| `test_desktop.py` | 45 | kernel thread, native bridge, streaming, dialogs, sandboxing |
| `test_requirements.py` | 29 | tap-to-memory, ethical-hacking scope, extended roster |
| `test_media_agents.py` | 30 | document parsing, capability gating, SSRF guard |
| `test_languages.py` | 252 | 35 language packs, per-language numbers, cue sweep |
| `test_scripts.py` | 187 | visemes across 9 writing systems, script detection |
| `test_music.py` | 124 | syllables, metre, rhyme, tempo, scales, note plans |
| `test_documentation.py` | 180 | every documented count and the agent roster asserted against the code |
| `test_phonetics.py` | 47 | spoken-form normalisation, grapheme visemes |
| `test_expression.py` | 49 | mood decay, negation scope, prosody, SSML |
| `test_voice_personas.py` | 56 | anime-g / anime-b acoustics, per-emotion timbre |
| `test_voice_backends.py` | 30 | Piper and system TTS probing, fallback |
| `interface/src/__tests__` | 294 | components rendered in jsdom, language picker, layout, transport |

Tests run fully offline and deterministically — no network, no API keys, no
model downloads.

---

## Project layout

```
aera/
├── core/         config, event bus, errors, logging, kernel
├── memory/       graph, embeddings, engine
├── ai/           provider adapters and the model router
├── agents/       base framework, registry, 15 specialists
├── workspace/    project scanner and indexer
├── automation/   workflow engine
├── voice/        STT/TTS pipeline, emotion, 35 language packs, visemes, singing
├── hologram/     avatar state machine
├── security/     vault, permissions, audit
├── api/          FastAPI app, routers, middleware
└── desktop/      native window, JS bridge, preferences, built UI

interface/        React + TypeScript front end — the only UI
├── src/document.ts   the HTML shell; index.html is generated from it
├── src/pages/        one directory per feature area
├── src/components/   shared UI primitives
├── src/design-system/ colours, typography, spacing, themes, global CSS
├── src/store/        Zustand state
├── src/services/     typed client and host-agnostic transport
└── vite-plugins/     generates index.html and globals.css at build time

assets/brand/     generated banner, icons and social card
installer/        PyInstaller spec and frozen entrypoint
config/           annotated YAML defaults
docs/             the original design specification (108 documents)
scripts/          install, run, test, build, build-desktop, clean
tools/brand/      regenerates the brand assets from code
tools/meshgen/    placeholder hologram meshes
tests/            1,965 Python tests
```

---

## Implementation status

Built and tested against the specification in `docs/`:

| Subsystem | Status |
|---|---|
| Memory graph, hybrid recall, consolidation | ✅ complete |
| Agent framework + 15 specialists | ✅ complete |
| Model router, 7 providers, failover | ✅ complete |
| REST API (128 operations) + WebSocket | ✅ complete |
| Workspace indexer, symbol extraction | ✅ complete |
| Automation engine, triggers, workflows | ✅ complete |
| Security: vault, permissions, audit | ✅ complete |
| Voice pipeline, emotion, visemes | ✅ orchestration complete; audio backends pluggable |
| Hologram avatar state | ✅ state machine complete; renderer is client-side |
| Desktop application (native window, menus, dialogs) | ✅ complete |
| React + TypeScript interface | ✅ complete |
| Standalone executable packaging | ✅ spec complete — binaries build in CI |
| Browser dashboard for headless mode | ✅ complete |
| PostgreSQL / pgvector backend | ⬜ planned — SQLite + in-process graph today |
| Docker: containers, images, volumes, networks, logs, stats | ✅ complete — Engine API over the Unix socket |
| Audio transcription (AudioAgent → STT backend) | ✅ wired end to end — no STT engine bundled |
| Vision / image understanding | ⬜ router has no multimodal transport — agent says so |
| OCR (Tesseract) | ✅ wired — activates when pytesseract is installed |
| Plugin discovery, manifests, permission gating | ✅ complete — 15 permissions, partial approval |
| Plugin code execution | ⬜ needs process isolation — refused explicitly, never a silent no-op |
| Terminal UI, plugin marketplace | ⬜ planned — status shown in-app |
| Phone sync, desktop app integrations | ⬜ planned — no Device Agent |

The voice engine implements the full pipeline (VAD → STT → intent → memory →
LLM → emotion → TTS → lip-sync) with headless backends; plugging in Whisper or
Piper is an interface implementation, not a rewrite.

**Languages.** 35 packs supply emotion cues, negation, intensifiers and number
words; the analysis machinery around them is language-independent. Numbers
follow each language's own grammar rather than English word order — German
*siebenundachtzig*, French *quatre-vingt-sept*, Hindi *सत्तासी*, and lakh/crore
grouping across the subcontinent. Twelve packs deliberately keep numerals
instead of guessing: Japanese and Korean readings depend on the counter that
follows, and ten Indic packs have irregular 21-99 forms not carried here.
`GET /api/v1/voice/languages` reports which case each language is in.

**Singing** is a separate layer, because sung pitch is quantised to a scale
where spoken pitch glides, sung timing is fixed by the bar where spoken timing
follows stress, and the unit is the syllable rather than the word. `sing()`
returns a note plan — which syllable, at what pitch, in which bar, for how
long — derived from the words themselves: syllable count, stress placement,
phrase endings. Syllable counting works in every script the language packs
cover, so lyrics are not English-only. Emotion picks the key, tempo and time
signature. It is a note plan, not audio; rendering it still needs a real voice
model, and the endpoint says so rather than returning silence.

Lip-sync covers nine writing systems with real articulation — Latin, Cyrillic,
Greek, Arabic, Hebrew, the Indic abugidas, Thai, Kana and Hangul. Han gets
syllable timing only, because mapping a character to its reading needs a
dictionary AERA does not bundle; Georgian, Armenian, Ethiopic, Lao, Khmer and
Myanmar are recognised and get the same timing-only treatment until they have
tables. `ALPHABETIC` and `TIMING_ONLY` in `aera/voice/scripts.py` state which,
and an import-time check keeps the claim honest.

**On packaging:** the PyInstaller spec, frozen entrypoint and cross-platform
workflow are complete and every bundled import is verified, but the binaries
have not been linked and launched here — this development sandbox is headless
and lacks `libpython3.11.so`. `ci/github-actions-desktop.yml` builds all three
platforms, checks the bundle contents and smoke-tests the frozen app under a
virtual display; run it once to produce release artifacts.

---

## License

MIT

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
