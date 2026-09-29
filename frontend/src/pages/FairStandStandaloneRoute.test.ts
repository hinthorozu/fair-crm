import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const frontendSrc = join(here, "..");

function read(relativePath: string): string {
  return readFileSync(join(frontendSrc, relativePath), "utf8");
}

describe("Stand projects CRM routes", () => {
  it("routes list inside AppLayout and editor outside AppLayout", () => {
    const app = read("App.tsx");
    expect(app).toContain('"/stand-projects"');
    expect(app).toContain('"/stand-projects/new"');
    expect(app).toContain('"/stand-projects/:id"');
    expect(app).toContain("<StandProjectsPage");
    expect(app).toContain("<FairStandPage");
    expect(app).toContain('navigate("/stand-projects")');
    expect(app.indexOf('parsed.route === "/stand-projects/new"')).toBeLessThan(
      app.indexOf("<AppLayout breadcrumbs={breadcrumbs} navItems={navItems}"),
    );
    expect(app).toContain('path: "/stand-projects"');
    expect(app).toContain("openInNewTab: true");
    expect(app).toContain('pathname === "/fair-stand"');
    expect(app).toContain("standCustomerId");
    expect(app).toContain("onCreateStandProject={goToStandProjectNew}");
    expect(app).toContain("onOpenProject={goToStandProjectEdit}");
    expect(app).toContain("customerId=${encodeURIComponent(customerId)}");
    expect(app).toContain("navigate(path); setParsed(parseRoute(path)); setSidebarOpen(false);");
    expect(app).toContain('window.open(path, "_blank", "noopener,noreferrer")');
    expect(app).toContain("openStandProjectPath(path)");
    const newProject = app.slice(app.indexOf("const goToStandProjectNew"), app.indexOf("const goToStandProjectEdit"));
    expect(newProject).toContain("openStandProjectPath(path)");
    expect(newProject).not.toContain("navigate(path)");
    const editProject = app.slice(app.indexOf("const goToStandProjectEdit"), app.indexOf("const handleLoginSuccess"));
    expect(editProject).toContain("openStandProjectPath(path)");
    expect(editProject).not.toContain("navigate(path)");
    const detail = read("pages/CustomerDetailPage.tsx");
    expect(detail).toContain('id: "projects"');
    expect(detail).toContain("listFairStandProjects(customerId)");
    expect(detail).toContain("PERMISSION_STAND_PROJECTS_READ");
    expect(detail).toContain("PERMISSION_STAND_PROJECTS_CREATE");
    expect(detail).toContain("onCreateStandProject(customerId)");
  });

  it("uses a full-viewport standalone host with chrome back bar", () => {
    const css = read("styles.css");
    expect(css).toContain(".fair-stand-standalone");
    expect(css).toContain("height: 100dvh");
    expect(css).toContain(".fair-stand-chrome");
    expect(css).not.toContain("height: calc(100vh - var(--topbar-height))");
  });

  it("keeps normal CRM routes on AppLayout", () => {
    const app = read("App.tsx");
    expect(app).toContain('{parsed.route === "/dashboard" && <DashboardPage');
    expect(app).toContain('{parsed.route === "/customers" && <CustomersPage');
    expect(app).toContain('{parsed.route === "/stand-projects" && (');
  });
});
