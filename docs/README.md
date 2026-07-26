# AERA AI Operating System

> Next-Generation Personal AI Operating System

---

# Overview

AERA is an intelligent AI operating system designed to function as a unified AI voice assistant, development environment, automation platform, and personal knowledge system.

Unlike traditional assistants, AERA maintains persistent memory, understands project context, manages connected applications, operates with local and cloud AI models, and provides an interactive holographic AI interface.

The platform is modular, scalable, privacy-focused, and designed for professional, creative, and technical workflows.

---

# Vision

Create a truly intelligent AI companion capable of:

- Remembering conversations
- Understanding long-term projects
- Automating workflows
- Assisting with coding
- Managing documents
- Controlling connected applications
- Operating both locally and in the cloud
- Providing natural voice interaction
- Learning continuously while respecting user privacy

---

# Core Principles

- Local First
- Privacy First
- AI Native
- Modular Architecture
- Shared Memory System
- Human-Centered Interaction
- Extensible Platform

---

# Major Modules

- Dashboard
- Macros
- Memory Graph
- Workspace
- Applications
- Gallery
- Phone
- Settings
- Voice System
- Hologram Avatar
- Automation Engine

---

# Dashboard

The Dashboard is the central workspace.

Features include:

- 3D AI Hologram
- AI Core
- Tap to Speak
- Workspace Panel
- Transcript Panel
- Background Drag & Drop
- System Status
- Running Tasks

---

# Macros

Macros provides the AI Brain.

Features:

- Memory Graph
- Long-Term Memory
- Short-Term Memory
- Working Memory
- Context Memory
- Memory Recall
- Memory Synchronization

---

# Applications

Applications allow AERA to integrate with desktop software.

Examples:

- Terminal
- Git
- VS Code
- Blender
- Photoshop
- Premiere
- DaVinci Resolve
- Custom Applications

---

# Workspace

Workspace manages local projects.

Capabilities:

- Open Local Folder
- Project Explorer
- AI Context
- File Analysis
- Source Code Indexing

---

# Gallery

Media management.

Supports:

- Images
- Videos
- Local folders
- Preview
- AI Analysis

---

# Phone

Phone integration.

Supports:

- Android
- iPhone
- Notifications
- Messages
- Device Status

---

# Settings

Three primary sections:

- AI
- Voice
- System

---

# Voice System

Features:

- Speech Recognition
- Text to Speech
- Emotion Engine
- Natural Conversation
- Voice Memory
- Interrupt Handling

---

# AI Models

Supported:

## Local

- Ollama
- llama.cpp
- Local LLMs

## Cloud

- OpenAI
- Google Gemini
- Anthropic Claude
- OpenRouter
- Custom APIs

---

# Agent System

Examples:

- Core Agent
- Memory Agent
- Coding Agent
- Terminal Agent
- Git Agent
- Research Agent
- Voice Agent
- Vision Agent
- Planning Agent
- Automation Agent
- Security Agent
- Device Agent

All agents share the same memory system.

---

# Background Services

Runs automatically:

- Memory Engine
- Context Engine
- Agent Scheduler
- AI Router
- Voice Engine
- Update Service
- Performance Monitor
- Security Service
- Logging
- Diagnostics

---

# Security

- Local Encryption
- Permission System
- Secure API Storage
- Local Memory Protection
- Session Isolation

---

# Architecture

```
User
   │
Dashboard
   │
AI Core
   │
Agent Manager
   │
Memory Graph
   │
LLM Router
   │
Applications
```

---

# Technology Stack

Frontend

- Flutter

Backend

- FastAPI
- Python

AI

- Ollama
- llama.cpp
- OpenAI
- Gemini
- Claude

Database

- SQLite
- PostgreSQL

Vector Database

- ChromaDB
- FAISS

Deployment

- Docker
- Docker Compose
- Kubernetes

---

# Project Goals

- Fully modular
- Offline capable
- Fast
- Extensible
- Cross-platform
- Enterprise-ready

---

# Roadmap

Phase 1

- Dashboard
- Workspace
- Memory
- Voice

Phase 2

- Agent System
- Applications
- Automation

Phase 3

- Hologram
- Local AI
- Multi-Agent Collaboration

Phase 4

- AI Operating System
- Marketplace
- Plugin SDK

---

# License

Copyright © AERA AI

All rights reserved.

---

# Repository Structure

The documents in this directory are the original **design specification**.
`REQUIREMENTS.md` at the repository root is the **conformance record**: what
is built, what is built with a limit, and what is not built at all. Where the
two differ, that file is what exists.

```
AERA/
├── aera/          the Python package: kernel, agents, memory, voice, api
├── interface/     React + TypeScript front end, the only UI
├── tests/         1,845 tests
├── docs/          this documentation set
├── config/        layered YAML configuration
├── installer/     PyInstaller spec
├── ci/            build workflows
├── tools/         brand and asset generation
├── REQUIREMENTS.md  what is built, and what is not
└── README.md
```

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
