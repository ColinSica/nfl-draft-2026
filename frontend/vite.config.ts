import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// Builds into the FastAPI app's static dir so a single `python -m src.api.app`
// serves both the API and the frontend.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: path.resolve(__dirname, '..', 'src', 'api', 'static'),
    emptyOutDir: true,
  },
});
