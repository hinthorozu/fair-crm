import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  appType: "spa",
  server: {
    port: 5173,
    host: "127.0.0.1",
    proxy: {
      "/kyrox-core": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/kyrox-core/, ""),
      },
    },
  },
  preview: {
    port: 5173,
    host: "127.0.0.1",
  },
});
