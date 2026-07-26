# Containers

Version: 1.0.0

---

# Overview

Each AERA module runs inside an isolated container.

---

# Container List

| Container | Purpose |
|-----------|----------|
| core | AI Core |
| api | REST API |
| dashboard | Web UI |
| postgres | Database |
| redis | Cache |
| chromadb | Vector Database |
| ollama | Local AI |
| nginx | Reverse Proxy |
| monitoring | Metrics |

---

# Lifecycle

```
Create

↓

Start

↓

Healthy

↓

Running

↓

Stop

↓

Remove
```

---

# Health

```bash
docker ps

docker inspect
```

---

# Restart Policy

```
always
```

---

# Summary

Containers isolate every AERA component.

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
