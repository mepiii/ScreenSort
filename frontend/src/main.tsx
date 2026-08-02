/**
 * Purpose: Mount the ScreenSort React application.
 * Callers: Vite HTML entrypoint.
 * Deps: React, React DOM, App, global CSS.
 * API: Browser entry module.
 * Side effects: Renders into #root.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
