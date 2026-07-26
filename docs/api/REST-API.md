# REST API

Version: 1.0.0

Status: Stable

Priority: Critical

---

# Overview

The REST API is the primary communication interface for AERA.

It enables applications, plugins, dashboards, mobile apps, desktop apps, AI agents, and external services to securely communicate with the AERA Core Engine.

All APIs follow RESTful principles and return JSON responses.

---

# Base URL

```
http://localhost:8080/api/v1
```

Production

```
https://api.aera.ai/v1
```

---

# API Architecture

```
Client

↓

REST API Gateway

↓

Authentication

↓

Core Agent

↓

Service Router

↓

AI Agents

↓

Database
```

---

# Content Types

Request

```
application/json
```

Response

```
application/json
```

---

# Authentication

Supports

- JWT
- API Key
- OAuth2
- Session Token

Example

```
Authorization: Bearer <token>
```

---

# HTTP Methods

| Method | Description |
|---------|-------------|
| GET | Read Data |
| POST | Create |
| PUT | Update |
| PATCH | Partial Update |
| DELETE | Delete |

---

# Response Format

Success

```json
{
  "success": true,
  "message": "Completed",
  "data": {}
}
```

Error

```json
{
  "success": false,
  "error": "Unauthorized"
}
```

---

# API Modules

```
/auth
/users
/agents
/models
/memory
/workspace
/docker
/plugins
/projects
/settings
/files
/voice
/hologram
/system
```

---

# Agent APIs

```
GET    /agents

POST   /agents/start

POST   /agents/stop

POST   /agents/restart

GET    /agents/status
```

---

# Memory APIs

```
GET /memory/search

POST /memory/store

DELETE /memory/remove

GET /memory/history
```

---

# Workspace APIs

```
GET /workspace

POST /workspace/open

POST /workspace/index

GET /workspace/search
```

---

# Voice APIs

```
POST /voice/speak

POST /voice/listen

POST /voice/emotion

GET /voice/status
```

---

# Hologram APIs

```
POST /avatar/show

POST /avatar/hide

POST /avatar/emotion

POST /avatar/gesture
```

---

# Docker APIs

```
GET /docker/containers

POST /docker/start

POST /docker/stop

POST /docker/build
```

---

# AI APIs

```
GET /models

POST /models/load

POST /models/unload

POST /models/generate
```

---

# Status Codes

| Code | Meaning |
|------|---------|
|200|OK|
|201|Created|
|204|No Content|
|400|Bad Request|
|401|Unauthorized|
|403|Forbidden|
|404|Not Found|
|429|Too Many Requests|
|500|Internal Server Error|

---

# Pagination

```
?page=1

&limit=50
```

---

# Filtering

```
?status=running

?type=voice
```

---

# Versioning

```
/api/v1

/api/v2
```

---

# Rate Limiting

Default

```
100 requests/minute
```

Configurable.

---

# Logging

Stores

- Request
- Response
- Errors
- Duration
- User
- IP

---

# Security

- HTTPS
- JWT
- CORS
- CSRF Protection
- Rate Limit
- Input Validation

---

# Future

- GraphQL
- gRPC
- Streaming APIs
- AI Events
- Plugin APIs

---

# Summary

The REST API provides secure HTTP access to every major AERA service.

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
