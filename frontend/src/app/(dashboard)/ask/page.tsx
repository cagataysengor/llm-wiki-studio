import { AskClient } from "@/components/ask-client";
import { api } from "@/lib/api";

export default async function AskPage() {
  const settings = await api.getSettings();

  return (
    <>
      <section className="page-heading">
        <div>
          <span className="eyebrow">Ask AI</span>
          <h2>Question-answer workflow</h2>
        </div>
        <p>Ask the backend directly, inspect sources, then save the answer into the wiki.</p>
      </section>
      <AskClient settings={settings} />
    </>
  );
}
