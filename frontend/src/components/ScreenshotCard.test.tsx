/**
 * Purpose: Verify screenshot card metadata, image, and OCR preview rendering.
 * Callers: Vitest runner.
 * Deps: React Testing Library, Vitest, ScreenshotCard.
 * API: ScreenshotCard display tests.
 * Side effects: None.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import ScreenshotCard from './ScreenshotCard';
import { ScreenshotRecord } from '../api/client';

const record = (overrides: Partial<ScreenshotRecord> = {}): ScreenshotRecord => ({
  id: 7,
  original_filename: 'dashboard.png',
  stored_filename: 'stored-dashboard.png',
  path: '/uploads/stored-dashboard.png',
  category: 'Dashboard',
  confidence: 0.876,
  tags: ['metrics', 'charts'],
  created_at: '2026-04-27T00:00:00Z',
  ...overrides,
});

describe('ScreenshotCard', () => {
  it('renders OCR preview when OCR text exists', () => {
    render(<ScreenshotCard screenshot={record({ ocr_text: 'Revenue by region dashboard heading' })} />);

    expect(screen.getByText('OCR text')).toBeInTheDocument();
    expect(screen.getByText('Revenue by region dashboard heading')).toBeInTheDocument();
  });

  it('truncates long OCR text predictably with ellipsis', () => {
    const longText = 'A'.repeat(161);
    render(<ScreenshotCard screenshot={record({ ocr_text: longText })} />);

    expect(screen.getByText(`${'A'.repeat(160)}…`)).toHaveClass('break-words');
    expect(screen.queryByText(longText)).not.toBeInTheDocument();
  });

  it('truncates OCR text without splitting Unicode grapheme clusters', () => {
    render(<ScreenshotCard screenshot={record({ ocr_text: `${'A'.repeat(159)}👍🏽tail` })} />);

    expect(screen.getByText(`${'A'.repeat(159)}👍🏽…`)).toBeInTheDocument();
  });

  it('does not render OCR preview when OCR text is empty', () => {
    render(<ScreenshotCard screenshot={record({ ocr_text: '' })} />);

    expect(screen.queryByText('OCR text')).not.toBeInTheDocument();
  });
});
