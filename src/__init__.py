"""AERA AGI — application package.

Layout follows docs/03-FILE-STRUCTURE.md:

    src/
    ├── core/        AI Core orchestration
    ├── agents/      Agent Manager + specialized agents
    ├── memory/      Memory Graph engine
    ├── ai/          Model Router (local + cloud)
    ├── routes/      REST API routes
    ├── websocket/   Realtime endpoints
    ├── common/      Shared schemas
    ├── config/      Settings
    └── ...          (see each package docstring)

Entry points:
    main.py       CLI entry (`python -m src.main serve`)
    app.py        FastAPI application (`uvicorn src.app:app`)
    server.py     Development server runner
    bootstrap.py  Subsystem initialization
"""

__version__ = "0.1.0"
