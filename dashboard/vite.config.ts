import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/onboarding": {
        target: "http://api:8000",
        changeOrigin: true,
      },
      "/sources": {
        target: "http://api:8000",
        changeOrigin: true,
      },
      "/status": {
        target: "http://api:8000",
        changeOrigin: true,
      },
      "/runs": {
        target: "http://api:8000",
        changeOrigin: true,
      },
      "/files": {
        target: "http://api:8000",
        changeOrigin: true,
      },
      "/metrics": {
        target: "http://api:8000",
        changeOrigin: true,
      },
      "/jobs": {
        target: "http://api:8000",
        changeOrigin: true,
      },
      "/ontology": {
        target: "http://api:8000",
        changeOrigin: true,
      },
      "/chat": {
        target: "http://api:8000",
        changeOrigin: true,
      },
    },
  },
});
