# AERA

**Artificial Enhanced Reasoning Assistant** — a modular AI Operating System with a
persistent memory graph, multi-agent orchestration and local-first model routing.

[![tests](https://img.shields.io/badge/tests-286%20passing-brightgreen)]()
[![python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![license](https://img.shields.io/badge/license-MIT-lightgrey)]()

AERA is not a chatbot wrapper. It is a runtime: requests enter through a Core
Agent that detects intent, recalls relevant memory, delegates to a specialist
agent, and writes the outcome back into a shared knowledge graph that every
other agent can read.

---

## Quick start

```bash
git clone https://github.com/manoj-dahal/Aera-Agi.git
cd Aera-Agi
./scripts/install.sh

source .venv/bin/activate
aera serve
```

Open **http://localhost:8080** for the dashboard, `/docs` for the interactive
API reference.

**No API keys required.** AERA ships with a built-in offline reasoner, so the
full stack — memory, agents, routing, automation, voice pipeline — runs with
zero configuration and zero network access. Add a local or cloud model when you
want production-grade generation.

### Docker

```bash
docker compose up -d                      # core only, offline
docker compose --profile local-ai up -d   # + Ollama for local LLMs
docker compose --profile full up -d       # + PostgreSQL and Redis
```

### Command line

```bash
aera serve                    # API + dashboard
aera repl                     # interactive session
aera chat "explain CQRS"      # one-shot query
aera index ~/projects/my-app  # index a codebase into memory
aera memory search "docker"   # query the memory graph
aera agents                   # list agents and their state
aera status                   # full system snapshot
```

---

## Architecture

```
                        Dashboard  ·  REST  ·  WebSocket
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

15 agents ship enabled by default, each declaring capabilities the router uses.

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

## API

63 REST operations plus a WebSocket gateway. Every response uses a consistent
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
./scripts/test.sh              # 286 tests
pytest tests/test_memory.py -v # one module
```

| Module | Tests | Covers |
|---|---|---|
| `test_memory.py` | 38 | graph CRUD, traversal, ranking, persistence |
| `test_core.py` | 36 | config layering, event bus, vault, permissions |
| `test_agents.py` | 50 | intent routing, lifecycle, sandboxing |
| `test_ai.py` | 33 | provider adapters, failover, routing modes |
| `test_api.py` | 66 | all endpoints, auth, rate limits, WebSocket |
| `test_subsystems.py` | 63 | workspace, automation, voice, hologram, kernel |

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
├── voice/        STT/TTS pipeline, emotion, visemes
├── hologram/     avatar state machine
├── security/     vault, permissions, audit
├── api/          FastAPI app, routers, middleware
└── web/          dashboard (HTML/CSS/JS, no build step)

config/           annotated YAML defaults
docs/             the original design specification (108 documents)
scripts/          install, run, test, build, clean
tests/            286 tests
```

---

## Implementation status

Built and tested against the specification in `docs/`:

| Subsystem | Status |
|---|---|
| Memory graph, hybrid recall, consolidation | ✅ complete |
| Agent framework + 15 specialists | ✅ complete |
| Model router, 7 providers, failover | ✅ complete |
| REST API (63 operations) + WebSocket | ✅ complete |
| Workspace indexer, symbol extraction | ✅ complete |
| Automation engine, triggers, workflows | ✅ complete |
| Security: vault, permissions, audit | ✅ complete |
| Voice pipeline, emotion, visemes | ✅ orchestration complete; audio backends pluggable |
| Hologram avatar state | ✅ state machine complete; renderer is client-side |
| Web dashboard | ✅ complete |
| Flutter desktop client | ⬜ planned — no Dart toolchain in this environment |
| PostgreSQL / pgvector backend | ⬜ planned — SQLite + in-process graph today |
| Plugin marketplace, phone sync, app integrations | ⬜ planned |

The voice engine implements the full pipeline (VAD → STT → intent → memory →
LLM → emotion → TTS → lip-sync) with headless backends; plugging in Whisper or
Piper is an interface implementation, not a rewrite.

---

## License

MIT
