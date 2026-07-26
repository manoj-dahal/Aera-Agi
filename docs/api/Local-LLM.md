# Local LLM

Version: 1.0.0

---

# Overview

Local LLM enables AERA to run AI models directly on the user's hardware for privacy, offline usage, and reduced latency.

---

# Supported Engines

- Ollama
- LM Studio
- llama.cpp
- vLLM
- MLC
- TensorRT-LLM

---

# Features

- Offline AI
- GPU Acceleration
- Model Switching
- Quantized Models
- Multi-GPU
- Local Embeddings

---

# Supported Models

- Llama
- Mistral
- Qwen
- Gemma
- Phi
- DeepSeek

---

# Configuration

```yaml
provider: local

engine: ollama

model: llama3

gpu: true

context: 32768
```

---

# Advantages

- Complete Privacy
- Offline
- Low Latency
- No API Cost
- Custom Models

---

# Future

- Distributed Inference
- Multi-GPU Scheduling
- Hybrid Local + Cloud Routing