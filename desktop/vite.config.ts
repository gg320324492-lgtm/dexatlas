import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Tauri 前端构建配置：dev 端口固定 5173，与 src-tauri/tauri.conf.json 的 devUrl 对齐。
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    // 工作台后端在 8618；浏览器 dev 下 /api 走 vite 代理，避免跨源被 CORS 拦截。
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8618",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    target: "es2022",
  },
});
