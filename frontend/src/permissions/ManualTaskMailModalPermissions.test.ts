import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  fileURLToPath(new URL("../components/todos/ManualTaskMailModal.tsx", import.meta.url)),
  "utf8",
);

describe("Manual task mail send permission", () => {
  it("uses the canonical mail-send execute permission helper", () => {
    expect(source).toContain("const canSend = canSendMail(grantedPermissions)");
  });

  it("fails closed before the manual mail mutation", () => {
    expect(source).toContain(
      "const handleSendFromPreview = async () => {\n    if (!canSend || !canSendFromPreview || !previewPayload || sending) return;",
    );
  });

  it("does not render the preview send action without permission", () => {
    expect(source).toContain("{canSend ? (\n              <button");
  });
});