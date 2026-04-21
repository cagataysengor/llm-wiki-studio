import { api } from "@/lib/api";

type WikiDetailPageProps = {
  params: Promise<{ slug: string }>;
};

export default async function WikiDetailPage({ params }: WikiDetailPageProps) {
  const { slug } = await params;
  const page = await api.getWikiPage(slug);

  return (
    <>
      <section className="page-heading">
        <div>
          <span className="eyebrow">Wiki Detail</span>
          <h2>{page.title}</h2>
        </div>
        <p>{page.summary || "Detailed persisted markdown page."}</p>
      </section>

      <section className="panel">
        <h3>Rendered markdown source</h3>
        <pre className="code-block">{page.markdown}</pre>
      </section>
    </>
  );
}

