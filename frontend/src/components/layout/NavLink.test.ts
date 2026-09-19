import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { NavLink } from "./NavLink";

describe("NavLink new-tab support", () => {
  it("opens an explicit new-tab item with noopener noreferrer", () => {
    const html = renderToStaticMarkup(
      React.createElement(NavLink, {
        variant: "sidebar",
        href: "/fair-stand",
        label: "Fair Stand",
        icon: React.createElement("span", { "data-testid": "icon" }),
        openInNewTab: true,
      }),
    );

    expect(html).toContain('href="/fair-stand"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain("Fair Stand");
  });

  it("keeps in-app sidebar links in the same tab", () => {
    const html = renderToStaticMarkup(
      React.createElement(NavLink, {
        variant: "sidebar",
        href: "/dashboard",
        label: "Dashboard",
        icon: React.createElement("span"),
      }),
    );

    expect(html).toContain('href="/dashboard"');
    expect(html).not.toContain('target="_blank"');
    expect(html).not.toContain("noopener");
  });
});
