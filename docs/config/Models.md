# Models Configuration

Version: 1.0.0

---

# Overview

Configures every AI model.

---

# models.yaml

```yaml
models:

  default: gpt-5

  reasoning: claude

  coding: gpt-5

  research: gemini

  vision: gemini

  local:

    enabled: true

    provider: ollama

    model: llama3

  embedding:

    model: text-embedding
```

---

# Model Routing

```
Task

↓

Router

↓

Provider

↓

Model

↓

Response
```

---

# Settings

- Temperature
- Top P
- Max Tokens
- Context Window
- Streaming
- Timeout

---

# Summary

Controls all AI model routing.