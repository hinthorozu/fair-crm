import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ActivationPage, isPublicAuthPath, ResetPasswordPage } from "./PublicAuthPages";
import { authLabels } from "../labels/authLabels";

describe("public auth pages", () => {
  it.each([
    "/signup",
    "/signup/",
    "/activate",
    "/forgot-password",
    "/reset-password/",
  ])("recognizes public auth path %s", (path) => {
    expect(isPublicAuthPath(path)).toBe(true);
  });

  it.each(["/login", "/dashboard", "/settings/security", "/unknown"])(
    "does not classify %s as a public auth route",
    (path) => {
      expect(isPublicAuthPath(path)).toBe(false);
    },
  );

  it("renders a safe missing-token state for activation without echoing token data", () => {
    const html = renderToStaticMarkup(React.createElement(ActivationPage, { token: "" }));
    expect(html).toContain(authLabels.tokenMissing);
    expect(html).toContain("/login");
    expect(html).not.toContain("activation-secret");
  });

  it("renders a safe missing-token state for password reset", () => {
    const html = renderToStaticMarkup(React.createElement(ResetPasswordPage, { token: "" }));
    expect(html).toContain(authLabels.tokenMissing);
    expect(html).toContain("/login");
  });
});
