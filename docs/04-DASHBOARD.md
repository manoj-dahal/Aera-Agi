# 04 - DASHBOARD

Version: 1.0.0

Status: Design Specification

---

# Overview

The Dashboard is the central workspace of AERA.

Every interaction starts from this screen. It provides access to AI conversations, workspace management, holographic visualization, project context, and system status.

The Dashboard is designed to remain clean while most AI processing runs in the background.

---

# Design Goals

- Clean UI
- Minimal distractions
- AI-first workflow
- Fast access
- Project awareness
- Persistent memory integration
- Voice-first interaction

---

# Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ Header                                                              │
├─────────────┬───────────────────────────────┬───────────────────────┤
│             │                               │   Transcript Pane     │
│AI Hologram  │                               │                       │
│──────────── │            AI Core            │                       │
│ Workspace   │                               │                       │
│ Panel       │                               │                       │
│             │          Tap to Speak         │                       │
│             │                               │                       │
├─────────────┴───────────────────────────────┴───────────────────────┤
│ Bottom Status Bar                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

# Components

## Header

Displays global information.

Features

- AERA Logo
- Current Project
- Connected AI Model
- Local LLM Status
- Cloud AI Status
- Network Status
- Notifications
- User Profile

---

# Left Sidebar

Navigation.

```
Dashboard
Macros
Apps
Gallery
Phone
Settings
```

The sidebar remains fixed on desktop and collapses on smaller screens.

---

# Workspace Panel

The Workspace Panel manages local projects.

## Header

Contains:

- Workspace Title
- Open Local Folder
- Search Workspace
- Refresh Workspace

---

## Project Explorer

Displays:

- Project folders
- Files
- Source code
- Images
- Documents
- Configuration files

---

## AI Context

Background services automatically:

- Index projects
- Build context
- Detect programming language
- Track active files
- Update project memory

No manual synchronization is required.

---

# Center Panel

The center is dedicated to the AI assistant.

---

## AI Hologram

A 3D holographic avatar representing AERA.

States

- Idle
- Listening
- Thinking
- Speaking
- Processing
- Error
- Offline

---

## Emotion System

Avatar expressions include:

- Neutral
- Happy
- Curious
- Confident
- Focused
- Thinking
- Excited
- Calm

Expressions synchronize with voice output.

---

## AI Core

Displayed beneath the hologram.

Shows:

- Active AI
- Current model
- Processing state
- Active agent
- Memory status

---

## Tap to Speak

Primary interaction button.

Workflow

```
Tap

↓

Voice Activation

↓

Background Memory Recall

↓

Intent Detection

↓

AI Processing

↓

Response

↓

Conversation Saved
```

---

# Transcript Panel

Located on the right side.

Displays:

- Conversations
- AI responses
- Reasoning summaries
- Task updates
- Generated code
- Analysis results

---

## Background Watermark

The transcript background contains a subtle AERA watermark.

Normally:

- Nearly invisible

During drag operation:

- Watermark glows
- Drop indicator appears
- Highlight animation starts

After file drop:

- Watermark returns to idle state

---

## Drag & Drop

Dashboard is the only location supporting drag & drop.

Supported items

- Files
- Folders
- Images
- Videos
- Audio
- PDFs
- Source code
- Archives

Drop workflow

```
Drag File

↓

Watermark Activated

↓

Drop

↓

AI Detects Content

↓

Appropriate Agent Selected

↓

Processing Begins

↓

Results Displayed
```

---

# Bottom Status Bar

Displays:

- CPU Usage
- GPU Usage
- RAM Usage
- Local Model Status
- Active Agent
- Running Tasks
- Background Services
- Connection Status

---

# Background Services

Invisible services include:

- Memory Recall
- Context Engine
- Workspace Indexer
- AI Router
- Agent Scheduler
- Local LLM Detection
- Voice Engine
- Logging
- Diagnostics
- Notification Service
- Performance Monitor

---

# Dashboard Workflow

```
Open Dashboard

↓

Load Workspace

↓

Restore Memory

↓

Initialize AI

↓

Load Active Project

↓

Start Background Services

↓

Ready
```

---

# User Workflow

```
User Opens Dashboard

↓

Selects Project

↓

Speaks

↓

AI Understands Context

↓

Agents Execute

↓

Results Appear

↓

Memory Updated
```

---

# Performance Goals

- Dashboard startup < 3 seconds
- Instant navigation
- Lazy loading
- GPU-accelerated hologram
- Background processing
- Minimal CPU usage while idle

---

# Accessibility

- Keyboard shortcuts
- Screen reader support
- Adjustable UI scaling
- High contrast mode
- Voice-first navigation

---

# Future Enhancements

- Multi-monitor support
- Collaborative dashboard
- Live agent visualization
- Custom dashboard widgets
- Plugin dashboard panels
- Real-time project analytics

---

# Summary

The Dashboard is the operational center of AERA. It combines workspace management, holographic AI interaction, voice communication, transcript visualization, and background intelligence into a single unified interface while keeping the experience clean and responsive.

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
