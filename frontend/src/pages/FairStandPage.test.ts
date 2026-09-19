import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { FairStandPage } from "./FairStandPage";

const here = dirname(fileURLToPath(import.meta.url));

describe("FairStandPage standalone host", () => {
  it("renders a full-viewport host without PageShell", () => {
    const html = renderToStaticMarkup(React.createElement(FairStandPage));
    expect(html).toContain('data-testid="fair-stand-standalone"');
    expect(html).toContain('data-testid="fair-stand-host"');
    expect(html).toContain("fair-stand-standalone");
    expect(html).not.toContain("page-shell");
    expect(html).not.toContain("sidebar");
    expect(html).not.toContain("app-topbar");
  });

  it("mounts Fair Stand with existing catalog session headers", () => {
    const source = readFileSync(join(here, "FairStandPage.tsx"), "utf8");
    expect(source).toContain("catalogHeaders: buildApiHeaders()");
    expect(source).toContain('import("@fair-stand/mountFairStand.js")');
    expect(source).not.toContain("PageShell");
  });
});
