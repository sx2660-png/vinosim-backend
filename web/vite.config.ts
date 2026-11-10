import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const LOCAL_API = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": LOCAL_API,
      "/articles": LOCAL_API,
      "/quiz": LOCAL_API,
      "/agent": LOCAL_API,
      "/scan": LOCAL_API,
      "/label": LOCAL_API,
      "/webhook": LOCAL_API,
    },
  },
});
