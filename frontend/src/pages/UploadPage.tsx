/**
 * Purpose: Provide screenshot upload, classification, and result review UI.
 * Callers: App route rendering and UploadPage tests.
 * Deps: React state hooks, Dropzone, ScreenSort API client.
 * API: Default UploadPage component.
 * Side effects: Uploads selected image files to the API.
 */
import { FormEvent, useState } from 'react';

import { imageUrl, ScreenshotRecord, uploadScreenshot } from '../api/client';
import Dropzone from '../components/Dropzone';

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<ScreenshotRecord | null>(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);

  const handleFile = (file: File) => {
    setSelectedFile(file);
    setResult(null);
    setError('');
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedFile || uploading) return;

    setUploading(true);
    setError('');
    setResult(null);
    try {
      setResult(await uploadScreenshot(selectedFile));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_360px]">
      <section className="overflow-hidden rounded-3xl border border-white/10 bg-white/[0.04] shadow-2xl shadow-black/30 backdrop-blur">
        <div className="border-b border-white/10 bg-gradient-to-br from-cyan-400/20 via-slate-900 to-fuchsia-500/10 p-8 sm:p-10">
          <p className="mb-3 text-sm font-bold uppercase tracking-[0.3em] text-cyan-200">Upload</p>
          <h2 className="max-w-2xl text-4xl font-black tracking-tight text-white sm:text-5xl">Classify screenshots fast.</h2>
          <p className="mt-4 max-w-xl text-base text-slate-300">Drop PNG, JPEG, or WebP files. ScreenSort labels category, confidence, tags, and OCR text.</p>
        </div>

        <form className="space-y-5 p-6 sm:p-8" onSubmit={handleSubmit}>
          <Dropzone disabled={uploading} onFile={handleFile} />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            {selectedFile ? <p className="min-w-0 text-sm text-slate-300">Selected: <span className="font-semibold text-white">{selectedFile.name}</span></p> : <p className="text-sm text-slate-500">No file selected.</p>}
            <button
              className="rounded-full bg-cyan-300 px-5 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-950/30 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400 disabled:shadow-none"
              disabled={!selectedFile || uploading}
              type="submit"
            >
              {uploading ? 'Classifying…' : 'Classify screenshot'}
            </button>
          </div>
          {error ? <p className="rounded-2xl border border-red-400/40 bg-red-950/40 p-4 text-sm text-red-200" role="alert">{error}</p> : null}
        </form>
      </section>

      <aside className="rounded-3xl border border-white/10 bg-slate-900/70 p-6 shadow-2xl shadow-black/20">
        <p className="text-sm font-bold uppercase tracking-[0.25em] text-slate-400">Workflow</p>
        <div className="mt-6 space-y-4">
          {['Upload screenshot', 'AI classifies content', 'Review in Library'].map((step, index) => (
            <div className="flex gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-4" key={step}>
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-cyan-300 text-sm font-black text-slate-950">{index + 1}</span>
              <p className="font-semibold text-white">{step}</p>
            </div>
          ))}
        </div>
      </aside>

      {result ? (
        <section className="grid gap-6 rounded-3xl border border-white/10 bg-slate-900/80 p-6 shadow-2xl shadow-black/20 md:grid-cols-[minmax(0,1fr)_320px] lg:col-span-2">
          <img alt={result.original_filename} className="max-h-[560px] w-full rounded-2xl border border-white/10 bg-slate-950 object-contain" src={imageUrl(result.id)} />
          <div className="space-y-5">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.25em] text-slate-400">Category</p>
              <h3 className="mt-2 break-words text-3xl font-black text-white">{result.category}</h3>
            </div>
            <p className="rounded-2xl bg-cyan-300/10 p-4 text-lg font-bold text-cyan-100">{Math.round(result.confidence * 100)}% confidence</p>
            <div className="flex flex-wrap gap-2">
              {result.tags.map((tag) => (
                <span className="rounded-full bg-white/10 px-3 py-1 text-sm font-semibold text-slate-200" key={tag}>{tag}</span>
              ))}
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
