# AI Providers

Version: 1.0.0

---

# Overview

AERA supports multiple AI providers through a unified interface.

---

# Supported Providers

- OpenAI
- Google Gemini
- Anthropic Claude
- Ollama
- LM Studio
- OpenRouter
- vLLM
- llama.cpp

---

# Architecture

```
Core Agent

↓

Provider Manager

↓

Provider Adapter

↓

AI Provider
```

---

# Features

- Model Switching
- Automatic Failover
- Cost Tracking
- Load Balancing
- Fallback Models
- Multi-Agent Routing

---

# Configuration

```
providers/

openai.yaml

gemini.yaml

claude.yaml

ollama.yaml

openrouter.yaml
```

---

# Selection

Can automatically choose

- Cheapest
- Fastest
- Highest Quality
- Local First
- User Preference

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
