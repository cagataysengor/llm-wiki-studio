# LLM Wiki Studio

LLM Wiki Studio is a wiki-first knowledge workspace that turns uploaded documents and code files into a persistent, queryable knowledge layer.

![LLM Wiki Studio Overview](docs/images/overview.png)

## Why This Project Exists

Many "chat with your docs" tools are useful for one-off questions, but they often re-discover the same context from scratch every time. The result is helpful in the moment, but it does not accumulate into a durable knowledge asset.

This project takes a different approach. Instead of treating uploads as raw files to retrieve from forever, it compiles them into a growing wiki layer that can be queried, extended, and maintained over time.

The workflow is designed around a simple idea:

- ingest source material through a backend API
- generate source summary pages and topic pages automatically
- maintain `index.md` and `log.md` as system wiki pages
- answer questions using wiki pages first and raw sources second
- save useful answers back into the wiki as durable notes
- surface wiki health issues so the knowledge base can be maintained, not just queried

## What Makes It Useful

- Works with local models for private, low-cost experiments
- Also supports hosted providers like Gemini and OpenAI-style endpoints
- Handles mixed source types such as Markdown, PDF, DOCX, and code files
- Builds a persistent wiki layer instead of relying only on raw-file retrieval
- Generates source summaries, topic pages, saved answers, and system wiki pages
- Keeps an explicit maintenance loop with index, log, and lint reporting
- Uses query-aware retrieval so technical questions prefer code/config context while narrative questions prefer document-like sources

## Current Features

Available capabilities:

- Upload and index source files
- Generate source summary pages during ingest
- Generate and update topic pages linked across related sources
- Maintain system pages such as `index.md` and `log.md`
- Ask wiki-first grounded questions over the knowledge layer
- Save answers into wiki pages
- Browse, review, and delete non-system wiki entries
- Run wiki health checks with lint-style findings
- Use `Local`, `Gemini`, `OpenAI`, and `Claude` provider modes
- Run locally with SQLite, or use Docker Compose with PostgreSQL + `pgvector`

## Architecture

- Backend: FastAPI, Pydantic, SQLAlchemy
- Frontend: Next.js App Router, TypeScript, React Query
- Storage: SQLite by default, PostgreSQL + `pgvector` via Docker Compose
- Retrieval: wiki-first question answering plus database-backed chunk retrieval with intent-aware reranking
- Wiki layer: source summaries, topic pages, saved answers, `index.md`, `log.md`, and lint reporting
- Local inference: OpenAI-compatible local endpoints such as `llama.cpp`

## Core Workflow

### 1. Ingest

When a file is uploaded, the system stores the raw source, extracts text, chunks it for retrieval, and generates wiki artifacts.

Typical ingest outputs:

- a source summary page for the uploaded file
- one or more topic pages derived from the content
- updated `index.md` and `log.md` entries

### 2. Ask

Questions are answered against the wiki first, then refined with raw source chunks when needed. This keeps answers grounded while still benefiting from the synthesized knowledge already stored in the workspace.

### 3. Save

Useful answers can be saved back into the wiki as durable pages so they do not disappear into chat history.

### 4. Maintain

The wiki can be health-checked for issues such as orphan pages, thin topic coverage, and missing topic links. This makes the system feel more like a maintained knowledge base than a temporary QA interface.

## Screenshots

### Ask

![Ask AI](docs/images/ask-ai.png)

### Wiki

![Wiki](docs/images/wiki.png)

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

Default model names can be changed in `backend/.env`, and users can still type a different valid
model name in the `Model name` field when asking a question.

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
- wiki maintenance endpoints

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
- Topic synthesis is still heuristic and not yet entity-level or contradiction-aware
- This is not yet a production-hardened multi-user platform
- Auth, background jobs, and workspace isolation are not implemented yet

## Roadmap

1. Improve topic synthesis and move toward richer entity and concept pages
2. Add stronger cross-linking, contradiction handling, and wiki maintenance workflows
3. Move long-running ingest and generation to background tasks
4. Add auth and multi-user workspaces
5. Improve retrieval observability, evaluation, and deployment readiness

## Product Direction

This repository is intended to be shared as the professional version of the project:

- backend logic is organized into maintainable service modules
- frontend is a dedicated Next.js application
- provider secrets are handled server-side
- retrieval is structured, query-aware, and wiki-first
- the app is positioned as a knowledge workspace, not only a file-chat interface
- the codebase is shaped for portfolio use, iteration, and open-source sharing
