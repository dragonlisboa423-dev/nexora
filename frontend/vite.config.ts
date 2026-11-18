import { createHash } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
function publicWorker(): Plugin {
  return {
    name: "saly-private-safe-pwa",
    generateBundle(_, bundle) {
      this.emitFile({
        type: "asset",
        fileName: "pdfjs/LICENSE",
        source: readFileSync(resolve("node_modules/pdfjs-dist/LICENSE")),
      });
      for (const folder of ["cmaps", "standard_fonts", "wasm"]) {
        for (const filename of readdirSync(
          resolve("node_modules/pdfjs-dist", folder),
        )) {
          this.emitFile({
            type: "asset",
            fileName: `pdfjs/${folder}/${filename}`,
            source: readFileSync(
              resolve("node_modules/pdfjs-dist", folder, filename),
            ),
          });
        }
      }
      const files = [
        "/",
        "/offline.html",
        "/manifest.webmanifest",
        "/icons/saly-192.png",
        "/icons/saly-512.png",
        ...Object.keys(bundle)
          .filter((name) => /\.(js|mjs|css)$/.test(name))
          .map((name) => "/" + name),
      ];
      const version = createHash("sha256")
        .update(Object.keys(bundle).join("|"))
        .update(readFileSync(resolve("index.html")))
        .update(readFileSync(resolve("public/manifest.webmanifest")))
        .update(readFileSync(resolve("public/icons/saly-192.png")))
        .update(readFileSync(resolve("public/icons/saly-512.png")))
        .digest("hex")
        .slice(0, 20);
      this.emitFile({
        type: "asset",
        fileName: "sw.js",
        source: `
const CACHE='saly-public-'+${JSON.stringify(version)};
const PUBLIC=${JSON.stringify(files)};
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(PUBLIC))));
self.addEventListener('message',event=>{if(event.data?.type==='SKIP_WAITING')self.skipWaiting();});
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('saly-public-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{const url=new URL(event.request.url);if(event.request.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/api')||url.pathname.startsWith('/docs')||url.pathname==='/openapi.json')return;
if(event.request.mode==='navigate'){event.respondWith(fetch(event.request).catch(async()=>await caches.match('/')||await caches.match('/offline.html')));return;}
if(!PUBLIC.includes(url.pathname))return;
event.respondWith(caches.match(url.pathname).then(hit=>hit||fetch(event.request)));});
`,
      });
    },
  };
}
export default defineConfig({
  plugins: [react(), publicWorker()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id: string) =>
          id.includes("three") ? "three" : undefined,
      },
    },
  },
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
