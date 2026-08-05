import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: "./" is important — Streamlit serves the built index.html from a
// nested path, so absolute "/assets/..." URLs would 404.
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { port: 3001 },
});
