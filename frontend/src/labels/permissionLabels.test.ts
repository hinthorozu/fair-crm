import { describe, expect, it } from "vitest";

import { FAIR_CRM_PERMISSION_CODES } from "../permissions/corePermissions";
import { formatPermissionDescription, getPermissionDisplayCopy } from "./permissionLabels";

describe("permissionLabels", () => {
  it("has Turkish display copy for every Fair CRM permission exposed by the frontend", () => {
    for (const code of FAIR_CRM_PERMISSION_CODES) {
      expect(getPermissionDisplayCopy(code), code).toBeDefined();
    }
  });

  it("localizes known Core platform permissions", () => {
    expect(getPermissionDisplayCopy("settings.platform.read")?.title).toBe("Organizasyon ayarlarını görüntüleme");
    expect(getPermissionDisplayCopy("jobs.platform.enqueue")?.title).toBe("Arka plan işi başlatma");
    expect(getPermissionDisplayCopy("notifications.platform.send")?.title).toBe("Bildirim gönderme");
    expect(getPermissionDisplayCopy("audit.logs.read")?.title).toBe("Denetim kayıtlarını görüntüleme");
  });

  it("does not invent a Turkish label for an unknown permission", () => {
    expect(getPermissionDisplayCopy("unknown.module.magic")).toBeUndefined();
    expect(formatPermissionDescription("unknown.module.magic", "Original description"))
      .toBe("Original description");
  });
});
