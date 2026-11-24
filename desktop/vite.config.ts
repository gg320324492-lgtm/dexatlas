import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Tauri 前端构建配置：dev 端口固定 5173，与 src-tauri/tauri.conf.json 的 devUrl 对齐。
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: "dist",
    target: "es2022",
  },
});
