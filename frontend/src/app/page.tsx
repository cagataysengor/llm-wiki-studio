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
            <h2>Turn raw sources into a living, queryable wiki that grows over time.</h2>
            <p className="hero-lead">
              Uploaded sources are turned into summary pages, topic pages, and a persistent wiki
              layer that can be queried, extended, and maintained over time.
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
                FastAPI backend, Next.js frontend, wiki-first retrieval, and support for both
                local and hosted language models.
              </p>
            </div>
            <div className="hero-metrics">
              <div className="metric">
                <strong>{documents.length}</strong>
                <span className="muted">source files ingested into the workspace</span>
              </div>
              <div className="metric">
                <strong>{pages.length}</strong>
                <span className="muted">wiki pages generated, linked, or saved</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="showcase-strip">
        <article className="showcase-card">
          <div className="micro-label">Overview</div>
          <strong>Build a persistent knowledge layer between raw files and AI answers</strong>
          <p className="muted">
            The system ingests raw sources, generates wiki pages, tracks activity, and answers
            questions against an evolving wiki-first knowledge base.
          </p>
        </article>
        <article className="showcase-card highlight">
          <div className="eyebrow">Core Flow</div>
          <strong>Ingest sources, generate knowledge pages, ask questions, and maintain the wiki</strong>
        </article>
      </section>

      <section className="stats-grid">
        <StatCard
          label="Indexed documents"
          value={String(documents.length)}
          description="Raw sources available to feed and expand the wiki."
        />
        <StatCard
          label="Wiki pages"
          value={String(pages.length)}
          description="Generated summaries, topic pages, saved answers, and system pages."
        />
        <StatCard
          label="Default provider"
          value={settings.default_provider}
          description="Default model provider currently exposed to the workspace."
        />
      </section>

      <section className="panel-grid">
        <article className="panel">
          <div className="micro-label">Current Features</div>
          <h3>Available now</h3>
          <div className="list">
            <div className="list-item">Automatic source summary generation during ingest</div>
            <div className="list-item">Topic page creation and wiki page linking</div>
            <div className="list-item">Wiki-first question answering with raw source support</div>
            <div className="list-item">Automatic index, log, and wiki health reporting</div>
          </div>
        </article>

        <article className="panel">
          <div className="micro-label">Planned Improvements</div>
          <h3>Next steps</h3>
          <div className="list">
            <div className="list-item">Stronger topic synthesis and entity-level page updates</div>
            <div className="list-item">Safer source deletion and graph-aware cleanup workflows</div>
            <div className="list-item">Authentication and team workspaces</div>
            <div className="list-item">Async jobs, observability, and richer evaluation flows</div>
          </div>
        </article>
      </section>

      <section className="feature-band">
        <article className="feature-card">
          <div className="micro-label">Wiki Layer</div>
          <strong>Sources become durable knowledge pages</strong>
          <p className="muted">
            New files are compiled into summaries and topic pages instead of staying as isolated
            raw documents.
          </p>
        </article>
        <article className="feature-card">
          <div className="micro-label">Retrieval</div>
          <strong>Wiki-first answers with source support</strong>
          <p className="muted">
            The system prefers synthesized wiki knowledge first and falls back to raw chunks for
            detail and grounding.
          </p>
        </article>
        <article className="feature-card">
          <div className="micro-label">Maintenance</div>
          <strong>Index, log, lint, and cleanup workflows</strong>
          <p className="muted">
            The wiki keeps its own catalog, activity history, health report, and manual cleanup
            controls.
          </p>
        </article>
      </section>
    </>
  );
}
