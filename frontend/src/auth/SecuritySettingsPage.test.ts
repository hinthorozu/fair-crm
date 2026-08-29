import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { isSecuritySettingsPath, SecuritySettingsPage } from "../pages/SecuritySettingsPage";
import { authLabels } from "../labels/authLabels";

describe("security settings page", () => {
  it.each(["/settings/security", "/settings/security/"])(
    "recognizes authenticated security route %s",
    (path) => {
      expect(isSecuritySettingsPath(path)).toBe(true);
    },
  );

  it.each(["/login", "/settings", "/settings/profile", "/dashboard"])(
    "does not classify %s as the security settings route",
    (path) => {
      expect(isSecuritySettingsPath(path)).toBe(false);
    },
  );

  it("renders current, new and confirmation password controls without exposing credentials", () => {
    const html = renderToStaticMarkup(
      React.createElement(SecuritySettingsPage, {
        accessToken: "access-token-secret",
        onPasswordChanged: () => undefined,
      }),
    );

    expect(html).toContain('id="security-current-password"');
    expect(html).toContain('id="security-new-password"');
    expect(html).toContain('id="security-confirm-password"');
    expect(html).toContain(authLabels.passwordPolicyHint);
    expect(html).toContain('href="/dashboard"');
    expect(html).not.toContain("access-token-secret");
  });
});
