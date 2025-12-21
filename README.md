# AdAi-FastAPI

FastAPI backend for a Gemini-powered chat endpoint.

## Quickstart

Create `.env` and `.env-model`.

Use `.env` for app + database settings (see `.env.example`).
Use `.env-model` for Gemini/model settings only (see `.env-model.example`).

### `.env-model` (example)

```env
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-1.5-flash
```

### `.env` (example)

```env
APP_NAME=Thesis Agent Backend
ENVIRONMENT=local
LOG_LEVEL=INFO

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=app
POSTGRES_PASSWORD=app
POSTGRES_DB=app
```

Install deps:

```zsh
pip install -r requirements.txt
```

Run:

```zsh
/Users/michalpodolec/WORKS/AdAi-FastAPI/venv/bin/python -m uvicorn app.main:app --reload
```

## Database (Postgres + pgvector)

DB code lives in `app/db/`.

### pgvector requirement

This project uses pgvector (and an HNSW cosine index). Your application DB user is
expected to NOT have privileges to run `CREATE EXTENSION`.

Before running migrations, enable pgvector as a privileged user (or via managed DB provisioning):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Migrations (Alembic)

Apply the latest migrations:

```zsh
/Users/michalpodolec/WORKS/AdAi-FastAPI/venv/bin/python -m alembic upgrade head
```

Create a new migration:

```zsh
/Users/michalpodolec/WORKS/AdAi-FastAPI/venv/bin/python -m alembic revision -m "describe change"
```

Autogenerate (requires ORM models to be up to date):

```zsh
/Users/michalpodolec/WORKS/AdAi-FastAPI/venv/bin/python -m alembic revision --autogenerate -m "describe change"
```

### Dev-only helper (not migrations)

For quick local experiments, there is also a dev-friendly initializer that creates tables via SQLAlchemy metadata:

```zsh
/Users/michalpodolec/WORKS/AdAi-FastAPI/venv/bin/python -c "from app.db.engine import get_engine; from app.db.init_db import init_db; init_db(get_engine())"
```

## Project structure

- `app/api/` contains route definitions (FastAPI routers + endpoint handlers)
- `app/models/` contains Pydantic models split per API module
- `app/db/` contains SQLAlchemy engine/session/models

Endpoints:
- `GET /` basic health
- `GET /health` liveness
- `POST /api/v1/chat`

## Tests

```zsh
/Users/michalpodolec/WORKS/AdAi-FastAPI/venv/bin/python -m pytest -q
```