export interface AIProvider {
  id: string;
  name: string;
  has_models_api: boolean;
  models: { id: string; name: string }[];
  api_configured: boolean;
}

export interface ProviderConfig {
  provider: string;
  name: string;
  base_url: string;
  model: string;
  api_key: string;
  models: { id: string; name: string }[];
  has_models_api: boolean;
  endpoint: string;
}

export interface ArticleImage {
  id: string;
  image_index: number;
  original_url: string | null;
  local_path: string | null;
}

export interface PublishRecord {
  id: string;
  article_id: string;
  platform: string;
  title: string | null;
  content_snapshot: string | null;
  status: string;
  error_message: string | null;
  published_at: string | null;
  created_at: string;
}

export interface Article {
  id: string;
  source_url: string;
  source_title: string | null;
  source_account: string | null;
  author: string | null;
  publish_time: string | null;
  cover_path: string | null;
  clean_html: string | null;
  content_text: string | null;

  current_title: string | null;
  current_content: string | null;

  fetch_status: string;
  ai_edit_status: string;
  ai_edit_error: string | null;

  created_at: string;
  updated_at: string;
  images: ArticleImage[];
  publish_records: PublishRecord[];
}

export interface ArticleListResponse {
  total: number;
  items: Article[];
}

export interface BatchCrawlItemResult {
  url: string;
  status: 'success' | 'failed';
  article_id?: string;
  title?: string;
  error?: string;
}

export interface BatchCrawlResponse {
  total: number;
  success_count: number;
  failed_count: number;
  results: BatchCrawlItemResult[];
}

const API_BASE = '/api/v1';

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export const api = {
  fetchArticle: (url: string) =>
    apiFetch<Article>('/articles/fetch', {
      method: 'POST',
      body: JSON.stringify({ url }),
    }),

  listArticles: (skip = 0, limit = 20) =>
    apiFetch<ArticleListResponse>(`/articles?skip=${skip}&limit=${limit}`),

  getArticle: (id: string) =>
    apiFetch<Article>(`/articles/${id}`),

  updateArticle: (id: string, data: { current_title?: string; current_content?: string }) =>
    apiFetch<Article>(`/articles/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteArticle: (id: string) =>
    apiFetch<{ success: boolean }>(`/articles/${id}`, { method: 'DELETE' }),

  aiEdit: (articleId: string) =>
    apiFetch<Article>(`/ai/edit/${articleId}`, { method: 'POST' }),

  publish: (articleId: string) =>
    apiFetch<{ success: boolean; message: string }>(`/publish/${articleId}`, { method: 'POST' }),

  clearPublishHistory: (articleId: string) =>
    apiFetch<{ success: boolean; deleted_count: number; message: string }>(`/publish/${articleId}/history`, {
      method: 'DELETE',
    }),

  batchCrawlArticles: (urls: string[]) =>
    apiFetch<BatchCrawlResponse>('/articles/crawl/batch', {
      method: 'POST',
      body: JSON.stringify({ urls }),
    }),

  getProviders: () => apiFetch<{ providers: AIProvider[] }>("/config/providers"),

  getProviderConfig: () => apiFetch<ProviderConfig>("/config/provider"),

  setProvider: (provider: string) =>
    apiFetch<ProviderConfig>("/config/provider", {
      method: "POST",
      body: JSON.stringify({ provider }),
    }),

  setApiKey: (provider: string, apiKey: string) =>
    apiFetch<{ success: boolean }>("/config/api-key", {
      method: "POST",
      body: JSON.stringify({ provider, api_key: apiKey }),
    }),

  setModel: (provider: string, model: string) =>
    apiFetch<{ success: boolean }>("/config/model", {
      method: "POST",
      body: JSON.stringify({ provider, model }),
    }),

  getModels: (provider: string) =>
    apiFetch<{ models: { id: string; name: string }[] }>(`/config/models/${provider}`),
};
