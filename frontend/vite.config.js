import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// The Svelte dev server proxies /api to the FastAPI backend on :8000,
// so the app can call same-origin /api/* (no CORS needed).
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
