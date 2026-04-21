import { StatCard } from "@/components/stat-card";
import { api } from "@/lib/api";

export default async function HomePage() {
  const [settings, documents, pages] = await Promise.all([
    api.getSettings(),
    api.getDocuments().catch(() => []),
    api.getWikiPages().catch(() => []),
  ]);

  return (
    <>
      <section className="hero-card">
        <div className="hero-grid">
          <div className="stack hero-copy">
            <span className="hero-badge">Knowledge Workspace</span>
            <h2>Turn scattered documents into a living, queryable company wiki.</h2>
            <p className="hero-lead">
              Upload documents, retrieve grounded context, and turn useful answers into reusable
              knowledge with a dedicated API and frontend.
            </p>
            <div className="pill-row">
              {settings.providers.map((provider) => (
                <span className="pill" key={provider}>
                  {provider}
                </span>
              ))}
            </div>
          </div>

          <div className="hero-panel">
            <div>
              <h3>Workspace summary</h3>
              <p className="muted">
                FastAPI backend, Next.js frontend, grounded retrieval, and support for both local
                and hosted language models.
              </p>
            </div>
            <div className="hero-metrics">
              <div className="metric">
                <strong>{documents.length}</strong>
                <span className="muted">indexed sources already wired into the API</span>
              </div>
              <div className="metric">
                <strong>{pages.length}</strong>
                <span className="muted">knowledge pages available to browse and extend</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="showcase-strip">
        <article className="showcase-card">
          <div className="micro-label">Overview</div>
          <strong>Search documents, ask questions, and build a reusable wiki</strong>
          <p className="muted">
            The application is structured around ingestion, retrieval, question answering, and
            knowledge capture.
          </p>
        </article>
        <article className="showcase-card highlight">
          <div className="eyebrow">Core Flow</div>
          <strong>Ingest documents, ask grounded questions, and save answers into the wiki</strong>
        </article>
      </section>

      <section className="stats-grid">
        <StatCard
          label="Indexed documents"
          value={String(documents.length)}
          description="Files already ingested into the backend workspace."
        />
        <StatCard
          label="Wiki pages"
          value={String(pages.length)}
          description="Persisted markdown pages available for browsing and editing."
        />
        <StatCard
          label="Default provider"
          value={settings.default_provider}
          description="Public backend defaults exposed to the frontend."
        />
      </section>

      <section className="panel-grid">
        <article className="panel">
          <div className="micro-label">Current Features</div>
          <h3>Available now</h3>
          <div className="list">
            <div className="list-item">Document ingest API and local raw storage</div>
            <div className="list-item">Wiki page persistence and listing</div>
            <div className="list-item">Question answering route with retrieved context</div>
            <div className="list-item">Provider abstraction for local and hosted LLMs</div>
          </div>
        </article>

        <article className="panel">
          <div className="micro-label">Planned Improvements</div>
          <h3>Next steps</h3>
          <div className="list">
            <div className="list-item">Authentication and team workspaces</div>
            <div className="list-item">Postgres + pgvector retrieval pipeline</div>
            <div className="list-item">Async background jobs for indexing and generation</div>
            <div className="list-item">Observability, tests, CI, and deployment templates</div>
          </div>
        </article>
      </section>

      <section className="feature-band">
        <article className="feature-card">
          <div className="micro-label">Architecture</div>
          <strong>Separated backend and frontend</strong>
          <p className="muted">
            The application uses a dedicated API layer and a separate frontend for a cleaner
            product structure.
          </p>
        </article>
        <article className="feature-card">
          <div className="micro-label">Security</div>
          <strong>Server-side provider configuration</strong>
          <p className="muted">
            Secrets stay server-side while the frontend consumes a cleaner and safer API surface.
          </p>
        </article>
        <article className="feature-card">
          <div className="micro-label">Knowledge</div>
          <strong>Answers can be saved into the wiki</strong>
          <p className="muted">
            Useful responses can be turned into durable knowledge pages instead of staying as
            one-off chat outputs.
          </p>
        </article>
      </section>
    </>
  );
}
