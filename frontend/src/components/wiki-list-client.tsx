"use client";

import Link from "next/link";
import { useState, useTransition } from "react";

import { api } from "@/lib/api";
import { WikiPage } from "@/lib/types";

type WikiListClientProps = {
  initialPages: WikiPage[];
};

export function WikiListClient({ initialPages }: WikiListClientProps) {
  const [pages, setPages] = useState(initialPages);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isPending, startTransition] = useTransition();

  function handleDelete(slug: string, title: string) {
    const confirmed = window.confirm(`Delete "${title}"? This only removes the wiki page.`);
    if (!confirmed) {
      return;
    }

    setError("");
    setMessage("");
    startTransition(() => {
      void (async () => {
        try {
          await api.deleteWikiPage(slug);
          setPages((current) => current.filter((page) => page.slug !== slug));
          setMessage(`Deleted wiki page: ${title}`);
        } catch (deleteError) {
          setError(deleteError instanceof Error ? deleteError.message : "Delete failed.");
        }
      })();
    });
  }

  return (
    <section className="panel">
      <h3>Saved pages</h3>
      {message ? <p className="notice success">{message}</p> : null}
      {error ? <p className="notice error">{error}</p> : null}
      <div className="list">
        {pages.length === 0 ? (
          <div className="list-item">No wiki pages available yet.</div>
        ) : (
          pages.map((page) => (
            <div className="list-item" key={page.slug}>
              <Link href={`/wiki/${page.slug}`}>
                <strong>{page.title}</strong>
              </Link>
              <p className="muted">{page.summary || "No summary yet."}</p>
              <div className="pill-row">
                {page.tags.map((tag) => (
                  <span className="pill" key={tag}>
                    {tag}
                  </span>
                ))}
              </div>
              {page.slug !== "index" && page.slug !== "log" ? (
                <button
                  className="button secondary"
                  disabled={isPending}
                  onClick={() => handleDelete(page.slug, page.title)}
                  type="button"
                >
                  Delete page
                </button>
              ) : (
                <span className="pill">system page</span>
              )}
            </div>
          ))
        )}
      </div>
    </section>
  );
}
