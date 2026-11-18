import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: true,
    port: 5173,
    // Dev: forward API calls to uvicorn on :8000 (override with API_TARGET).
    proxy: { "/api": process.env.API_TARGET ?? "http://localhost:8000" },
  },
  build: { outDir: "dist", assetsDir: "assets", sourcemap: false },
});
