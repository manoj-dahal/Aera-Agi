# Dockerfile

Version: 1.0.0

---

# Overview

The Dockerfile defines how the AERA application image is built.

---

# Build Stages

```
Base Image

↓

System Packages

↓

Python

↓

Node.js

↓

Dependencies

↓

Application

↓

Configuration

↓

Runtime

↓

Health Check
```

---

# Example Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "main.py"]
```

---

# Multi-Stage Build

```
Builder

↓

Dependencies

↓

Compile

↓

Runtime Image
```

---

# Best Practices

- Small base images
- Multi-stage builds
- Non-root user
- Health checks
- Layer caching
- Environment variables

---

# Summary

The Dockerfile builds optimized AERA container images.