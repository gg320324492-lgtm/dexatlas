import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The production build is what the FastAPI app serves from web/dist. In dev
// mode `npm run dev` proxies the API paths to the Python server, so the
// front end never needs to know which process answered it.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8618",
    },
  },
});
