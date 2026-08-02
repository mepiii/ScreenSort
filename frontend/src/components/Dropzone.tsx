/**
 * Purpose: Provide screenshot file selection through click, drag, and drop.
 * Callers: Upload screens and component tests.
 * Deps: React drag/input events, lucide-react UploadCloud.
 * API: Dropzone({ onFile, disabled }).
 * Side effects: Invokes onFile with accepted image files from user input.
 */
import { UploadCloud } from 'lucide-react';
import { DragEvent, ChangeEvent, useState } from 'react';

type DropzoneProps = {
  onFile: (file: File) => void;
  disabled?: boolean;
};

const acceptedTypes = new Set(['image/png', 'image/jpeg', 'image/webp']);
const accept = 'image/png,image/jpeg,image/webp';

export default function Dropzone({ onFile, disabled = false }: DropzoneProps) {
  const [dragging, setDragging] = useState(false);

  const submitFile = (file?: File) => {
    if (!disabled && file && acceptedTypes.has(file.type)) onFile(file);
  };

  const handleDragOver = (event: DragEvent<HTMLLabelElement>) => {
    if (disabled) return;
    event.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => setDragging(false);

  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
    if (disabled) return;
    event.preventDefault();
    setDragging(false);
    submitFile(event.dataTransfer.files[0]);
  };

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    submitFile(event.target.files?.[0]);
    event.target.value = '';
  };

  return (
    <label
      className={`group flex min-h-72 cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed p-10 text-center transition ${
        dragging ? 'border-cyan-300 bg-cyan-300/10 text-cyan-50' : 'border-white/15 bg-slate-950/60 text-slate-300'
      } ${disabled ? 'cursor-not-allowed opacity-50' : 'hover:border-cyan-300 hover:bg-cyan-300/5 hover:text-white'}`}
      aria-disabled={disabled}
      data-testid="dropzone"
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <span className="mb-5 grid h-16 w-16 place-items-center rounded-2xl bg-cyan-300/10 text-cyan-200 ring-1 ring-cyan-300/20 transition group-hover:scale-105 group-hover:bg-cyan-300/15">
        <UploadCloud aria-hidden="true" className="h-8 w-8" />
      </span>
      <span className="text-xl font-black text-white">Drop screenshot here</span>
      <span className="mt-2 text-sm text-slate-400">or click to choose PNG, JPEG, WebP</span>
      <input
        accept={accept}
        aria-label="Choose screenshot"
        className="sr-only"
        disabled={disabled}
        onChange={handleChange}
        type="file"
      />
    </label>
  );
}
