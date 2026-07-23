import { describe, expect, it } from "vitest";
import { runStatusBadgeVariant, runStatusLabel } from "./scraperBadges";
import {
  mapTechnicalRunStatusToUserFacing,
  operationUserFacingStatusLabel,
  resolveOperationUserFacingStatus,
} from "./operationRunStatus";
import type { Operation, OperationRun } from "../types/operation";

function makeRun(status: string): OperationRun {
  return {
    id: "run-1",
    organization_id: "org-1",
    operation_id: "op-1",
    status,
    progress: 0,
    total_items: 0,
    processed_items: 0,
    succeeded_items: 0,
    failed_items: 0,
    attempt: 1,
    started_at: null,
    finished_at: null,
    error_code: null,
    error_message: null,
    error_details: {},
    core_job_id: null,
    triggered_by: null,
    created_at: "2026-07-23T10:00:00.000Z",
    updated_at: "2026-07-23T10:00:00.000Z",
  };
}

describe("Web Scraper uses shared Operation status mapping", () => {
  it("maps scraper OperationRun statuses to shared Turkish labels", () => {
    expect(operationUserFacingStatusLabel(mapTechnicalRunStatusToUserFacing("running"))).toBe(
      "Çalışıyor",
    );
    expect(operationUserFacingStatusLabel(mapTechnicalRunStatusToUserFacing("completed"))).toBe(
      "Bitti",
    );
    expect(operationUserFacingStatusLabel(mapTechnicalRunStatusToUserFacing("failed"))).toBe(
      "Hata",
    );
    expect(operationUserFacingStatusLabel(mapTechnicalRunStatusToUserFacing("cancelled"))).toBe(
      "İptal",
    );
  });

  it("does not treat scraper queued as Zamanlandı", () => {
    expect(mapTechnicalRunStatusToUserFacing("queued")).toBe("running");
  });

  it("resolves scraper operation status from latest_run, not lifecycle Aktif", () => {
    const operation = {
      status: "active",
      latest_run: makeRun("completed"),
      run_settings: {},
    } as Pick<Operation, "latest_run" | "run_settings"> & { status: string };
    expect(resolveOperationUserFacingStatus(operation)).toBe("completed");
    expect(operation.status).toBe("active");
  });

  it("Live Log / scraperBadges reuse the same shared labels", () => {
    expect(runStatusLabel("running")).toBe("Çalışıyor");
    expect(runStatusLabel("completed")).toBe("Bitti");
    expect(runStatusLabel("failed")).toBe("Hata");
    expect(runStatusLabel("cancelled")).toBe("İptal");
    expect(runStatusLabel("queued")).toBe("Çalışıyor");
    // Scraper transitional cancel states align with OperationRun → running
    expect(runStatusLabel("cancel_requested")).toBe("Çalışıyor");
    expect(runStatusLabel("cancelling")).toBe("Çalışıyor");
  });

  it("uses shared badge semantics", () => {
    expect(runStatusBadgeVariant("running")).toBe("info");
    expect(runStatusBadgeVariant("completed")).toBe("success");
    expect(runStatusBadgeVariant("failed")).toBe("danger");
    expect(runStatusBadgeVariant("cancelled")).toBe("neutral");
  });
});
