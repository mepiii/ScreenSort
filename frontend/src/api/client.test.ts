/* Purpose: API client contract tests. Callers: Vitest. Deps: client module, fetch/FormData mocks. API: upload/list/image behavior tests. Side effects: patches global fetch. */
import { afterEach, describe, expect, it, vi } from 'vitest';

import { getWatcherStatus, imageUrl, listScreenshots, scanWatcherFolder, uploadScreenshot } from './client';

const record = {
  id: 1,
  original_filename: 'screen.png',
  stored_filename: 'abc.png',
  path: '/uploads/abc.png',
  category: 'work',
  confidence: 0.92,
  tags: ['terminal'],
  created_at: '2026-04-27T12:00:00Z',
};

describe('API client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('uploads screenshots as multipart form data', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(record), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const file = new File(['image'], 'screen.png', { type: 'image/png' });
    await expect(uploadScreenshot(file)).resolves.toEqual(record);

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/screenshots', {
      method: 'POST',
      headers: {},
      body: expect.any(FormData),
    });
    expect(fetchMock.mock.calls[0][1].body.get('file')).toBe(file);
  });

  it('lists screenshots with URLSearchParams filters and request init', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify([record]), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const init = { signal: new AbortController().signal };
    await expect(listScreenshots({ query: 'term & space', category: 'work/tools', tag: 'terminal+#1' }, init)).resolves.toEqual([record]);

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/screenshots?query=term+%26+space&category=work%2Ftools&tag=terminal%2B%231',
      { ...init, headers: {} },
    );
  });

  it('throws API detail for failed responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Nope' }), { status: 400 })));

    await expect(listScreenshots()).rejects.toThrow('Nope');
  });

  it('builds image URLs from the configured base URL', () => {
    expect(imageUrl(7)).toBe('http://localhost:8000/api/screenshots/7/image');
  });

  it('gets watcher status', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      screenshots_dir: 'data/inbox',
      organized_dir: 'data/organized',
      organize_mode: 'copy',
      source_exists: true,
    }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const status = await getWatcherStatus();

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/watcher/status', { headers: {} });
    expect(status.source_exists).toBe(true);
  });

  it('scans watcher folder', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      seen: 1,
      ingested: 1,
      skipped: 0,
      failed: 0,
      records: [],
    }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const summary = await scanWatcherFolder();

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/watcher/scan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    expect(summary.ingested).toBe(1);
  });
});
