# 05 - MACROS

Version: 1.0.0

Status: Design Specification

---

# Overview

Macros is the intelligence center of AERA.

Unlike the Dashboard, which is designed for interaction, the Macros page is responsible for AI memory visualization and background intelligence management.

Almost every AI capability operates in the background while this page exposes only the Memory Graph and essential memory controls.

---

# Design Goals

- Clean Interface
- Memory-Centric Design
- Background AI Processing
- Shared Intelligence
- Visual Memory Representation
- Minimal User Interaction

---

# Layout

```
┌──────────────────────────────────────────────────────────────┐
│ Header                                                       │
├────────────────────────────────────┬─────────────────────────┤
│                                    │                         │
│                                    │          Memory Panel   │
│                                    │                         │
│      neural Memory Graph           │      • Short-Term Memory│
│                                    │       • Long-Term Memory│
│                                    │         • Working Memory│
│                                    │        • Semantic Memory│
│                                    │        • Episodic Memory│
│                                    │      • Procedural Memory│
│                                    │                         │
├───────────────────────────────────┴──────────────────────────┤
│ Background Status                                            │
└──────────────────────────────────────────────────────────────┘
```

---

# neural Memory Graph

The Memory Graph is the only primary visual component of the Macros page.

It represents the relationships between:

- Conversations
- Projects
- Files
- Tasks
- AI Decisions
- Agents
- Knowledge
- User Preferences

Each memory is displayed as a connected node.

---

# Graph Characteristics

Nodes

- Conversation
- Project
- File
- Task
- Idea
- Person
- Folder
- Agent
- Knowledge

Connections

- Related
- Parent
- Child
- Dependency
- Reference
- Timeline

---

# Memory Types Panel

Located on the right side.

Displays:

- Short-Term Memory
- Long-Term Memory
- Working Memory
- Semantic Memory
- Episodic Memory
- Procedural Memory

Selecting a memory type filters the graph.

---

# Shared neural Memory

Every AI agent accesses the same memory graph.

Supported agents include:

- Core Agent
- Memory Agent
- Coding Agent
- Terminal Agent
- Git Agent
- Voice Agent
- Vision Agent
- Planning Agent
- Research Agent
- Automation Agent
- Workspace Agent
- Security Agent
- Device Agent

No agent maintains a separate memory database.

---

# Background AI Skills

These operate automatically and are not displayed as UI components.

## Memory Engine

Responsibilities

- Store memory
- Update memory
- Compress memory
- Organize memory
- Remove duplicates

---

## Recall Engine

Responsibilities

- Context recall
- Project recall
- Conversation recall
- File recall
- Task recall

---

## Context Engine

Responsibilities

- Active project detection
- User intent understanding
- Workspace awareness
- Conversation continuity

---

## Knowledge Engine

Responsibilities

- Build relationships
- Link concepts
- Connect projects
- Organize information

---

## Learning Engine

Responsibilities

- Learn user workflow
- Improve recommendations
- Optimize future responses

---

## Agent Coordinator

Responsibilities

- Synchronize agents
- Share context
- Route tasks
- Balance workloads

---

# Memory Workflow

```
User Action

↓

Context Analysis

↓

Working Memory

↓

Memory Graph

↓

Knowledge Linking

↓

Long-Term Storage

↓

Future Recall
```

---

# Graph Interaction

Users can:

- Zoom
- Pan
- Select Nodes
- Expand Connections
- Collapse Branches
- Search Memory
- Filter by Memory Type

---

# Memory Node Information

Each node contains:

- Title
- Type
- Creation Time
- Last Updated
- Connected Nodes
- Importance Score
- Related Projects
- Related Agents

---

# Background Services

The following services always run automatically:

- Memory Engine
- Recall Engine
- Context Engine
- Knowledge Graph Builder
- Learning Engine
- Agent Synchronizer
- Memory Backup
- Memory Compression
- Duplicate Detection
- Relationship Builder
- Context Indexer

---

# Memory Synchronization

Synchronization occurs between:

- Dashboard
- Workspace
- Voice System
- Applications
- Gallery
- Phone
- AI Agents

All modules share the same memory graph.

---

# Performance

Goals

- Instant graph rendering
- Efficient memory indexing
- Low memory usage
- Fast search
- Background optimization

---

# Security

Memory protection includes:

- Encryption
- Permission validation
- Local storage
- Secure backup
- Session isolation

---

# Future Features

Planned enhancements include:

- 3D Memory Graph
- Timeline View
- Project Dependency View
- AI Insight Overlay
- Memory Health Dashboard
- Graph Analytics
- Collaborative Memory
- Visual Recall History

---

# Summary

The Macros page is the cognitive center of AERA. It presents a unified Memory Graph while all memory processing, learning, synchronization, and agent collaboration occur transparently in the background. This design keeps the interface simple while exposing the intelligence of the system through a single interactive graph.