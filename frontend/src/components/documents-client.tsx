"use client";

import { useState, useTransition } from "react";

import { api } from "@/lib/api";
import { DocumentItem } from "@/lib/types";

type DocumentsClientProps = {
  initialDocuments: DocumentItem[];
};

export function DocumentsClient({ initialDocuments }: DocumentsClientProps) {
  const [documents, setDocuments] = useState(initialDocuments);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [isPending, startTransition] = useTransition();

  function handleUpload() {
    if (!selectedFile) {
      setError("Please select a file first.");
      setMessage("");
      return;
    }

    setError("");
    setMessage("");

    startTransition(() => {
      void (async () => {
        try {
          const result = await api.ingestDocument(selectedFile);
          const refreshed = await api.getDocuments();
          setDocuments(refreshed);
          setMessage(
            `${result.filename} indexed successfully with ${result.chunk_count} chunks.`
          );
          setSelectedFile(null);
        } catch (uploadError) {
          setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
        }
      })();
    });
  }

  return (
    <>
      <section className="panel">
        <h3>Upload a new source</h3>
        <div className="stack">
          <label className="field">
            <span>Supported in this scaffold</span>
            <input
              type="file"
              accept=".txt,.md,.csv,.json,.py,.html,.pdf,.docx"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <div className="pill-row">
            <span className="pill">txt</span>
            <span className="pill">md</span>
            <span className="pill">csv</span>
            <span className="pill">json</span>
            <span className="pill">py</span>
            <span className="pill">html</span>
            <span className="pill">pdf</span>
            <span className="pill">docx</span>
          </div>
          <button className="button" disabled={isPending} onClick={handleUpload} type="button">
            {isPending ? "Indexing..." : "Upload and index"}
          </button>
          {message ? <p className="notice success">{message}</p> : null}
          {error ? <p className="notice error">{error}</p> : null}
        </div>
      </section>

      <section className="panel">
        <h3>Backend-connected inventory</h3>
        <div className="list">
          {documents.length === 0 ? (
            <div className="list-item">No documents found yet.</div>
          ) : (
            documents.map((document) => (
              <div className="list-item" key={document.id}>
                <strong>{document.filename}</strong>
                <p className="muted">
                  {document.filetype ?? "unknown"} · {document.text_length} chars
                </p>
                <code>{document.filepath}</code>
              </div>
            ))
          )}
        </div>
      </section>
    </>
  );
}
