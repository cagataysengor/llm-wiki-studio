import Link from "next/link";

import { api } from "@/lib/api";

export default async function WikiPageList() {
  const pages = await api.getWikiPages().catch(() => []);

  return (
    <>
      <section className="page-heading">
        <div>
          <span className="eyebrow">Wiki</span>
          <h2>Knowledge pages</h2>
        </div>
        <p>Persisted markdown now has a dedicated browsing surface.</p>
      </section>

      <section className="panel">
        <h3>Saved pages</h3>
        <div className="list">
          {pages.length === 0 ? (
            <div className="list-item">No wiki pages available yet.</div>
          ) : (
            pages.map((page) => (
              <Link className="list-item" href={`/wiki/${page.slug}`} key={page.slug}>
                <strong>{page.title}</strong>
                <p className="muted">{page.summary || "No summary yet."}</p>
                <div className="pill-row">
                  {page.tags.map((tag) => (
                    <span className="pill" key={tag}>
                      {tag}
                    </span>
                  ))}
                </div>
              </Link>
            ))
          )}
        </div>
      </section>
    </>
  );
}

