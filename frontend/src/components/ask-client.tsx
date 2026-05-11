"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";

import { api } from "@/lib/api";
import {
  AskQuestionPayload,
  AskResponse,
  LocalServerStatus,
  PublicSettings,
  SaveAnswerResponse,
  WikiPage,
} from "@/lib/types";

type AskClientProps = {
  settings: PublicSettings;
};

const LOCAL_PRESETS = [
  {
    id: "llamacpp",
    label: "llama.cpp",
    url: "http://127.0.0.1:8080/v1/chat/completions",
    model: "local-model",
  },
  {
    id: "ollama",
    label: "Ollama",
    url: "http://127.0.0.1:11434/v1/chat/completions",
    model: "gpt-oss:120b-cloud",
  },
  {
    id: "ollama-cloud",
    label: "Ollama Cloud",
    url: "https://ollama.com/v1/chat/completions",
    model: "gpt-oss:120b-cloud",
  },
];

export function AskClient({ settings }: AskClientProps) {
  const initialProviderConfig =
    settings.provider_defaults[settings.default_provider] ??
    settings.provider_defaults.Local ?? {
      url: "http://localhost:8080/v1/chat/completions",
      model: "local-model",
    };
  const [question, setQuestion] = useState("");
  const [provider, setProvider] = useState(settings.default_provider);
  const [modelName, setModelName] = useState(initialProviderConfig.model);
  const [llmUrl, setLlmUrl] = useState(initialProviderConfig.url);
  const [topK, setTopK] = useState("6");
  const [agenticMode, setAgenticMode] = useState(false);
  const [wikiTitle, setWikiTitle] = useState("");
  const [mergeIfSimilar, setMergeIfSimilar] = useState(true);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [saveResult, setSaveResult] = useState<SaveAnswerResponse | null>(null);
  const [agenticApplyResult, setAgenticApplyResult] = useState<WikiPage | null>(null);
  const [error, setError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [agenticApplyError, setAgenticApplyError] = useState("");
  const [waitSeconds, setWaitSeconds] = useState(0);
  const [localStatus, setLocalStatus] = useState<LocalServerStatus | null>(null);
  const [localStatusError, setLocalStatusError] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [applyingSuggestionKey, setApplyingSuggestionKey] = useState("");
  const [, startTransition] = useTransition();
  const [isSaving, startSaveTransition] = useTransition();
  const providerConfigured = settings.provider_server_configured[provider];
  const providerSupported = settings.provider_runtime_support[provider];
  const shouldWarnMissingKey = provider !== "Local" && !providerConfigured;

  useEffect(() => {
    const providerConfig = settings.provider_defaults[provider];
    if (!providerConfig) {
      return;
    }
    setModelName(providerConfig.model);
    setLlmUrl(providerConfig.url);
  }, [provider, settings.provider_defaults]);

  useEffect(() => {
    if (provider !== "Local") {
      return;
    }

    let cancelled = false;
    const loadStatus = async () => {
      try {
        const status = await api.getLocalServerStatus(llmUrl, modelName);
        if (cancelled) {
          return;
        }
        setLocalStatus(status);
        setLocalStatusError("");
      } catch (statusError) {
        if (cancelled) {
          return;
        }
        setLocalStatus(null);
        setLocalStatusError(
          statusError instanceof Error ? statusError.message : "Failed to check local server status."
        );
      }
    };

    void loadStatus();
    const interval = window.setInterval(() => {
      void loadStatus();
    }, 15000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [llmUrl, modelName, provider]);

  useEffect(() => {
    if (!isAsking) {
      setWaitSeconds(0);
      return;
    }

    const startedAt = Date.now();
    const interval = window.setInterval(() => {
      setWaitSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);

    return () => window.clearInterval(interval);
  }, [isAsking]);

  function handleAsk() {
    if (!question.trim()) {
      setError("Please enter a question.");
      return;
    }
    if (!providerSupported) {
      setError(`${provider} is not enabled in the backend runtime yet.`);
      return;
    }

    setError("");
    setSaveError("");
    setAgenticApplyError("");
    setSaveResult(null);
    setAgenticApplyResult(null);
    setResult(null);
    setWikiTitle("");
    setIsAsking(true);

    void (async () => {
      try {
        const payload: AskQuestionPayload = {
          question: question.trim(),
          provider,
          model_name: modelName,
          llm_url: llmUrl,
          embed_model: settings.default_embed_model,
          top_k: Number(topK) || 6,
          agentic_mode: agenticMode,
        };
        const response = await api.askQuestion(payload);
        startTransition(() => {
          setResult(response);
          setWikiTitle(question.trim().slice(0, 80));
        });
      } catch (askError) {
        setError(askError instanceof Error ? askError.message : "Question failed.");
      } finally {
        setIsAsking(false);
      }
    })();
  }

  function handleSave() {
    if (!result) {
      setSaveError("Ask a question first.");
      return;
    }

    const title = wikiTitle.trim() || result.question.slice(0, 80);
    setSaveError("");
    setSaveResult(null);

    startSaveTransition(() => {
      void (async () => {
        try {
          const response = await api.saveAnswer({
            title,
            question: result.question,
            answer: result.answer,
            source_files: Array.from(new Set(result.sources.map((item) => item.filename))),
            merge_if_similar: mergeIfSimilar,
          });
          setSaveResult(response);
        } catch (saveActionError) {
          setSaveError(saveActionError instanceof Error ? saveActionError.message : "Save failed.");
        }
      })();
    });
  }

  async function handleApplyAgenticUpdate(suggestion: NonNullable<AskResponse["agentic"]>["suggested_updates"][number]) {
    if (suggestion.action === "none" || !suggestion.markdown.trim()) {
      return;
    }

    const suggestionKey = `${suggestion.action}-${suggestion.target_slug}-${suggestion.title}`;
    setApplyingSuggestionKey(suggestionKey);
    setAgenticApplyError("");
    setAgenticApplyResult(null);

    try {
      const response =
        suggestion.action === "update" && suggestion.target_slug
          ? await api.updateWikiPage(suggestion.target_slug, {
              title: suggestion.title,
              markdown: suggestion.markdown,
            })
          : await api.createWikiPage({
              title: suggestion.title,
              markdown: suggestion.markdown,
            });
      setAgenticApplyResult(response);
    } catch (applyError) {
      setAgenticApplyError(applyError instanceof Error ? applyError.message : "Agentic wiki update failed.");
    } finally {
      setApplyingSuggestionKey("");
    }
  }

  return (
    <section className="two-col">
      <article className="panel">
        <h3>Ask the knowledge base</h3>
        <div className="stack">
          <label className="field">
            <span>Question</span>
            <textarea
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Enter your question"
              value={question}
            />
          </label>

          <div className="mode-control" role="group" aria-label="Answer mode">
            <button
              aria-pressed={!agenticMode}
              className={`mode-option ${!agenticMode ? "active" : ""}`}
              onClick={() => setAgenticMode(false)}
              type="button"
            >
              <strong>Standard</strong>
              <small>Wiki-first answer</small>
            </button>
            <button
              aria-pressed={agenticMode}
              className={`mode-option ${agenticMode ? "active" : ""}`}
              onClick={() => setAgenticMode(true)}
              type="button"
            >
              <strong>Agentic Wiki</strong>
              <small>Checks wiki memory first</small>
            </button>
          </div>

          <label className="field">
            <span>Provider</span>
            <select onChange={(event) => setProvider(event.target.value)} value={provider}>
              {settings.providers.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Model name</span>
            <input onChange={(event) => setModelName(event.target.value)} value={modelName} />
          </label>

          <label className="field">
            <span>LLM URL</span>
            <input onChange={(event) => setLlmUrl(event.target.value)} value={llmUrl} />
          </label>

          {provider === "Local" ? (
            <div className="preset-row" aria-label="Local runtime presets">
              {LOCAL_PRESETS.map((preset) => (
                <button
                  className="preset-button"
                  key={preset.id}
                  onClick={() => {
                    setLlmUrl(preset.url);
                    setModelName(preset.model);
                  }}
                  type="button"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          ) : null}

          <div className="list-item">
            <strong>Provider secret handling</strong>
            <p className="muted">
              {providerConfigured
                ? "This provider is configured on the server. No secret is sent from the browser."
                : provider === "Local"
                  ? "Local mode does not require a provider API key."
                  : "This provider does not have a server-side key configured yet."}
            </p>
          </div>

          <div className="list-item">
            <strong>Provider readiness</strong>
            <p className="muted">
              {provider === "Local"
                ? "Local and OpenAI-style endpoints can be tested by changing the URL and model below."
                : providerConfigured
                  ? `${provider} is ready to use from the UI with the server-side key.`
                  : `Add the ${provider.toUpperCase()}_API_KEY value to backend/.env and restart the backend.`}
            </p>
          </div>

          <label className="field">
            <span>Top K</span>
            <input max="12" min="1" onChange={(event) => setTopK(event.target.value)} type="number" value={topK} />
          </label>

          {agenticMode ? (
            <div className="notice info">
              Wiki memory is checked first. Raw source retrieval is used only when the wiki looks insufficient.
            </div>
          ) : null}

          {provider === "Local" ? (
            <div className="list-item">
              <strong>Local server status</strong>
              <p className="muted">
                {localStatus
                  ? localStatus.reachable
                    ? `Running at ${localStatus.url}`
                    : `Not reachable at ${localStatus.url}`
                  : "Checking local model server..."}
              </p>
              {localStatus?.reachable ? (
                <div className="pill-row">
                  <span className="pill">Online</span>
                  <span className="pill">{localStatus.auth_ok ? "Auth ok" : "Auth failed"}</span>
                  {typeof localStatus.model_available === "boolean" ? (
                    <span className="pill">{localStatus.model_available ? "Model found" : "Model alias possible"}</span>
                  ) : null}
                  <span className="pill">{localStatus.model_count} model(s)</span>
                  {localStatus.models.slice(0, 2).map((item) => (
                    <span className="pill" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              ) : null}
              {!localStatus?.reachable && localStatus?.detail ? (
                <p className="muted">{localStatus.detail}</p>
              ) : null}
              {localStatus?.diagnostics?.length ? (
                <div className="stack">
                  {localStatus.diagnostics.slice(0, 3).map((item) => (
                    <p className="muted" key={item}>
                      {item}
                    </p>
                  ))}
                </div>
              ) : null}
              {localStatusError ? <p className="muted">{localStatusError}</p> : null}
            </div>
          ) : null}

          <button
            className="button"
            disabled={
              isAsking ||
              (!providerConfigured && provider !== "Local") ||
              (provider === "Local" && localStatus?.reachable === false)
            }
            onClick={handleAsk}
            type="button"
          >
            {isAsking ? "Generating..." : "Ask question"}
          </button>
          {provider === "Local" && localStatus?.reachable === false ? (
            <p className="notice error">
              Local model server is not reachable yet. Start your llama.cpp server before asking a question.
            </p>
          ) : null}
          {isAsking ? (
            <div className="notice info">
              {provider === "Local"
                ? `Local/OpenAI-compatible model is thinking. This can take a while depending on the selected endpoint. Elapsed: ${waitSeconds}s.`
                : `Request sent successfully. Waiting for the model response. Elapsed: ${waitSeconds}s.`}
            </div>
          ) : null}
          {isAsking && provider === "Local" ? (
            <div className="list-item">
              <strong>Live local run</strong>
              <p className="muted">
                The request is in progress. Response time depends on the selected endpoint,
                model size, context length, and provider load.
              </p>
            </div>
          ) : null}
          {shouldWarnMissingKey ? (
            <p className="notice error">
              {provider} is selected but no server-side key is configured yet.
            </p>
          ) : null}
          {error ? <p className="notice error">{error}</p> : null}
        </div>
      </article>

      <article className="panel">
        <h3>Answer, evidence, and wiki action</h3>
        {result ? (
          <div className="stack">
            <pre className="code-block">{result.answer}</pre>

            {result.agentic ? (
              <div className="agentic-panel">
                <div className="agentic-header">
                  <div>
                    <strong>Agentic wiki gate</strong>
                    <p className="muted">{result.agentic.why_raw_retrieval_needed}</p>
                  </div>
                  <span className="score-badge">
                    {result.agentic.used_raw_sources ? "Wiki + raw" : "Wiki only"}
                  </span>
                </div>

                <div className="agentic-metrics">
                  <div>
                    <span>Context path</span>
                    <strong>{result.agentic.used_raw_sources ? "Wiki + raw sources" : "Wiki memory only"}</strong>
                  </div>
                  <div>
                    <span>Raw sources</span>
                    <strong>{result.agentic.used_raw_sources ? "Used" : "Skipped"}</strong>
                  </div>
                  <div>
                    <span>Context tokens</span>
                    <strong>{result.agentic.token_estimate.context_tokens}</strong>
                  </div>
                </div>

                <div className="pill-row">
                  <span className="pill">Confidence: {result.agentic.wiki_confidence}</span>
                  <span className="pill">Intent: {result.agentic.query_intent}</span>
                  {result.agentic.sufficiency_factors.slice(0, 3).map((factor) => (
                    <span className="pill" key={factor.name}>
                      {factor.name.replaceAll("_", " ")} · {factor.score.toFixed(2)}
                    </span>
                  ))}
                </div>

                <div className="list">
                  {result.agentic.suggested_updates.map((item) => (
                    <div className="list-item" key={`${item.kind}-${item.title}`}>
                      <strong>{item.title}</strong>
                      <p className="muted">{item.kind.replaceAll("_", " ")}</p>
                      <p>{item.reason}</p>
                      {item.markdown ? <pre className="preview-block">{item.markdown}</pre> : null}
                      {item.action !== "none" ? (
                        <button
                          className="button secondary"
                          disabled={Boolean(applyingSuggestionKey)}
                          onClick={() => void handleApplyAgenticUpdate(item)}
                          type="button"
                        >
                          {applyingSuggestionKey === `${item.action}-${item.target_slug}-${item.title}`
                            ? "Applying..."
                            : item.action === "update"
                              ? "Update wiki page"
                              : "Create wiki page"}
                        </button>
                      ) : null}
                    </div>
                  ))}
                </div>

                {agenticApplyResult ? (
                  <p className="notice success">
                    Wiki page updated: <Link href={`/wiki/${agenticApplyResult.slug}`}>{agenticApplyResult.title}</Link>
                  </p>
                ) : null}
                {agenticApplyError ? <p className="notice error">{agenticApplyError}</p> : null}

                {result.agentic.wiki_pages.length > 0 ? (
                  <div className="pill-row">
                    {result.agentic.wiki_pages.map((page) => (
                      <span className="pill" key={page.slug}>
                        {page.title} · {page.score.toFixed(2)}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}

            <label className="field">
              <span>Wiki title</span>
              <input onChange={(event) => setWikiTitle(event.target.value)} value={wikiTitle} />
            </label>

            <label className="checkbox-row">
              <input
                checked={mergeIfSimilar}
                onChange={(event) => setMergeIfSimilar(event.target.checked)}
                type="checkbox"
              />
              <span>Merge into a similar existing wiki page if a title match is found</span>
            </label>

            <button className="button secondary" disabled={isSaving} onClick={handleSave} type="button">
              {isSaving ? "Saving..." : "Save as wiki page"}
            </button>

            {saveResult ? (
              <p className="notice success">
                Wiki page {saveResult.action === "merged" ? "updated" : "created"}:{" "}
                <Link href={`/wiki/${saveResult.slug}`}>{saveResult.title}</Link>
              </p>
            ) : null}
            {saveError ? <p className="notice error">{saveError}</p> : null}

            <div className="list">
              {result.sources.length === 0 ? (
                <div className="list-item">No source chunks were retrieved.</div>
              ) : (
                result.sources.map((source, index) => (
                  <div className="list-item" key={`${source.document_id}-${index}`}>
                    <strong>{source.filename}</strong>
                    <p className="muted">Score: {source.score.toFixed(2)}</p>
                    <p>{source.text.slice(0, 360)}...</p>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : (
          <div className="list">
            <div className="list-item">A wiki-first answer will appear here after you run a question</div>
            <div className="list-item">Retrieved wiki passages and source chunks will be listed with scores</div>
            <div className="list-item">Useful answers can be saved back into the wiki as durable pages</div>
          </div>
        )}
      </article>
    </section>
  );
}
