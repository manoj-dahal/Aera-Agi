# docker/

Per-service container definitions and compose fragments.

The root `Dockerfile` and `docker-compose.yml` cover the default stack
(core + redis + ollama + nginx). Add specialized files here as services
are split out, e.g.:

```
docker/
├── core.Dockerfile
├── voice.Dockerfile
├── compose.gpu.yml
└── compose.dev.yml
```

See `docs/27-DOCKER.md` and `docs/docker/` for the full container architecture.
