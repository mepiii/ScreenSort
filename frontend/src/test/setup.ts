/**
 * Purpose: Configure shared Vitest DOM assertions.
 * Callers: Vitest setupFiles from vite.config.ts.
 * Deps: @testing-library/jest-dom/vitest.
 * API: Test environment setup module.
 * Side effects: Registers jest-dom matchers.
 */
import '@testing-library/jest-dom/vitest';
