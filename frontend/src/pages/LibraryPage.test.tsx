/**
 * Purpose: Verify screenshot library browsing and filtering behavior.
 * Callers: Vitest runner.
 * Deps: React Testing Library, Vitest, LibraryPage, Fetch API.
 * API: LibraryPage interaction tests.
 * Side effects: Mocks global fetch calls.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import LibraryPage from './LibraryPage';
import { getWatcherStatus, scanWatcherFolder } from '../api/client';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client');
  return {
    ...actual,
    getWatcherStatus: vi.fn(),
    scanWatcherFolder: vi.fn(),
  };
});

const getWatcherStatusMock = vi.mocked(getWatcherStatus);
const scanWatcherFolderMock = vi.mocked(scanWatcherFolder);

const records = [
  {
    id: 7,
    original_filename: 'dashboard.png',
    stored_filename: 'stored-dashboard.png',
    path: '/uploads/stored-dashboard.png',
    category: 'Dashboard',
    confidence: 0.876,
    tags: ['metrics', 'charts'],
    created_at: '2026-04-27T00:00:00Z',
  },
];

const jsonResponse = (body: unknown) => ({
  ok: true,
  json: vi.fn().mockResolvedValue(body),
}) as unknown as Response;

describe('LibraryPage', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse(records));
    getWatcherStatusMock.mockResolvedValue({
      screenshots_dir: '/watch/inbox',
      organized_dir: '/watch/organized',
      organize_mode: 'copy',
      source_exists: true,
    });
    scanWatcherFolderMock.mockResolvedValue({ seen: 3, ingested: 1, skipped: 1, failed: 1, records });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    globalThis.fetch = originalFetch;
  });

  it('mentions OCR text in search helper copy', () => {
    render(<LibraryPage />);

    expect(screen.getByText('Search filenames, categories, tags, and OCR text.')).toBeInTheDocument();
  });

  it('loads and displays screenshot cards', async () => {
    render(<LibraryPage />);

    expect(screen.getByText(/loading library/i)).toBeInTheDocument();
    expect(await screen.findByText('dashboard.png')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('88% confidence')).toBeInTheDocument();
    expect(screen.getByText('metrics')).toBeInTheDocument();
    expect(screen.getByAltText('dashboard.png')).toHaveAttribute('src', 'http://localhost:8000/api/screenshots/7/image');
  });

  it('refetches screenshots with encoded filters', async () => {
    const user = userEvent.setup();
    render(<LibraryPage />);

    await screen.findByText('dashboard.png');
    await user.type(screen.getByLabelText(/search screenshots/i), 'term & space');
    await user.type(screen.getByLabelText(/category/i), 'work/tools');
    await user.type(screen.getByLabelText(/tag/i), 'terminal+#1');

    await waitFor(() => expect(globalThis.fetch).toHaveBeenLastCalledWith(
      'http://localhost:8000/api/screenshots?query=term+%26+space&category=work%2Ftools&tag=terminal%2B%231',
      { headers: {}, signal: expect.any(AbortSignal) },
    ));
  });

  it('renders watcher status source and mode', async () => {
    render(<LibraryPage />);

    expect(await screen.findByText('Default: /watch/inbox · Mode: copy')).toBeInTheDocument();
  });

  it('scans watcher folder and shows summary', async () => {
    const user = userEvent.setup();
    render(<LibraryPage />);

    await screen.findByText('dashboard.png');
    await user.click(screen.getByRole('button', { name: /scan folder/i }));

    expect(scanWatcherFolderMock).toHaveBeenCalledTimes(1);
    expect(await screen.findByText('Scan complete: 3 seen, 1 ingested, 1 skipped, 1 failed.')).toBeInTheDocument();
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(2));
  });

  it('refreshes with latest filters after scan completes', async () => {
    const user = userEvent.setup();
    let resolveScan: (value: Awaited<ReturnType<typeof scanWatcherFolder>>) => void;
    scanWatcherFolderMock.mockReturnValue(new Promise((resolve) => {
      resolveScan = resolve;
    }));
    render(<LibraryPage />);

    await screen.findByText('dashboard.png');
    await user.click(screen.getByRole('button', { name: /scan folder/i }));
    await user.type(screen.getByLabelText(/search screenshots/i), 'fresh');

    resolveScan!({ seen: 1, ingested: 1, skipped: 0, failed: 0, records });

    expect(await screen.findByText('Scan complete: 1 seen, 1 ingested, 0 skipped, 0 failed.')).toBeInTheDocument();
    await waitFor(() => expect(globalThis.fetch).toHaveBeenLastCalledWith(
      'http://localhost:8000/api/screenshots?query=fresh',
      { headers: {}, signal: expect.any(AbortSignal) },
    ));
  });

  it('shows scan error alert', async () => {
    const user = userEvent.setup();
    scanWatcherFolderMock.mockRejectedValue(new Error('Scan failed.'));
    render(<LibraryPage />);

    await screen.findByText('dashboard.png');
    await user.click(screen.getByRole('button', { name: /scan folder/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Scan failed.');
  });

  it('aborts stale requests without showing abort errors and ignores watcher cleanup', async () => {
    const abortError = new DOMException('Aborted', 'AbortError');
    const abortSpy = vi.spyOn(AbortController.prototype, 'abort');
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => new Promise((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(abortError), { once: true });
    }));
    globalThis.fetch = fetchMock as typeof fetch;
    getWatcherStatusMock.mockResolvedValue({
      screenshots_dir: '/late',
      organized_dir: '/organized',
      organize_mode: 'move',
      source_exists: true,
    });

    const { unmount } = render(<LibraryPage />);
    unmount();

    await waitFor(() => expect(abortSpy).toHaveBeenCalled());
    expect(screen.queryByText('Source: /late · Mode: move')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
