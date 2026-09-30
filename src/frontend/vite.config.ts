import { defineConfig } from "vite";

// No plugins: Vite compiles TSX with the automatic JSX runtime from tsconfig.
export default defineConfig({
  server: { proxy: { "/api": "http://localhost:8000" } },
  build: { sourcemap: false },
});
