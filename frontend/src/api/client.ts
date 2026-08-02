/* Purpose: typed ScreenSort API client. Callers: frontend views and tests. Deps: Vite env, Fetch, FormData, URLSearchParams. API: ScreenshotRecord, watcher types, uploadScreenshot, listScreenshots, watcher calls, imageUrl. Side effects: performs HTTP requests. */
export type ScreenshotRecord = {
  id: number;
  original_filename: string;
  stored_filename: string;
  path: string;
  category: string;
  confidence: number;
  tags: string[];
  ocr_text?: string | null;
  created_at: string;
};

export type ScreenshotFilters = {
  query?: string;
  category?: string;
  tag?: string;
};

export type WatcherStatus = {
  screenshots_dir: string;
  organized_dir: string;
  organize_mode: 'copy' | 'move';
  source_exists: boolean;
};

export type ScanSummary = {
  seen: number;
  ingested: number;
  skipped: number;
  failed: number;
  records: ScreenshotRecord[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined;

const authHeaders = (): HeadersInit => (API_KEY ? { 'X-API-Key': API_KEY } : {});

async function parseResponse<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail ?? 'Request failed.');
  return body as T;
}

export async function uploadScreenshot(file: File): Promise<ScreenshotRecord> {
  const body = new FormData();
  body.append('file', file);

  return parseResponse<ScreenshotRecord>(
    await fetch(`${API_BASE_URL}/screenshots`, {
      method: 'POST',
      headers: authHeaders(),
      body,
    }),
  );
}

export async function listScreenshots(filters: ScreenshotFilters = {}, init?: RequestInit): Promise<ScreenshotRecord[]> {
  const params = new URLSearchParams();
  if (filters.query) params.set('query', filters.query);
  if (filters.category) params.set('category', filters.category);
  if (filters.tag) params.set('tag', filters.tag);
  const query = params.toString();

  return parseResponse<ScreenshotRecord[]>(await fetch(`${API_BASE_URL}/screenshots${query ? `?${query}` : ''}`, { ...init, headers: { ...authHeaders(), ...init?.headers } }));
}

export async function getWatcherStatus(): Promise<WatcherStatus> {
  return parseResponse<WatcherStatus>(await fetch(`${API_BASE_URL}/watcher/status`, { headers: authHeaders() }));
}

export async function scanWatcherFolder(screenshotsDir?: string): Promise<ScanSummary> {
  return parseResponse<ScanSummary>(await fetch(`${API_BASE_URL}/watcher/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(screenshotsDir ? { screenshots_dir: screenshotsDir } : {}),
  }));
}

export async function deleteScreenshot(id: number): Promise<void> {
  await parseResponse<{ deleted: boolean }>(await fetch(`${API_BASE_URL}/screenshots/${id}`, { method: 'DELETE', headers: authHeaders() }));
}

export function imageUrl(id: number): string {
  const authQuery = API_KEY ? `?api_key=${encodeURIComponent(API_KEY)}` : '';
  return `${API_BASE_URL}/screenshots/${id}/image${authQuery}`;
}
