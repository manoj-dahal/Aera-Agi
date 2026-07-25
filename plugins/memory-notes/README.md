# Memory Notes — Example AERA Plugin

A minimal reference plugin demonstrating the documented plugin contract
(docs/17-PLUGIN-SYSTEM.md):

- `manifest.yaml` — name, version, author, type, permissions, dependencies
- `src/main.py` — `setup(api)` / `teardown(api)` entry points
- Permission-gated `PluginAPI` — this plugin requests `memory_graph`
  and `notifications` only

## Try it

```bash
curl -X POST localhost:8000/api/plugins/discover
curl -X POST localhost:8000/api/plugins/Memory%20Notes/approve -d '{}' \
     -H 'content-type: application/json'
curl -X POST "localhost:8000/api/plugins/Memory%20Notes/enable"
```

Once enabled, every automation execution is noted into the Memory Graph.
