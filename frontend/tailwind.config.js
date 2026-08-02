/**
 * Purpose: Configure Tailwind content scanning.
 * Callers: PostCSS/Tailwind build pipeline.
 * Deps: tailwindcss config loader.
 * API: default Tailwind config object.
 * Side effects: none until tooling loads it.
 * @type {import('tailwindcss').Config}
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
};
