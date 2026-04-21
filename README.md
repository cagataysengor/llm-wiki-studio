# LLM Wiki Studio

LLM Wiki Studio is a productized RAG application that turns uploaded documents and code files into a searchable wiki plus an AI Q&A workspace.

## Why This Project Exists

Many "chat with your docs" tools are good at answering a few questions, but they often feel fragile, hard to extend, and not very product-like.

This project focuses on building a usable document intelligence application:

- upload source material and index it through a backend API
- retrieve grounded context from multiple files
- ask questions with local or hosted language models
- save useful answers back into a growing wiki
- present the whole flow in a frontend that feels like a real product instead of a notebook or utility script

## What Makes It Useful

- Works with local models for private, low-cost experiments
- Also supports hosted providers like Gemini and OpenAI-style endpoints
- Handles mixed source types such as Markdown, PDF, DOCX, and code files
- Keeps a wiki output layer so answers can become reusable project knowledge
- Uses query-aware retrieval so technical questions prefer code/config context while narrative questions prefer document-like sources

## Current Features

Available capabilities:

- Upload and index documents
- View indexed sources
- Ask grounded questions over indexed content
- Save answers into wiki pages
- Browse saved wiki entries
- Use `Local`, `Gemini`, `OpenAI`, and `Claude` provider modes
- Run locally with SQLite, or use Docker Compose with PostgreSQL + `pgvector`

## Architecture

- Backend: FastAPI, Pydantic, SQLAlchemy
- Frontend: Next.js App Router, TypeScript, React Query
- Storage: SQLite by default, PostgreSQL + `pgvector` via Docker Compose
- Retrieval: database-backed chunk search with intent-aware reranking
- Local inference: OpenAI-compatible local endpoints such as `llama.cpp`

## Project Structure

```text
backend/
  app/
    api/routes/       # HTTP endpoints
    core/             # settings and config
    db/               # engine and session management
    models/           # SQLAlchemy models
    schemas/          # request/response contracts
    services/         # ingest, retrieval, QA, wiki logic
frontend/
  src/app/            # Next.js routes
  src/components/     # UI building blocks
  src/lib/            # API client and shared types
data/
  raw/                # uploaded source files
  wiki/               # saved markdown wiki pages
  index/              # chunk index artifacts
scripts/
  restart_backend.sh
  restart_frontend.sh
```

## Quickstart

### 1. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

Backend:

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

### 2. Start the frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Frontend:

- App: `http://localhost:3000`

### 3. Ask questions with a local model

If you want to run a local model with `llama.cpp`, start an OpenAI-compatible server like this:

```bash
/path/to/llama-server \
  -m "/path/to/model.gguf" \
  --host 127.0.0.1 \
  --port 8080 \
  -ngl 0 \
  -c 4096
```

Then use these values in the app:

- Provider: `Local`
- LLM URL: `http://127.0.0.1:8080/v1/chat/completions`
- Embedding URL: `http://127.0.0.1:8080/v1/embeddings`

Note:

- CPU mode works, but will be slower.
- Users with GPU-enabled `llama.cpp` builds can use the same app with much faster inference.

## Provider Setup

The application supports these provider modes in the UI:

- `Local`
- `OpenAI`
- `Gemini`
- `Claude`

Hosted providers are configured through `backend/.env`.

Example:

```bash
OPENAI_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
CLAUDE_API_KEY=your_key_here
```

The frontend does not send provider API keys from the browser. Requests go through the backend.

### Embedding endpoints

The default local setup can use a local embedding endpoint.

```bash
EMBEDDING_PROVIDER=Local
EMBEDDING_MODE=auto
EMBEDDING_URL=http://127.0.0.1:8080/v1/embeddings
```

You can also use a remote or hosted embedding endpoint:

```bash
EMBEDDING_PROVIDER=Remote
EMBEDDING_MODE=remote
EMBEDDING_URL=https://your-embedding-endpoint/v1/embeddings
EMBEDDING_API_KEY=your_key_here
```

Any OpenAI-compatible embedding endpoint can be used, including local or hosted services. OpenAI is only one possible provider, not a requirement.

## Docker Compose

The repository includes a local multi-service environment:

- `frontend` on `http://localhost:3000`
- `backend` on `http://localhost:8000`
- `db` with PostgreSQL + `pgvector`

Start:

```bash
make up
```

Stop:

```bash
make down
```

Logs:

```bash
make logs
```

The database enables the vector extension from
[docker/postgres/init/01-enable-pgvector.sql](/home/cagatay/llm_wiki_app/docker/postgres/init/01-enable-pgvector.sql).

## Tests

Backend smoke tests cover the highest-signal application flows:

- health
- public settings
- ingest
- ask
- save-to-wiki
- reindex

Run locally:

```bash
cd backend
pip install -e ".[dev]"
pytest tests
```

CI runs backend tests on pushes and pull requests via
[.github/workflows/ci.yml](/home/cagatay/llm_wiki_app/.github/workflows/ci.yml).

## Open Source Publishing Notes

Before publishing your own fork or deployment:

- never commit real API keys
- rotate any keys used during local testing
- do not commit uploaded source files from `data/raw`
- do not commit generated wiki outputs from `data/wiki`
- keep generated local databases and indexes out of git

## Known Limitations

- Local CPU inference can be slow on older machines
- Retrieval quality is stronger on well-structured content than noisy mixed-source datasets
- This is not yet a production-hardened multi-user platform
- Auth, background jobs, and workspace isolation are not implemented yet

## Roadmap

1. Add first-class reindex jobs when embedding models change
2. Move long-running ingest and generation to background tasks
3. Add auth and multi-user workspaces
4. Improve retrieval observability and evaluation
5. Add deployment manifests and stronger end-to-end tests

## Product Direction

This repository is intended to be shared as the professional version of the project:

- backend logic is organized into maintainable service modules
- frontend is a dedicated Next.js application
- provider secrets are handled server-side
- retrieval is structured and query-aware
- the codebase is shaped for portfolio use, iteration, and open-source sharing
