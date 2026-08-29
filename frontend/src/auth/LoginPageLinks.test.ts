import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { LoginSecondaryActions } from "../pages/LoginPage";
import { authLabels } from "../labels/authLabels";

describe("login public auth integration", () => {
  it("links password recovery and account creation from login", () => {
    const html = renderToStaticMarkup(React.createElement(LoginSecondaryActions));

    expect(html).toContain('href="/forgot-password"');
    expect(html).toContain(authLabels.forgotPasswordLink);
    expect(html).toContain('href="/signup"');
    expect(html).toContain(authLabels.signupLink);
  });
});
