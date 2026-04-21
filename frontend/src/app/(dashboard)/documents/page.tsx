import { DocumentsClient } from "@/components/documents-client";
import { api } from "@/lib/api";

export default async function DocumentsPage() {
  const documents = await api.getDocuments().catch(() => []);

  return (
    <>
      <section className="page-heading">
        <div>
          <span className="eyebrow">Documents</span>
          <h2>Indexed source files</h2>
        </div>
        <p>Upload flow is now exposed from the backend and ready for a real UI form.</p>
      </section>

      <DocumentsClient initialDocuments={documents} />
    </>
  );
}
