import { api } from "@/lib/api";

export default async function SettingsPage() {
  const settings = await api.getSettings();

  return (
    <>
      <section className="page-heading">
        <div>
          <span className="eyebrow">Settings</span>
          <h2>Backend defaults</h2>
        </div>
        <p>Environment-driven defaults are now visible in a dedicated page.</p>
      </section>

      <section className="panel">
        <h3>Runtime configuration</h3>
        <div className="list">
          <div className="list-item">
            <strong>App name</strong>
            <p className="muted">{settings.app_name}</p>
          </div>
          <div className="list-item">
            <strong>Default embed model</strong>
            <p className="muted">{settings.default_embed_model}</p>
          </div>
          <div className="list-item">
            <strong>Embedding provider</strong>
            <p className="muted">
              {settings.embedding_provider} · mode: {settings.embedding_mode}
            </p>
          </div>
          <div className="list-item">
            <strong>Embedding URL</strong>
            <code>{settings.embedding_url}</code>
          </div>
          <div className="list-item">
            <strong>Providers</strong>
            <div className="pill-row">
              {settings.providers.map((provider) => (
                <span className="pill" key={provider}>
                  {provider}
                </span>
              ))}
            </div>
          </div>
          <div className="list-item">
            <strong>Server-side provider keys</strong>
            <div className="pill-row">
              {settings.providers.map((provider) => (
                <span className="pill" key={provider}>
                  {provider}: {settings.provider_server_configured[provider] ? "configured" : "missing"}
                </span>
              ))}
            </div>
          </div>
          <div className="list-item">
            <strong>Data directory</strong>
            <code>{settings.data_dir}</code>
          </div>
        </div>
      </section>
    </>
  );
}
