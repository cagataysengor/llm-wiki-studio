export type DocumentItem = {
  id: string;
  filename: string;
  filepath: string;
  filetype?: string | null;
  created_at: string;
  text_length: number;
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
};

export type AskQuestionPayload = {
  question: string;
  provider: string;
  model_name: string;
  llm_url: string;
  embed_model: string;
  top_k: number;
};

export type SaveAnswerResponse = {
  slug: string;
  title: string;
  filepath: string;
  action: "created" | "merged";
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
  url: string;
  model_count: number;
  models: string[];
  detail?: string;
};
