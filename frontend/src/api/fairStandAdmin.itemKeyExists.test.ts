import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./client", () => {
  class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.name = "ApiError";
      this.status = status;
    }
  }
  return {
    ApiError,
    apiRequest: vi.fn(),
  };
});

import { ApiError, apiRequest } from "./client";
import { fairStandAdminItemKeyExists } from "./fairStandAdmin";

describe("fairStandAdminItemKeyExists", () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it("returns true when GET item-record succeeds", async () => {
    vi.mocked(apiRequest).mockResolvedValueOnce({ itemKey: "wall_200_350" });
    await expect(fairStandAdminItemKeyExists("wall_200_350")).resolves.toBe(true);
    expect(apiRequest).toHaveBeenCalledWith("/api/v1/fair-stand/admin/item-records/wall_200_350");
  });

  it("returns false on 404", async () => {
    vi.mocked(apiRequest).mockRejectedValueOnce(new ApiError("not found", 404));
    await expect(fairStandAdminItemKeyExists("missing_key")).resolves.toBe(false);
  });

  it("rethrows non-404 errors", async () => {
    vi.mocked(apiRequest).mockRejectedValueOnce(new ApiError("forbidden", 403));
    await expect(fairStandAdminItemKeyExists("wall_200_350")).rejects.toMatchObject({
      status: 403,
    });
  });
});
