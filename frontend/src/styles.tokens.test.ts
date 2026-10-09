import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "styles.css"), "utf8");
const html = readFileSync(join(here, "../index.html"), "utf8");

describe("CRM shell tokens", () => {
  it("keeps the ink navy shell, sidebar surface, and Inter", () => {
    expect(css).toContain("--bg: #f5f5f6");
    expect(css).toContain("--surface-sidebar: #f3f3f5");
    expect(css).toContain("--text: #16161a");
    expect(css).toContain("--primary: #1e3a5f");
    expect(css).toContain("--primary-hover: #172c4a");
    expect(css).toContain("--font-sans: Inter,");
    expect(css).toContain("--topbar-height: 48px");
    expect(css).toContain("background: var(--surface-sidebar)");
    expect(html).toContain("family=Inter");
  });
});
