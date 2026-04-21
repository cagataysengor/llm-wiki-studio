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
} from "@/lib/types";

type AskClientProps = {
  settings: PublicSettings;
};

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
  const [wikiTitle, setWikiTitle] = useState("");
  const [mergeIfSimilar, setMergeIfSimilar] = useState(true);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [saveResult, setSaveResult] = useState<SaveAnswerResponse | null>(null);
  const [error, setError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [waitSeconds, setWaitSeconds] = useState(0);
  const [localStatus, setLocalStatus] = useState<LocalServerStatus | null>(null);
  const [localStatusError, setLocalStatusError] = useState("");
  const [isAsking, setIsAsking] = useState(false);
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
        const status = await api.getLocalServerStatus();
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
  }, [provider]);

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
    setSaveResult(null);
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
                ? `Local model is thinking. This can take a while on llama.cpp servers. Elapsed: ${waitSeconds}s.`
                : `Request sent successfully. Waiting for the model response. Elapsed: ${waitSeconds}s.`}
            </div>
          ) : null}
          {isAsking && provider === "Local" ? (
            <div className="list-item">
              <strong>Live local run</strong>
              <p className="muted">
                The request is in progress. With local models, 30-90 seconds can be normal depending
                on CPU speed, context size, and model quantization.
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
        <h3>Answer and next action</h3>
        {result ? (
          <div className="stack">
            <pre className="code-block">{result.answer}</pre>

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
              {isSaving ? "Saving..." : "Save answer to wiki"}
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
            <div className="list-item">Grounded answer generated by the provider adapter</div>
            <div className="list-item">Retrieved source chunks with scores</div>
            <div className="list-item">One-click save-to-wiki flow from the QA result</div>
          </div>
        )}
      </article>
    </section>
  );
}
