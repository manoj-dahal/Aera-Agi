# Volumes

Version: 1.0.0

---

# Overview

Volumes permanently store AERA data.

---

# Stored Data

- PostgreSQL
- ChromaDB
- Logs
- AI Models
- Cache
- User Files
- Workspace
- Plugins

---

# Structure

```
volumes/

postgres/

redis/

chromadb/

models/

workspace/

logs/

cache/
```

---

# Backup

```bash
docker run --rm \
-v aera_data:/data \
-v $(pwd):/backup \
busybox \
tar czf /backup/data.tar.gz /data
```

---

# Restore

Restore from the compressed backup into the appropriate Docker volume before starting the services.

---

# Summary

Volumes preserve important data across container updates and restarts.