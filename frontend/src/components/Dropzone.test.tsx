/**
 * Purpose: Verify Dropzone file selection and drag/drop behavior.
 * Callers: Vitest CLI.
 * Deps: React Testing Library, Vitest, Dropzone component.
 * API: Dropzone behavior test suite.
 * Side effects: Creates DOM File and DataTransfer test doubles.
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import Dropzone from './Dropzone';

const imageFile = (name = 'shot.png', type = 'image/png') => new File(['image'], name, { type });
const textFile = () => new File(['text'], 'notes.txt', { type: 'text/plain' });

describe('Dropzone', () => {
  it('renders a label-backed hidden screenshot input with image accepts', () => {
    render(<Dropzone onFile={vi.fn()} disabled={false} />);

    const input = screen.getByLabelText('Choose screenshot');

    expect(input).toHaveAttribute('type', 'file');
    expect(input).toHaveAttribute('accept', 'image/png,image/jpeg,image/webp');
    expect(input).toHaveClass('sr-only');
  });

  it('calls onFile when a user selects an image', () => {
    const onFile = vi.fn();
    const file = imageFile('photo.jpeg', 'image/jpeg');
    render(<Dropzone onFile={onFile} disabled={false} />);

    fireEvent.change(screen.getByLabelText('Choose screenshot'), { target: { files: [file] } });

    expect(onFile).toHaveBeenCalledWith(file);
  });

  it('ignores selected non-image files and disabled selections', () => {
    const onFile = vi.fn();
    const { rerender } = render(<Dropzone onFile={onFile} disabled={false} />);

    fireEvent.change(screen.getByLabelText('Choose screenshot'), { target: { files: [textFile()] } });
    rerender(<Dropzone onFile={onFile} disabled />);
    fireEvent.change(screen.getByLabelText('Choose screenshot'), { target: { files: [imageFile()] } });

    expect(onFile).not.toHaveBeenCalled();
  });

  it('shows drag state on dragover and clears it on dragleave', () => {
    render(<Dropzone onFile={vi.fn()} disabled={false} />);
    const area = screen.getByTestId('dropzone');

    fireEvent.dragOver(area);
    expect(area).toHaveClass('border-cyan-300');

    fireEvent.dragLeave(area);
    expect(area).not.toHaveClass('border-cyan-300');
  });

  it('calls onFile for dropped images and ignores dropped non-images', () => {
    const onFile = vi.fn();
    const file = imageFile('capture.webp', 'image/webp');
    render(<Dropzone onFile={onFile} disabled={false} />);
    const area = screen.getByTestId('dropzone');

    fireEvent.drop(area, { dataTransfer: { files: [textFile()] } });
    fireEvent.drop(area, { dataTransfer: { files: [file] } });

    expect(onFile).toHaveBeenCalledTimes(1);
    expect(onFile).toHaveBeenCalledWith(file);
  });

  it('does not call onFile for disabled drops', () => {
    const onFile = vi.fn();
    render(<Dropzone onFile={onFile} disabled />);

    fireEvent.drop(screen.getByTestId('dropzone'), { dataTransfer: { files: [imageFile()] } });

    expect(onFile).not.toHaveBeenCalled();
  });

  it('does not apply active drag styling on disabled dragover', () => {
    render(<Dropzone onFile={vi.fn()} disabled />);
    const area = screen.getByTestId('dropzone');

    fireEvent.dragOver(area);

    expect(area).toHaveAttribute('aria-disabled', 'true');
    expect(area).not.toHaveClass('border-cyan-300');
  });
});
