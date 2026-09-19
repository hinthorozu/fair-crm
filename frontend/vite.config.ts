import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, type PreviewServer, type ViteDevServer } from "vite";
import react from "@vitejs/plugin-react";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const fairStandRoot = path.resolve(frontendRoot, "../../fair-stand");
const fairStandSrc = path.resolve(fairStandRoot, "src");
const fairStandPublic = path.resolve(fairStandRoot, "public");
const fairStandFallbackSrc = path.resolve(frontendRoot, "src/fairStand");
const fairStandAlias = fs.existsSync(path.join(fairStandSrc, "mountFairStand.js"))
  ? fairStandSrc
  : fairStandFallbackSrc;
const fairStandFsAllow = fs.existsSync(fairStandRoot)
  ? [frontendRoot, fairStandRoot]
  : [frontendRoot];

function mimeFor(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".png") return "image/png";
  if (ext === ".webp") return "image/webp";
  if (ext === ".glb") return "model/gltf-binary";
  if (ext === ".gltf") return "model/gltf+json";
  if (ext === ".txt") return "text/plain; charset=utf-8";
  return "application/octet-stream";
}

function resolveFairStandPublicFile(urlPath: string): string | null {
  const rel = decodeURIComponent((urlPath.split("?")[0] || "").replace(/^\/+/, ""));
  if (!rel || rel.includes("..")) return null;
  const filePath = path.resolve(fairStandPublic, rel);
  const root = fairStandPublic.endsWith(path.sep) ? fairStandPublic : `${fairStandPublic}${path.sep}`;
  if (filePath !== fairStandPublic && !filePath.startsWith(root)) return null;
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) return null;
  return filePath;
}

function attachFairStandPublic(server: ViteDevServer | PreviewServer): void {
  server.middlewares.use((req, res, next) => {
    const filePath = resolveFairStandPublicFile(req.url || "");
    if (!filePath) {
      next();
      return;
    }
    res.statusCode = 200;
    res.setHeader("Content-Type", mimeFor(filePath));
    fs.createReadStream(filePath).pipe(res);
  });
}

function fairStandPublicAssets() {
  return {
    name: "fair-stand-public-assets",
    configureServer(server: ViteDevServer) {
      attachFairStandPublic(server);
    },
    configurePreviewServer(server: PreviewServer) {
      attachFairStandPublic(server);
    },
    writeBundle(options: { dir?: string }) {
      const outDir = options.dir;
      if (!outDir || !fs.existsSync(fairStandPublic)) return;
      fs.cpSync(fairStandPublic, outDir, { recursive: true });
    },
  };
}

export default defineConfig({
  plugins: [react(), fairStandPublicAssets()],
  appType: "spa",
  resolve: {
    alias: {
      "@fair-stand": fairStandAlias,
    },
  },
  server: {
    port: 5173,
    host: true,
    fs: {
      allow: fairStandFsAllow,
    },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
      "/data/quote-template-logos": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
      "/kyrox-core": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (pathName) => pathName.replace(/^\/kyrox-core/, ""),
      },
    },
  },
  preview: {
    port: 5173,
    host: true,
  },
});
