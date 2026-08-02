/**
 * Purpose: Configure CSS transforms for Vite.
 * Callers: PostCSS/Vite CSS pipeline.
 * Deps: @tailwindcss/postcss, autoprefixer.
 * API: default PostCSS config object.
 * Side effects: none until tooling loads it.
 */
export default {
  plugins: {
    '@tailwindcss/postcss': {},
    autoprefixer: {},
  },
};
