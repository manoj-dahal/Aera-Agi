# WebSocket

Version: 1.0.0

Status: Stable

---

# Overview

The WebSocket server enables real-time communication between clients and AERA.

Unlike REST, WebSockets provide persistent two-way communication.

---

# URL

```
ws://localhost:8080/ws
```

Production

```
wss://api.aera.ai/ws
```

---

# Features

- Real-Time AI Responses
- Live Voice
- Live Avatar
- Live Dashboard
- Streaming Tokens
- Agent Events
- Notifications

---

# Architecture

```
Client

↓

WebSocket Gateway

↓

Core Agent

↓

Agent Bus

↓

Events
```

---

# Events

Incoming

```
message

voice

agent

memory

workspace

docker

terminal
```

Outgoing

```
response

notification

status

stream

event

error
```

---

# Token Streaming

```
User

↓

AI

↓

Streaming Token

↓

Client Display
```

---

# Heartbeat

```
ping

pong
```

---

# Authentication

```
Bearer Token
```

during connection.

---

# Reconnect

Automatic.

Exponential Backoff.

---

# Security

- TLS
- JWT
- Origin Validation
- Rate Limiting

---

# Future

- Binary Streaming
- Voice Streaming
- Video Streaming