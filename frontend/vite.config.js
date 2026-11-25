import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const local = loadEnv(mode, process.cwd(), "");
  const backend = loadEnv(
    mode,
    fileURLToPath(new URL("../backend", import.meta.url)),
    "DJANGO_",
  );
  // Only VITE_ variables enter browser code. This token stays in the Node process.
  const token =
    process.env.DJANGO_API_TOKEN ||
    local.DJANGO_API_TOKEN ||
    backend.DJANGO_API_TOKEN;
  const proxy = {
    "/api/v1": {
      target:
        process.env.BACKEND_URL || local.BACKEND_URL || "http://127.0.0.1:8000",
      changeOrigin: true,
      timeout: 240_000,
      proxyTimeout: 240_000,
      configure(server) {
        server.on("proxyReq", (request) => {
          request.removeHeader("authorization");
          if (token) request.setHeader("Authorization", `Bearer ${token}`);
        });
      },
    },
  };
  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      cors: false,
      proxy,
    },
    preview: {
      host: "127.0.0.1",
      port: 4173,
      strictPort: true,
      cors: false,
      proxy,
    },
  };
});
