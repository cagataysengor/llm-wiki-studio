import Link from "next/link";

import { api } from "@/lib/api";
import { WikiListClient } from "@/components/wiki-list-client";

export default async function WikiPageList() {
  const [pages, lintReport] = await Promise.all([
    api.getWikiPages().catch(() => []),
    api.getWikiLintReport().catch(() => null),
  ]);

  return (
    <>
      <section className="page-heading">
        <div>
          <span className="eyebrow">Wiki</span>
          <h2>Knowledge pages</h2>
        </div>
        <p>Persisted markdown now has a dedicated browsing surface.</p>
      </section>

      {lintReport ? (
        <section className="panel">
          <h3>Wiki health</h3>
          <div className="stack">
            <p className="muted">
              Checked {lintReport.checked_pages} page{lintReport.checked_pages === 1 ? "" : "s"}.
            </p>
            <div className="list">
              {lintReport.findings.map((finding, index) => (
                <div className="list-item" key={`${finding.category}-${finding.page_slug ?? "global"}-${index}`}>
                  <strong>
                    {finding.category} · {finding.severity}
                  </strong>
                  <p className="muted">{finding.message}</p>
                  {finding.page_slug ? (
                    <Link href={`/wiki/${finding.page_slug}`}>{finding.page_title ?? finding.page_slug}</Link>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <WikiListClient initialPages={pages} />
    </>
  );
}
