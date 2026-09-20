import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(here, "../..");
const repoRoot = join(frontendRoot, "..");

describe("Fair Stand catalog same-origin proxy", () => {
  it("points Vite /api/v1/fair-stand to the Stand process", () => {
    const source = readFileSync(join(frontendRoot, "vite.config.ts"), "utf8");
    expect(source).toContain('"/api/v1/fair-stand"');
    expect(source).toContain('target: "http://127.0.0.1:8002"');
  });

  it("routes nginx /api/v1/fair-stand/ to :8002 ahead of CRM /api", () => {
    const source = readFileSync(join(repoRoot, "scripts/server/nginx/fair-crm.conf"), "utf8");
    const standIndex = source.indexOf("location ^~ /api/v1/fair-stand/");
    const crmApiIndex = source.indexOf("location /api/");
    expect(standIndex).toBeGreaterThan(-1);
    expect(crmApiIndex).toBeGreaterThan(standIndex);
    expect(source).toContain("proxy_pass http://127.0.0.1:8002;");
  });
});
