/**
 * Purpose: Configure Vite for the ScreenSort React frontend.
 * Callers: Vite CLI, Vitest CLI.
 * Deps: @vitejs/plugin-react, vitest/config.
 * API: default Vite/Vitest configuration object.
 * Side effects: Starts dev/build/test tooling only when invoked.
 */
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    passWithNoTests: true,
    setupFiles: './src/test/setup.ts',
  },
});
