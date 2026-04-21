import { AskClient } from "@/components/ask-client";
import { api } from "@/lib/api";

export default async function AskPage() {
  const settings = await api.getSettings();

  return (
    <>
      <section className="page-heading">
        <div>
          <span className="eyebrow">Wiki-first QA</span>
          <h2>Ask questions against the knowledge layer</h2>
        </div>
        <p>Query the wiki, inspect the supporting evidence, then save useful answers back into the workspace.</p>
      </section>
      <AskClient settings={settings} />
    </>
  );
}
