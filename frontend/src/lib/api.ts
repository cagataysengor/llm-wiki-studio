import {
  AskQuestionPayload,
  AskResponse,
  DocumentItem,
  IngestResponse,
  LocalServerStatus,
  PublicSettings,
  SaveAnswerResponse,
  WikiDeleteResponse,
  WikiPage,
  WikiLintResponse,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await extractErrorMessage(response);
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}


async function extractErrorMessage(response: Response): Promise<string> {
  const fallback = `API request failed: ${response.status}`;
  const contentType = response.headers.get("content-type") ?? "";

  try {
    if (contentType.includes("application/json")) {
      const payload = await response.json();
      if (typeof payload?.detail === "string" && payload.detail.trim()) {
        return payload.detail;
      }
      if (Array.isArray(payload?.detail)) {
        return payload.detail
          .map((item: unknown) => {
            if (typeof item === "string") {
              return item;
            }
            if (item && typeof item === "object" && "msg" in item) {
              return String((item as { msg: unknown }).msg);
            }
            return "";
          })
          .filter(Boolean)
          .join(", ") || fallback;
      }
    }

    const text = await response.text();
    return text.trim() || fallback;
  } catch {
    return fallback;
  }
}

export const api = {
  getSettings: () => request<PublicSettings>("/settings/public"),
  getLocalServerStatus: () => request<LocalServerStatus>("/settings/local-status"),
  getDocuments: () => request<DocumentItem[]>("/documents"),
  getWikiPages: () => request<WikiPage[]>("/wiki"),
  getWikiPage: (slug: string) => request<WikiPage>(`/wiki/${slug}`),
  getWikiLintReport: () => request<WikiLintResponse>("/wiki/lint/report"),
  deleteWikiPage: (slug: string) =>
    request<WikiDeleteResponse>(`/wiki/${slug}`, {
      method: "DELETE",
    }),
  ingestDocument: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<IngestResponse>("/documents/ingest", {
      method: "POST",
      body: formData,
    });
  },
  askQuestion: (payload: AskQuestionPayload) =>
    request<AskResponse>("/qa/ask", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  saveAnswer: (payload: {
    title: string;
    question: string;
    answer: string;
    source_files: string[];
    merge_if_similar: boolean;
  }) =>
    request<SaveAnswerResponse>("/qa/save", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createWikiPage: (payload: { title: string; markdown: string }) =>
    request<WikiPage>("/wiki", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
