# Custom Apps

Version: 1.0.0

---

# Overview

Custom Apps allow developers to build applications that integrate directly with AERA.

---

# Structure

```
apps/

MyApp/

manifest.yaml

icon.png

app.py

api/

assets/

config/

plugins/
```

---

# Manifest

```yaml
name: MyApp

version: 1.0

author: Developer

permissions:

- workspace

- voice

- memory
```

---

# Capabilities

- AI Integration
- Voice
- Memory
- Automation
- Dashboard Widgets
- Plugins
- REST API