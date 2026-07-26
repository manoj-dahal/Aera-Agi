# 27 - DOCKER

Version: 1.0.0

Status: Core Infrastructure Specification

---

# Overview

Docker provides the containerized runtime environment for AERA.

Every major component can run independently as a Docker container while communicating through the internal network. This architecture simplifies development, testing, deployment, upgrades, backups, and scaling.

AERA supports both **single-container** and **multi-container** deployments using Docker Compose.

---

# Objectives

- Containerized Architecture
- Easy Deployment
- Cross Platform
- GPU Support
- Modular Services
- Secure Isolation
- Easy Updates
- Scalable Infrastructure

---

# Architecture

```
                  Docker Engine
                        │
                        ▼
                Docker Compose
                        │
 ┌─────────────┬─────────────┬─────────────┐
 ▼             ▼             ▼
Frontend    Backend      AI Services
 │             │             │
 └─────────────┼─────────────┘
               ▼
          Memory Graph
               │
               ▼
          PostgreSQL
```

---

# Container Architecture

```
AERA

├── frontend
├── backend
├── api
├── ai-router
├── memory
├── agents
├── automation
├── voice
├── hologram
├── websocket
├── nginx
├── database
├── redis
├── monitoring
└── updater
```

---

# Core Containers

## Frontend

Responsibilities

- Dashboard
- Workspace UI
- Voice UI
- Settings
- Applications
- Hologram UI

---

## Backend

Responsibilities

- Business Logic
- API Gateway
- Authentication
- Service Management
- Configuration

---

## AI Router

Responsibilities

- Route AI Requests
- Select Models
- Load Balance
- Failover
- Streaming

---

## Memory Service

Responsibilities

- Memory Graph
- Embeddings
- Context Storage
- Search
- Recall

---

## Agent Service

Runs

- Core Agent
- Coding Agent
- Voice Agent
- Planning Agent
- Security Agent
- Research Agent
- Device Agent

---

## Automation Service

Responsibilities

- Workflow Engine
- Scheduler
- Event System
- Task Queue

---

## Voice Service

Runs

- STT
- TTS
- Emotion Engine
- Voice Activity Detection
- Wake Word Detection

---

## Hologram Service

Responsibilities

- Avatar Rendering
- Lip Sync
- Emotion Rendering
- Animation
- Gesture Engine

---

## Database

Stores

- Memory
- Settings
- Agents
- Workspaces
- Plugins
- Logs
- Automation

Recommended

- PostgreSQL

---

## Redis

Responsibilities

- Cache
- Session Storage
- Message Queue
- Event Queue
- Streaming Buffer

---

## Nginx

Provides

- Reverse Proxy
- SSL
- Load Balancing
- Static Files
- API Routing

---

# Network

Docker network

```
aera-network
```

Containers communicate internally.

```
Frontend

↓

Backend

↓

API

↓

AI Router

↓

Memory

↓

Database
```

---

# Volumes

Persistent storage

```
volumes/

├── database
├── memory
├── logs
├── cache
├── models
├── plugins
├── uploads
├── backups
└── config
```

---

# Environment Variables

```
APP_PORT

DATABASE_URL

REDIS_URL

API_PORT

JWT_SECRET

OPENAI_KEY

GOOGLE_KEY

CLAUDE_KEY

LOCAL_LLM_URL

GPU_ENABLED
```

---

# GPU Support

Supported

- NVIDIA CUDA
- AMD ROCm
- Apple Metal (host dependent)

Capabilities

- AI Inference
- Voice Models
- Vision Models
- Rendering

---

# Docker Compose

Example services

```
frontend

backend

database

redis

memory

ai-router

voice

agents

automation

nginx
```

---

# Startup Sequence

```
Docker Start

↓

Database

↓

Redis

↓

Memory

↓

Backend

↓

API

↓

AI Router

↓

Agents

↓

Frontend

↓

Ready
```

---

# Health Checks

Every container reports

- Status
- CPU Usage
- Memory Usage
- Uptime
- Response Time

Possible states

- Healthy
- Starting
- Restarting
- Unhealthy
- Stopped

---

# Logging

Logs collected from

- Backend
- API
- AI Router
- Agents
- Voice
- Database
- Nginx
- Docker

Centralized logging supported.

---

# Monitoring

Monitors

- CPU
- RAM
- GPU
- Containers
- API
- Database
- AI Models
- Agents

---

# Scaling

Supports

- Horizontal Scaling
- Vertical Scaling
- Multiple AI Workers
- Multiple API Workers
- Multiple Agent Workers
- Distributed Services

---

# Security

Container security

- Non-root Containers
- Read-only Filesystems (where practical)
- Secret Management
- Network Isolation
- Resource Limits
- Image Verification

---

# Backup

Backup includes

- Database
- Memory Graph
- Configuration
- Plugins
- AI Models
- Logs
- Uploaded Files

---

# Recovery

```
Container Failure

↓

Restart

↓

Health Check

↓

Restore Services

↓

Continue
```

---

# Configuration

```
docker/

├── Dockerfile
├── docker-compose.yaml
├── compose.dev.yaml
├── compose.prod.yaml
├── nginx.conf
├── redis.conf
├── postgres.conf
├── .env.example
└── healthcheck.sh
```

---

# Performance

Optimizations

- Layer Caching
- Multi-stage Builds
- BuildKit
- Resource Limits
- GPU Allocation
- Shared Volumes
- Lazy Service Startup

---

# Future Features

Planned

- Kubernetes Support
- Docker Swarm
- Multi-Node Deployment
- Auto Scaling
- Service Mesh
- Distributed Memory Graph
- Cloud Native Deployment
- Edge Deployment

---

# Recommended Resource Requirements

| Environment | CPU | RAM | Storage |
|-------------|-----|-----|---------|
| Minimum | 4 Cores | 8 GB | 50 GB |
| Recommended | 8 Cores | 16 GB | 100 GB |
| AI Development | 12+ Cores | 32 GB | 250 GB |
| Enterprise | 16+ Cores | 64 GB | 500 GB+ |

---

# Summary

The Docker infrastructure provides a modular, secure, and scalable deployment platform for AERA. By separating each subsystem into dedicated containers—including the frontend, backend, AI Router, Memory Graph, agents, voice services, automation, database, and monitoring—it enables reliable deployment, efficient resource management, simplified maintenance, and future horizontal scaling.

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
