/**
 * Purpose: Verify screenshot upload page behavior.
 * Callers: Vitest runner.
 * Deps: React Testing Library, Vitest, API client mock, UploadPage.
 * API: UploadPage interaction tests.
 * Side effects: Mocks upload API calls.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import UploadPage from './UploadPage';
import { uploadScreenshot } from '../api/client';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client');
  return {
    ...actual,
    imageUrl: (id: number) => `http://test.local/screenshots/${id}/image`,
    uploadScreenshot: vi.fn(),
  };
});

const record = {
  id: 7,
  original_filename: 'screen.png',
  stored_filename: 'stored.png',
  path: '/uploads/stored.png',
  category: 'Dashboard',
  confidence: 0.876,
  tags: ['metrics', 'charts'],
  created_at: '2026-04-27T00:00:00Z',
};

const file = new File(['image'], 'screen.png', { type: 'image/png' });

describe('UploadPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('shows selected filename and uploads screenshot results', async () => {
    vi.mocked(uploadScreenshot).mockResolvedValue(record);
    render(<UploadPage />);

    expect(screen.getByRole('button', { name: /classify screenshot/i })).toBeDisabled();
    await userEvent.upload(screen.getByLabelText(/choose screenshot/i), file);

    expect(screen.getByText('screen.png')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /classify screenshot/i }));

    await waitFor(() => expect(uploadScreenshot).toHaveBeenCalledWith(file));
    expect(await screen.findByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('88% confidence')).toBeInTheDocument();
    expect(screen.getByText('metrics')).toBeInTheDocument();
    expect(screen.getByAltText('screen.png')).toHaveAttribute('src', 'http://test.local/screenshots/7/image');
  });

  it('shows upload errors inline and clears uploading state', async () => {
    vi.mocked(uploadScreenshot).mockRejectedValue(new Error('Upload failed'));
    render(<UploadPage />);

    await userEvent.upload(screen.getByLabelText(/choose screenshot/i), file);
    await userEvent.click(screen.getByRole('button', { name: /classify screenshot/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Upload failed');
    expect(screen.getByRole('button', { name: /classify screenshot/i })).toBeEnabled();
  });

  it('clears stale result and error when selecting a new file', async () => {
    const nextFile = new File(['next'], 'next.png', { type: 'image/png' });
    vi.mocked(uploadScreenshot).mockResolvedValue(record);
    render(<UploadPage />);

    await userEvent.upload(screen.getByLabelText(/choose screenshot/i), file);
    await userEvent.click(screen.getByRole('button', { name: /classify screenshot/i }));
    expect(await screen.findByText('Dashboard')).toBeInTheDocument();

    vi.mocked(uploadScreenshot).mockRejectedValue(new Error('Upload failed'));
    await userEvent.upload(screen.getByLabelText(/choose screenshot/i), nextFile);
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /classify screenshot/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Upload failed');

    await userEvent.upload(screen.getByLabelText(/choose screenshot/i), file);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
