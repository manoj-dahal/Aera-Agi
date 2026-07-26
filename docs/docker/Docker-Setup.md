# Docker Setup

Version: 1.0.0

Status: Stable

Priority: Critical

---

# Overview

Docker is the primary containerization platform used by AERA.

Every core service runs inside isolated containers, making the platform portable, secure, scalable, and easy to deploy across Windows, Linux, macOS, servers, edge devices, and cloud infrastructure.

---

# Objectives

- Containerized Architecture
- Cross-Platform Deployment
- Service Isolation
- Easy Updates
- Scalability
- GPU Support
- High Availability
- Development Environment
- Production Deployment
- Container Orchestration

---

# Requirements

Minimum

- Docker 27+
- Docker Compose v2
- 8 GB RAM
- 4 CPU Cores
- 30 GB Storage

Recommended

- Docker 28+
- NVIDIA GPU
- 32 GB RAM
- 8+ CPU Cores
- NVMe SSD

---

# Install Docker

## Windows

Install

- Docker Desktop
- WSL2
- Ubuntu (Recommended)

---

## Linux

Ubuntu

```bash
sudo apt update

sudo apt install docker.io docker-compose-v2

sudo systemctl enable docker

sudo systemctl start docker
```

---

## Verify

```bash
docker --version

docker compose version
```

---

# Project Structure

```
AERA/

docker/

compose/

configs/

volumes/

logs/

Dockerfile

docker-compose.yml

.env
```

---

# Environment

```
.env

APP_NAME=AERA

APP_PORT=8080

API_PORT=8081

DB_PORT=5432

REDIS_PORT=6379

OLLAMA_PORT=11434

LOG_LEVEL=INFO
```

---

# Docker Services

```
Core

API

Dashboard

Memory

PostgreSQL

Redis

ChromaDB

Ollama

Nginx

Monitoring
```

---

# Startup

```bash
docker compose up -d
```

---

# Stop

```bash
docker compose down
```

---

# Restart

```bash
docker compose restart
```

---

# View Containers

```bash
docker ps
```

---

# Logs

```bash
docker compose logs

docker compose logs core

docker compose logs api
```

---

# Build

```bash
docker compose build
```

---

# Update

```bash
docker compose pull

docker compose up -d
```

---

# Volumes

Persistent

- Database
- Memory
- Logs
- Models
- Cache
- Workspace

---

# Networks

```
frontend

backend

database

ai-network
```

---

# Health Checks

Every container exposes

```
/health
```

Example

```
Core

↓

Healthy

↓

API

↓

Dashboard

↓

Ready
```

---

# Security

- Read-only containers
- Secret management
- Isolated networks
- Resource limits
- Signed images

---

# Summary

Docker provides a portable, scalable, and secure runtime for the entire AERA platform.