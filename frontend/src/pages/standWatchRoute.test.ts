import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { parseStandWatchToken } from "./standWatchRoute";

const here = dirname(fileURLToPath(import.meta.url));

describe("public stand watch route", () => {
  it("reads only the temporary token", () => {
    expect(parseStandWatchToken("/stand/watch/abc")).toBe("abc");
    expect(parseStandWatchToken("/stand/watch/abc/")).toBe("abc");
    expect(parseStandWatchToken("/stand/projects/abc")).toBeNull();
    expect(parseStandWatchToken("/login")).toBeNull();
  });

  it("is rendered before the login redirect and without the editor", () => {
    const app = readFileSync(join(here, "../App.tsx"), "utf8");
    const watchReturn = app.indexOf('parsed.route === "/stand/watch/:token"');
    const loginReturn = app.indexOf("if (!isAuthenticated) return <LoginPage");
    expect(watchReturn).toBeGreaterThan(-1);
    expect(watchReturn).toBeLessThan(loginReturn);
    expect(app).toContain("parseStandWatchToken(path)");
    expect(app).toContain("<StandWatchPage");
    const page = readFileSync(join(here, "StandWatchPage.tsx"), "utf8");
    expect(page).toContain("autoPlay");
    expect(page).toContain("playsInline");
    expect(page).toContain("muted");
    expect(page).not.toContain("controls");
    expect(page).not.toContain("mountFairStand");
    expect(page).not.toContain("fairStandProjects");
    expect(page).not.toContain("designState");
    expect(page).not.toContain("AppLayout");
  });
});
