import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  new URL("../components/mail_operations/MailOperationActionsMenu.tsx", import.meta.url),
  "utf8",
);

describe("MailOperationActionsMenu cancel permissions", () => {
  it("does not expose retry or cancel without execute permission", () => {
    expect(source).toContain(
      'if ((action === "retry" || action === "cancel") && !canExecute) return false;',
    );
  });

  it("fails closed before invoking retry or cancel callbacks", () => {
    expect(source).toContain(
      'if ((action === "retry" || action === "cancel") && !canExecute) return;',
    );
    expect(source).toContain('if (action === "retry" && retryDisabled) return;');
  });
});
