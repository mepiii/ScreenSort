/**
 * Purpose: Render a screenshot library card with classification metadata.
 * Callers: LibraryPage grid.
 * Deps: ScreenSort API image URL helper and ScreenshotRecord type.
 * API: ScreenshotCard component props.
 * Side effects: Loads screenshot image from the API.
 */
import { imageUrl, ScreenshotRecord } from '../api/client';

type ScreenshotCardProps = {
  screenshot: ScreenshotRecord;
  onDelete?: (screenshot: ScreenshotRecord) => void;
  deleting?: boolean;
};

const OCR_PREVIEW_MAX_LENGTH = 160;

type SegmenterLike = new (locale?: string, options?: { granularity: 'grapheme' }) => {
  segment(text: string): Iterable<{ segment: string }>;
};

const graphemes = (text: string) => {
  const segmenter = (Intl as typeof Intl & { Segmenter?: SegmenterLike }).Segmenter;
  if (!segmenter) return Array.from(text);
  return Array.from(new segmenter(undefined, { granularity: 'grapheme' }).segment(text), ({ segment }) => segment);
};

const ocrPreview = (text?: string | null) => {
  const trimmed = text?.trim();
  if (!trimmed) return null;
  const chars = graphemes(trimmed);
  return chars.length > OCR_PREVIEW_MAX_LENGTH ? `${chars.slice(0, OCR_PREVIEW_MAX_LENGTH).join('')}…` : trimmed;
};

export default function ScreenshotCard({ screenshot, onDelete, deleting = false }: ScreenshotCardProps) {
  const preview = ocrPreview(screenshot.ocr_text);

  return (
    <article className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900 shadow-xl shadow-black/20">
      <img alt={screenshot.original_filename} className="aspect-video w-full bg-slate-950 object-cover" src={imageUrl(screenshot.id)} />
      <div className="space-y-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="break-words font-semibold text-white">{screenshot.original_filename}</h3>
            <time className="text-sm text-slate-400" dateTime={screenshot.created_at}>
              {new Date(screenshot.created_at).toLocaleString()}
            </time>
          </div>
          <span className="break-words rounded-full bg-cyan-400/15 px-3 py-1 text-sm font-medium text-cyan-200">{screenshot.category}</span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-cyan-200">{Math.round(screenshot.confidence * 100)}% confidence</p>
          {onDelete ? (
            <button className="rounded-md border border-red-400/40 px-3 py-1 text-sm font-semibold text-red-200 hover:bg-red-950/50 disabled:cursor-not-allowed disabled:opacity-60" disabled={deleting} onClick={() => onDelete(screenshot)} type="button">
              {deleting ? 'Deleting…' : 'Delete'}
            </button>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {screenshot.tags.map((tag) => (
            <span className="rounded-full bg-slate-800 px-3 py-1 text-sm text-slate-200" key={tag}>{tag}</span>
          ))}
        </div>
        {preview ? (
          <section className="rounded-lg border border-slate-800 bg-slate-950/60 p-3" aria-label="OCR text">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">OCR text</p>
            <p className="mt-2 break-words text-sm text-slate-300">{preview}</p>
          </section>
        ) : null}
      </div>
    </article>
  );
}
