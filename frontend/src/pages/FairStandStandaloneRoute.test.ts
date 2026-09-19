import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const frontendSrc = join(here, "..");

function read(relativePath: string): string {
  return readFileSync(join(frontendSrc, relativePath), "utf8");
}

describe("Fair Stand standalone CRM route", () => {
  it("keeps /fair-stand authenticated and outside AppLayout", () => {
    const app = read("App.tsx");
    expect(app).toContain('if (pathname === "/fair-stand" || pathname === "/fair-stand/") return { route: "/fair-stand" }');
    expect(app).toContain("if (!isAuthenticated) return <LoginPage onSuccess={handleLoginSuccess} />");
    expect(app).toMatch(/if \(parsed\.route === "\/fair-stand"\) \{\s*return \(/);
    expect(app).toContain("<FairStandPage />");
    expect(app).not.toContain("{parsed.route === \"/fair-stand\" && <FairStandPage />}");
    expect(app).toContain("<AppLayout breadcrumbs={breadcrumbs} navItems={navItems}");
    expect(app.indexOf("if (parsed.route === \"/fair-stand\")")).toBeLessThan(app.indexOf("<AppLayout breadcrumbs={breadcrumbs} navItems={navItems}"));
  });

  it("opens the sidebar Fair Stand item in a new tab via shared NavLink", () => {
    const app = read("App.tsx");
    const layout = read("components/layout/AppLayout.tsx");
    const navLink = read("components/layout/NavLink.tsx");
    expect(app).toContain('path: "/fair-stand"');
    expect(app).toContain("openInNewTab: true");
    expect(app).not.toContain('handleNav("/fair-stand"');
    expect(layout).toContain("openInNewTab={item.openInNewTab}");
    expect(navLink).toContain('target={openInNewTab ? "_blank" : undefined}');
    expect(navLink).toContain('rel={openInNewTab ? "noopener noreferrer" : undefined}');
  });

  it("uses a full-viewport standalone host without CRM chrome CSS", () => {
    const css = read("styles.css");
    expect(css).toContain(".fair-stand-standalone");
    expect(css).toContain("height: 100dvh");
    expect(css).not.toContain("height: calc(100vh - var(--topbar-height))");
    expect(css).not.toContain(".app-content:has(.fair-stand-page)");
  });

  it("keeps normal CRM routes on AppLayout", () => {
    const app = read("App.tsx");
    expect(app).toContain('{parsed.route === "/dashboard" && <DashboardPage');
    expect(app).toContain('{parsed.route === "/customers" && <CustomersPage');
  });
});
