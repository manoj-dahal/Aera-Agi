# GPU Support

Version: 1.0.0

---

# Overview

GPU acceleration allows AERA to run local AI models, voice synthesis, image generation, embeddings, and other compute-intensive workloads efficiently.

---

# Supported GPUs

NVIDIA

- CUDA
- TensorRT
- cuDNN

AMD

- ROCm (Linux)

Intel

- oneAPI (experimental)

Apple

- Metal (outside Docker where supported)

---

# Requirements

- NVIDIA Driver
- NVIDIA Container Toolkit
- Docker Engine
- Docker Compose

---

# Verify GPU

```bash
nvidia-smi
```

---

# Docker Compose

```yaml
services:

  ollama:

    deploy:

      resources:

        reservations:

          devices:

            - driver: nvidia

              count: all

              capabilities:

                - gpu
```

---

# AI Workloads

GPU Accelerated

- Local LLM
- Whisper
- Stable Diffusion
- Embeddings
- OCR
- Face Detection
- Video Processing
- Speech Synthesis

---

# Monitoring

Monitor

- GPU Usage
- VRAM
- Temperature
- Power Usage
- Fan Speed

---

# Performance Tips

- Keep models on SSD
- Enable model caching
- Use quantized models when appropriate
- Monitor VRAM usage
- Reserve GPU resources for AI workloads

---

# Summary

GPU Support enables high-performance local AI processing, significantly improving inference speed and reducing latency for AERA's AI services.