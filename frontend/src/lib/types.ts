export type DocumentItem = {
  id: string;
  filename: string;
  filepath: string;
  filetype?: string | null;
  created_at: string;
  text_length: number;
};

export type IngestResponse = {
  document_id: string;
  filename: string;
  chunk_count: number;
  text_length: number;
  wiki_page_slug?: string | null;
  wiki_page_title?: string | null;
  topic_page_slugs: string[];
};

export type WikiPage = {
  slug: string;
  title: string;
  filepath: string;
  summary?: string | null;
  tags: string[];
  source_doc_ids: string[];
  updated_at: string;
  markdown?: string;
};

export type AskResponse = {
  question: string;
  answer: string;
  sources: Array<{
    document_id: string;
    filename: string;
    text: string;
    score: number;
  }>;
  agentic?: AgenticWikiReport | null;
};

export type AskQuestionPayload = {
  question: string;
  provider: string;
  model_name: string;
  llm_url: string;
  embed_model: string;
  top_k: number;
  agentic_mode: boolean;
};

export type AgenticWikiReport = {
  enabled: boolean;
  wiki_sufficiency_score: number;
  wiki_coverage: "strong" | "partial" | "weak" | "missing" | string;
  wiki_confidence: "high" | "medium" | "low" | string;
  query_intent: string;
  sufficiency_factors: Array<{
    name: string;
    score: number;
    reason: string;
  }>;
  used_raw_sources: boolean;
  why_raw_retrieval_needed: string;
  wiki_pages: Array<{
    slug: string;
    title: string;
    score: number;
  }>;
  matched_wiki_terms: string[];
  matched_source_terms: string[];
  suggested_updates: Array<{
    kind: string;
    action: "create" | "update" | "none" | string;
    target_slug: string;
    title: string;
    reason: string;
    markdown: string;
  }>;
  agent_steps: string[];
  token_estimate: {
    context_tokens: number;
    answer_tokens: number;
    raw_retrieval_avoided: boolean;
  };
};

export type SaveAnswerResponse = {
  slug: string;
  title: string;
  filepath: string;
  action: "created" | "merged";
};

export type WikiLintFinding = {
  severity: string;
  category: string;
  page_slug?: string | null;
  page_title?: string | null;
  message: string;
};

export type WikiLintResponse = {
  checked_pages: number;
  findings: WikiLintFinding[];
};

export type WikiDeleteResponse = {
  slug: string;
  title: string;
  action: string;
};

export type PublicSettings = {
  app_name: string;
  default_embed_model: string;
  embedding_provider: string;
  embedding_mode: string;
  embedding_url: string;
  default_provider: string;
  providers: string[];
  provider_server_configured: Record<string, boolean>;
  provider_runtime_support: Record<string, boolean>;
  provider_defaults: Record<string, { url: string; model: string }>;
  data_dir: string;
};

export type LocalServerStatus = {
  reachable: boolean;
  auth_ok: boolean;
  url: string;
  model_count: number;
  models: string[];
  selected_model?: string;
  model_available?: boolean | null;
  diagnostics?: string[];
  detail?: string;
};
