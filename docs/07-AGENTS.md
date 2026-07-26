# 07 - AGENTS

Version: 1.0.0

Status: Design Specification

---

# Overview

The Agent System is the intelligence layer of AERA.

Instead of relying on a single AI model for every task, AERA uses multiple specialized AI agents that collaborate through a shared Memory Graph.

Each agent has a dedicated responsibility but shares context, memory, and project knowledge with every other agent.

---

# Design Goals

- Modular
- Specialized
- Shared Memory
- Background Execution
- Scalable
- Intelligent Collaboration
- Automatic Task Routing

---

# Agent Architecture

```
                    User
                      │
                      ▼
                AI Core Manager
                      │
      ┌───────────────┼────────────────┐
      ▼               ▼                ▼
 Agent Router   Memory Graph     Model Router
      │               │                │
      ▼               ▼                ▼
 Specialized Agents   Shared Memory   AI Models
      │
      ▼
 Task Execution
```

---

# Agent Workflow

```
User Request

↓

AI Core

↓

Intent Detection

↓

Memory Recall

↓

Agent Selection

↓

Task Execution

↓

Memory Update

↓

Response
```

---

# Agent Roster

**34 agents are implemented. 31 are enabled by default.**

This table is generated from the agent classes and asserted against them by
`tests/test_documentation.py`. The per-agent sections that used to stand here
described twenty agents, omitted fourteen that exist, and included a Gallery
Agent that has never been written.

| Agent | Default | Purpose |
|---|---|---|
| `audio` | off | Transcribes and analyses audio recordings. |
| `automation` | on | Designs automation workflows and runs them through the engine. |
| `backup` | on | Creates and reports on memory graph backups. |
| `code_review` | on | Reviews code for bugs, security issues, performance and style. |
| `coding` | on | Writes, explains, refactors and tests code in Python, Dart, JavaScript, TypeScript, Go, Rust, Java, C#, C++, Swift, Kotlin, PHP, Ruby and SQL. |
| `collaboration` | on | Coordinates shared context and multi-agent handoffs. |
| `conversation` | on | Handles natural conversation with continuity across sessions. |
| `core` | on | Master coordinator that detects intent, recalls memory, selects specialised agents and assembles the final response. |
| `debug` | on | Analyses stack traces and failing behaviour, then proposes a fix. |
| `device` | on | Reports host machine details and manages connected devices. |
| `document` | on | Reads, summarises and answers questions about documents. |
| `ethical_hacking` | on | Assists with authorised defensive security work: vulnerability review, hardening guidance and threat modelling. |
| `git` | on | Analyses repositories, drafts commit messages and explains Git workflows. |
| `learning` | on | Detects patterns and preferences across the memory graph. |
| `memory` | on | Manages memory storage, recall, consolidation and graph maintenance. |
| `monitoring` | on | Monitors subsystem health and reports anomalies. |
| `network` | on | Runs local network diagnostics and connectivity checks. |
| `notification` | on | Formats and dispatches notifications to the dashboard. |
| `ocr` | on | Extracts text from images and scanned documents. |
| `performance` | on | Monitors system performance and suggests optimisations. |
| `personalization` | on | Tracks user preferences and adapts AERA's behaviour. |
| `planning` | on | Decomposes goals into ordered steps with dependencies and estimates. |
| `reasoning` | on | Performs step-by-step analysis, comparison and explanation. |
| `research` | on | Gathers and organises technical knowledge, then summarises findings. |
| `scheduler` | on | Manages scheduled jobs and reports on upcoming automation. |
| `security` | on | Reviews security posture, permissions and vulnerabilities. |
| `terminal` | off | Runs allowlisted shell commands and explains their output. |
| `translation` | on | Translates text between languages and corrects grammar. |
| `update` | on | Tracks component versions and reports available updates. |
| `vision` | on | Analyses images and screenshots using a vision-capable model. |
| `voice` | on | Controls speech synthesis, listening sessions and emotion. |
| `web` | off | Fetches and summarises public web pages. |
| `workspace` | on | Analyses project structure, indexes files and answers questions about them. |
| `writing` | on | Produces documentation, reports, summaries and technical prose. |

---

# Agents that are off by default

Each of these can act outside the process, so switching it on is a decision
rather than a default.

| Agent | Why | To enable |
|---|---|---|
| `terminal` | Executes shell commands | `agents.terminal`, `security.allow_terminal`, and an allowlist |
| `web` | Makes outbound requests | `agents.web` and `security.allow_network` |
| `audio` | Needs a speech-to-text engine that is not bundled | `agents.audio` |

---

# Not implemented

There is no Gallery Agent. `docs/agents/Gallery-Agent.md` describes one as a
"Core System Agent"; no such class has ever existed. Media work is split
between the `vision`, `ocr` and `document` agents.

The `vision` agent is registered and enabled, but reports the missing model
rather than describing an image it cannot see.


---

# Agent Collaboration

All agents communicate through:

- Memory Graph
- Context Engine
- AI Core
- Event Bus
- Task Queue

No agent communicates directly with another.

---

# Shared Memory

Every agent can:

- Read Context
- Store Memory
- Update Knowledge
- Access Active Project
- Share Results

---

# Background Execution

Agents normally execute silently.

Examples

- Project indexing
- Memory updates
- Context building
- Learning
- Monitoring
- Performance optimization

The user only sees the final result unless additional details are requested.

---

# Agent Priority

Priority Levels

Level 1

- Core Agent
- Memory Agent

Level 2

- Planning Agent
- Coding Agent
- Voice Agent

Level 3

- Workspace Agent
- Vision Agent
- Automation Agent
- Research Agent

Level 4

- Update Agent
- Notification Agent
- Learning Agent

---

# Error Handling

If an agent fails:

1. Log the error
2. Retry if appropriate
3. Notify the Core Agent
4. Select an alternative strategy
5. Preserve user context

---

# Performance Goals

- Fast task routing
- Low resource usage
- Background execution
- Shared context
- Scalable architecture
- Easy extensibility

---

# Future Agents

Potential future additions

- Finance Agent
- Calendar Agent
- Email Agent
- Presentation Agent
- Meeting Agent
- Cloud Infrastructure Agent
- Robotics Agent
- Data Science Agent
- Database Agent

---

# Summary

The Agent System enables AERA to divide complex work across specialized AI agents while maintaining a unified experience through shared memory and centralized coordination. This architecture improves scalability, maintainability, and overall intelligence without increasing interface complexity.

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
