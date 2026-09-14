import { defineConfig } from "vite";

export default defineConfig({
  build: {
    lib: {
      entry: "src/main.ts",
      name: "Perch",
      formats: ["iife"],
      fileName: () => "perch.js",
    },
    outDir: "dist",
    emptyOutDir: true,
  },
});
