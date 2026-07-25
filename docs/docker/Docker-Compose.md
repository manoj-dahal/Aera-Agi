# Docker Compose

Version: 1.0.0

---

# Overview

Docker Compose orchestrates every AERA service.

---

# Services

```
core

api

dashboard

postgres

redis

chromadb

ollama

nginx

monitoring
```

---

# Example

```yaml
services:

  core:
    build: .
    ports:
      - "8080:8080"

  postgres:
    image: postgres:17

  redis:
    image: redis:7
```

---

# Commands

Start

```bash
docker compose up -d
```

Stop

```bash
docker compose down
```

Restart

```bash
docker compose restart
```

Rebuild

```bash
docker compose up --build
```

---

# Profiles

- Development
- Production
- GPU
- Testing

---

# Summary

Docker Compose manages all AERA containers together.