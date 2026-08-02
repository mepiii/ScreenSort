/**
 * Purpose: Provide screenshot library browsing, scan routing, and management UI.
 * Callers: App library route and LibraryPage tests.
 * Deps: React state/effect hooks, ScreenshotCard, ScreenSort API client.
 * API: Default LibraryPage component.
 * Side effects: Fetches, scans, and deletes screenshot records.
 */
import { ChangeEvent, FormEvent, useEffect, useState } from 'react';

import { deleteScreenshot, getWatcherStatus, listScreenshots, scanWatcherFolder, ScanSummary, ScreenshotRecord, WatcherStatus } from '../api/client';
import ScreenshotCard from '../components/ScreenshotCard';

export default function LibraryPage() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [tag, setTag] = useState('');
  const [scanPath, setScanPath] = useState('');
  const [screenshots, setScreenshots] = useState<ScreenshotRecord[]>([]);
  const [watcherStatus, setWatcherStatus] = useState<WatcherStatus | null>(null);
  const [scanSummary, setScanSummary] = useState<ScanSummary | null>(null);
  const [scanError, setScanError] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');

    void listScreenshots({ query, category, tag }, { signal: controller.signal })
      .then(setScreenshots)
      .catch((caught) => {
        if (caught instanceof DOMException && caught.name === 'AbortError') return;
        setError(caught instanceof Error ? caught.message : 'Failed to load screenshots.');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [query, category, tag, refreshToken]);

  useEffect(() => {
    let active = true;

    getWatcherStatus()
      .then((status) => {
        if (active) {
          setWatcherStatus(status);
          setScanPath(status.screenshots_dir);
        }
      })
      .catch(() => undefined);

    return () => {
      active = false;
    };
  }, []);

  const update = (setter: (value: string) => void) => (event: ChangeEvent<HTMLInputElement>) => setter(event.target.value);
  const resetFilters = () => {
    setQuery('');
    setCategory('');
    setTag('');
  };

  const scanFolder = async (event?: FormEvent) => {
    event?.preventDefault();
    setScanning(true);
    setScanError('');
    setScanSummary(null);

    try {
      setScanSummary(await scanWatcherFolder(scanPath.trim() || undefined));
      setRefreshToken((value) => value + 1);
    } catch (caught) {
      setScanError(caught instanceof Error ? caught.message : 'Failed to scan folder.');
    } finally {
      setScanning(false);
    }
  };

  const removeScreenshot = async (screenshot: ScreenshotRecord) => {
    if (!window.confirm(`Delete ${screenshot.original_filename}?`)) return;
    setDeletingId(screenshot.id);
    setDeleteError('');

    try {
      await deleteScreenshot(screenshot.id);
      setScreenshots((records) => records.filter((record) => record.id !== screenshot.id));
    } catch (caught) {
      setDeleteError(caught instanceof Error ? caught.message : 'Failed to delete screenshot.');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-6 sm:px-6 lg:px-8">
      <section className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-6 shadow-xl shadow-black/20 sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-cyan-300">Manage</p>
            <h2 className="text-3xl font-bold tracking-tight text-white">Screenshot control center</h2>
            <p className="mt-3 max-w-2xl text-slate-300">Scan any folder, search OCR text, review categories, and delete screenshots you no longer need.</p>
          </div>
          <div className="grid grid-cols-3 gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-center">
            <div>
              <p className="text-2xl font-bold text-white">{screenshots.length}</p>
              <p className="text-xs uppercase tracking-wide text-slate-400">Shown</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-cyan-200">{scanSummary?.ingested ?? 0}</p>
              <p className="text-xs uppercase tracking-wide text-slate-400">Ingested</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-amber-200">{scanSummary?.failed ?? 0}</p>
              <p className="text-xs uppercase tracking-wide text-slate-400">Failed</p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <form className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6" aria-label="Folder scan" onSubmit={scanFolder}>
          <div>
            <h3 className="text-lg font-semibold text-white">Full folder scan</h3>
            {watcherStatus ? <p className="mt-2 text-sm text-slate-300">Default: {watcherStatus.screenshots_dir} · Mode: {watcherStatus.organize_mode}</p> : null}
          </div>
          <label className="space-y-2 text-sm font-medium text-slate-200">
            <span>Folder path</span>
            <input aria-label="Folder path" className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-white" onChange={update(setScanPath)} placeholder="/home/user/Pictures/Screenshots" value={scanPath} />
          </label>
          <div className="flex flex-wrap gap-3">
            <button className="rounded-md bg-cyan-400 px-4 py-2 font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60" disabled={scanning} type="submit">
              {scanning ? 'Scanning folder…' : 'Full scan folder'}
            </button>
            {watcherStatus ? <button className="rounded-md border border-slate-700 px-4 py-2 font-semibold text-slate-200" onClick={() => setScanPath(watcherStatus.screenshots_dir)} type="button">Use default</button> : null}
          </div>
          {scanSummary ? <p className="text-sm text-cyan-100">Scan complete: {scanSummary.seen} seen, {scanSummary.ingested} ingested, {scanSummary.skipped} skipped, {scanSummary.failed} failed.</p> : null}
          {scanError ? <p className="rounded-md border border-red-400/40 bg-red-950/40 p-3 text-sm text-red-200" role="alert">{scanError}</p> : null}
        </form>

        <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6" aria-label="Library filters">
          <div>
            <h3 className="text-lg font-semibold text-white">Find screenshots</h3>
            <p className="mt-2 text-sm text-slate-400">Search filenames, categories, tags, and OCR text.</p>
          </div>
          <label className="space-y-2 text-sm font-medium text-slate-200">
            <span>Search</span>
            <input aria-label="Search screenshots" className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-white" onChange={update(setQuery)} type="search" value={query} />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-2 text-sm font-medium text-slate-200">
              <span>Category</span>
              <input aria-label="Category" className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-white" onChange={update(setCategory)} value={category} />
            </label>
            <label className="space-y-2 text-sm font-medium text-slate-200">
              <span>Tag</span>
              <input aria-label="Tag" className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-white" onChange={update(setTag)} value={tag} />
            </label>
          </div>
          <button className="rounded-md border border-slate-700 px-4 py-2 font-semibold text-slate-200" onClick={resetFilters} type="button">Clear filters</button>
        </section>
      </section>

      {loading ? <p className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-slate-300">Loading library…</p> : null}
      {error ? <p className="rounded-md border border-red-400/40 bg-red-950/40 p-3 text-sm text-red-200" role="alert">{error}</p> : null}
      {deleteError ? <p className="rounded-md border border-red-400/40 bg-red-950/40 p-3 text-sm text-red-200" role="alert">{deleteError}</p> : null}
      {!loading && !error && screenshots.length === 0 ? <p className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-slate-300">No screenshots found.</p> : null}
      {screenshots.length > 0 ? (
        <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-3" aria-label="Screenshot library results">
          {screenshots.map((screenshot) => (
            <ScreenshotCard deleting={deletingId === screenshot.id} key={screenshot.id} onDelete={removeScreenshot} screenshot={screenshot} />
          ))}
        </section>
      ) : null}
    </div>
  );
}
