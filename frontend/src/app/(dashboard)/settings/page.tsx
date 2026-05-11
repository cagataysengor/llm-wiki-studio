import { api } from "@/lib/api";

export default async function SettingsPage() {
  const settings = await api.getSettings();
  const localDefaults = settings.provider_defaults.Local;
  const localStatus = await api.getLocalServerStatus(localDefaults?.url, localDefaults?.model);

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

      <section className="panel">
        <h3>Local provider diagnostics</h3>
        <div className="list">
          <div className="list-item">
            <strong>Connection</strong>
            <div className="pill-row">
              <span className="pill">{localStatus.reachable ? "Reachable" : "Offline"}</span>
              <span className="pill">{localStatus.auth_ok ? "Auth ok" : "Auth failed"}</span>
              <span className="pill">{localStatus.model_available ? "Model found" : "Model alias possible"}</span>
            </div>
          </div>
          <div className="list-item">
            <strong>Endpoint</strong>
            <code>{localDefaults?.url}</code>
          </div>
          <div className="list-item">
            <strong>Selected model</strong>
            <p className="muted">{localStatus.selected_model ?? localDefaults?.model}</p>
          </div>
          <div className="list-item">
            <strong>Provider messages</strong>
            {(localStatus.diagnostics ?? []).map((item) => (
              <p className="muted" key={item}>
                {item}
              </p>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
