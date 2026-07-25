# Core Agent

Version: 1.0.0

Status: Core System Agent

Priority: Critical

---

# Overview

The Core Agent is the central intelligence and orchestration layer of AERA.

It is responsible for coordinating every AI agent, managing conversations, routing tasks, selecting AI models, maintaining execution context, and ensuring all subsystems work together efficiently.

The Core Agent does **not** perform specialized tasks itself. Instead, it delegates work to specialized agents, monitors execution, and combines results into a unified response.

It is always active while AERA is running.

---

# Objectives

- Central AI Coordinator
- Agent Orchestration
- Task Routing
- Context Management
- Memory Integration
- Model Selection
- Conversation Management
- Event Coordination
- System Health Monitoring
- Resource Optimization

---

# Responsibilities

The Core Agent is responsible for

- Understanding user requests
- Planning task execution
- Selecting specialized agents
- Managing agent communication
- Tracking task progress
- Maintaining conversation context
- Selecting AI models
- Coordinating Memory Graph
- Handling failures
- Returning final responses

---

# Architecture

```
                     User

                      │

                      ▼

                 Core Agent

                      │

      ┌───────────────┼────────────────┐

      ▼               ▼                ▼

Memory Agent     Planning Agent   Reasoning Agent

      │               │                │

      └───────────────┼────────────────┘

                      ▼

            Specialized Agents

                      │

                      ▼

                Final Response
```

---

# Core Components

## Conversation Manager

Responsible for

- Session Management
- Conversation State
- Context Window
- User Intent
- Dialogue Flow

---

## Agent Manager

Responsibilities

- Agent Discovery
- Agent Startup
- Agent Shutdown
- Task Scheduling
- Agent Communication
- Health Monitoring

---

## Task Router

Determines

- Which agent to use
- Multiple agent execution
- Parallel execution
- Sequential execution
- Retry strategy

---

## AI Router

Responsible for

- Local LLM Selection
- Cloud AI Selection
- Model Switching
- Load Balancing
- Streaming

Supported providers

- Local LLM
- OpenAI
- Gemini
- Claude
- Custom Providers

---

## Context Manager

Maintains

- Current Conversation
- Workspace Context
- Open Files
- Running Tasks
- Active Agents
- User Preferences

---

## Memory Coordinator

Coordinates

- Memory Recall
- Memory Storage
- Graph Updates
- Memory Ranking
- Semantic Search

---

# Request Processing Pipeline

```
User Request

↓

Intent Detection

↓

Context Collection

↓

Memory Recall

↓

Task Planning

↓

Agent Selection

↓

Task Execution

↓

Result Validation

↓

Response Generation

↓

Memory Update

↓

Complete
```

---

# Agent Communication

Agents communicate using the internal Event Bus.

Example

```
User

↓

Core Agent

↓

Coding Agent

↓

Memory Agent

↓

Reasoning Agent

↓

Writing Agent

↓

Core Agent

↓

User
```

---

# Supported Agent Types

Core Agent can manage

- Memory Agent
- Coding Agent
- Terminal Agent
- Git Agent
- Voice Agent
- Audio Agent
- Vision Agent
- Planning Agent
- Reasoning Agent
- Research Agent
- Writing Agent
- Translation Agent
- Automation Agent
- Workspace Agent
- Device Agent
- Gallery Agent
- Security Agent
- Ethical-Hacking Agent
- Network Agent
- Performance Agent
- Learning Agent
- Update Agent
- Notification Agent

---

# Multi-Agent Collaboration

Example

```
Build Flutter App

↓

Planning Agent

↓

Coding Agent

↓

Terminal Agent

↓

Git Agent

↓

Performance Agent

↓

Documentation

↓

Core Agent
```

---

# Memory Integration

Uses

- Working Memory
- Short-Term Memory
- Long-Term Memory
- Semantic Memory
- Episodic Memory
- Memory Graph

Every interaction can update memory according to configured policies.

---

# Decision Engine

The Core Agent evaluates

- Task Complexity
- Required Skills
- Available Models
- Available Agents
- Resource Usage
- User Preferences
- Security Policies

---

# AI Model Selection

Routing examples

Simple Chat

↓

Small Local Model

---

Programming

↓

Coding Model

---

Vision

↓

Vision Model

---

Voice

↓

Speech Model

---

Reasoning

↓

Large Reasoning Model

---

Research

↓

Cloud Model (optional)

---

# Workspace Awareness

Tracks

- Open Projects
- Current File
- Cursor Position
- Active Editor
- Git Repository
- Running Terminal
- Build Status

---

# Background Services

Runs continuously

- Conversation Manager
- Agent Scheduler
- Context Manager
- Memory Synchronizer
- AI Router
- Health Monitor
- Event Dispatcher
- Task Queue
- Session Manager

---

# Error Recovery

```
Task Failed

↓

Detect Error

↓

Retry

↓

Alternative Agent

↓

Alternative Model

↓

Notify User

↓

Continue
```

---

# Security

Core Agent enforces

- Permission Validation
- Agent Isolation
- Secure API Access
- Memory Access Control
- Plugin Verification
- Audit Logging

The Core Agent cannot bypass system security policies.

---

# Performance Optimization

Features

- Parallel Agent Execution
- Lazy Agent Loading
- Context Compression
- Response Streaming
- Prompt Caching
- Agent Pooling
- Intelligent Scheduling

---

# State Machine

```
Idle

↓

Listening

↓

Thinking

↓

Planning

↓

Executing

↓

Waiting

↓

Generating

↓

Speaking

↓

Idle
```

---

# Internal Events

Published Events

- UserMessageReceived
- AgentStarted
- AgentCompleted
- MemoryUpdated
- WorkspaceChanged
- PluginLoaded
- ModelChanged
- ConversationEnded

Subscribed Events

- VoiceInput
- FileModified
- GitChanged
- AutomationTriggered
- NotificationReceived
- SystemStatusChanged

---

# Configuration

```
config/

├── core-agent.yaml
├── routing.yaml
├── scheduler.yaml
├── conversation.yaml
├── context.yaml
├── permissions.yaml
└── models.yaml
```

---

# Metrics

Monitors

- Active Conversations
- Running Agents
- Queue Length
- Average Response Time
- Memory Usage
- Token Usage
- AI Model Latency
- Agent Success Rate

---

# Future Features

Planned

- Self-Improving Agent Routing
- Dynamic Agent Creation
- Autonomous Task Decomposition
- Cross-Device Agent Coordination
- Distributed Multi-PC Execution
- AI Collaboration Optimization
- Predictive Task Planning
- Adaptive Conversation Intelligence

---

# Summary

The Core Agent is the brain of AERA. It orchestrates all specialized agents, manages conversations, coordinates memory, routes AI requests, maintains context, and ensures secure, efficient execution of every task. Rather than replacing specialized agents, it acts as an intelligent coordinator that brings together their capabilities into a seamless AI experience.