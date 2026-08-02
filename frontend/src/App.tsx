/**
 * Purpose: Provide route-aware ScreenSort application shell.
 * Callers: src/main.tsx.
 * Deps: React state/effect hooks, route pages, Tailwind utility classes.
 * API: Default App component.
 * Side effects: Syncs top-level routes with browser history.
 */
import { MouseEvent, useEffect, useState } from 'react';

import LibraryPage from './pages/LibraryPage';
import UploadPage from './pages/UploadPage';

type Page = 'upload' | 'library';

const pagePaths: Record<Page, string> = {
  upload: '/upload',
  library: '/library',
};

const pages: Record<Page, { label: string; title: string; body: string }> = {
  upload: {
    label: 'Upload',
    title: 'Upload screenshots',
    body: 'Choose screenshots to sort and classify.',
  },
  library: {
    label: 'Library',
    title: 'Screenshot library',
    body: 'Browse processed screenshots and categories.',
  },
};

function getCurrentPage(): Page {
  return window.location.pathname === '/library' ? 'library' : 'upload';
}

export default function App() {
  const [page, setPage] = useState<Page>(getCurrentPage());

  useEffect(() => {
    const syncPage = () => setPage(getCurrentPage());
    window.addEventListener('popstate', syncPage);
    return () => window.removeEventListener('popstate', syncPage);
  }, []);

  const navigate = (event: MouseEvent<HTMLAnchorElement>, nextPage: Page) => {
    event.preventDefault();
    if (page !== nextPage) {
      window.history.pushState(null, '', pagePaths[nextPage]);
      setPage(nextPage);
    }
  };

  return (
    <main className="min-h-screen text-slate-100">
      <nav className="sticky top-0 z-10 border-b border-white/10 bg-slate-950/80 px-4 py-4 backdrop-blur-xl sm:px-6">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">ScreenSort</h1>
            <p className="hidden text-xs text-slate-400 sm:block">ML screenshot organizer</p>
          </div>
          <div className="flex rounded-full border border-white/10 bg-white/5 p-1" aria-label="Primary navigation">
            {(Object.keys(pages) as Page[]).map((key) => (
              <a
                aria-current={page === key ? 'page' : undefined}
                className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                  page === key
                    ? 'bg-cyan-300 text-slate-950 shadow-lg shadow-cyan-950/30'
                    : 'text-slate-300 hover:bg-white/10 hover:text-white'
                }`}
                href={pagePaths[key]}
                key={key}
                onClick={(event) => navigate(event, key)}
              >
                {pages[key].label}
              </a>
            ))}
          </div>
        </div>
      </nav>
      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {page === 'upload' ? <UploadPage /> : <LibraryPage />}
      </section>
    </main>
  );
}
