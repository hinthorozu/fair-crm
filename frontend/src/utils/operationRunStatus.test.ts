import { describe, expect, it } from "vitest";
import {
  mapTechnicalRunStatusToUserFacing,
  operationUserFacingStatusLabel,
  resolveOperationUserFacingStatus,
  resolveRunUserFacingStatus,
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

describe("mapTechnicalRunStatusToUserFacing", () => {
  it("maps core technical statuses to the six user-facing keys", () => {
    expect(mapTechnicalRunStatusToUserFacing("running")).toBe("running");
    expect(mapTechnicalRunStatusToUserFacing("paused")).toBe("paused");
    expect(mapTechnicalRunStatusToUserFacing("completed")).toBe("completed");
    expect(mapTechnicalRunStatusToUserFacing("cancelled")).toBe("cancelled");
    expect(mapTechnicalRunStatusToUserFacing("failed")).toBe("failed");
    expect(mapTechnicalRunStatusToUserFacing("scheduled")).toBe("scheduled");
  });

  it("maps immediate queued to Çalışıyor (not Zamanlandı)", () => {
    expect(mapTechnicalRunStatusToUserFacing("queued")).toBe("running");
    expect(operationUserFacingStatusLabel("running")).toBe("Çalışıyor");
  });

  it("maps queued with future schedule to Zamanlandı", () => {
    const future = new Date(Date.now() + 60 * 60 * 1000).toISOString();
    expect(
      mapTechnicalRunStatusToUserFacing("queued", {
        runSettings: { scheduled_at: future },
      }),
    ).toBe("scheduled");
    expect(operationUserFacingStatusLabel("scheduled")).toBe("Zamanlandı");
  });

  it("does not treat past schedule as Zamanlandı for queued", () => {
    const past = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    expect(
      mapTechnicalRunStatusToUserFacing("queued", {
        runSettings: { scheduled_at: past },
      }),
    ).toBe("running");
  });

  it("exposes the required Turkish labels", () => {
    expect(operationUserFacingStatusLabel("paused")).toBe("Durduruldu");
    expect(operationUserFacingStatusLabel("completed")).toBe("Bitti");
    expect(operationUserFacingStatusLabel("cancelled")).toBe("İptal");
    expect(operationUserFacingStatusLabel("failed")).toBe("Hata");
  });
});

describe("resolveOperationUserFacingStatus", () => {
  it("uses latest_run, not operation lifecycle status", () => {
    const operation = {
      latest_run: makeRun("failed"),
      run_settings: {},
      status: "active",
    } as Pick<Operation, "latest_run" | "run_settings"> & { status: string };
    expect(resolveOperationUserFacingStatus(operation)).toBe("failed");
    expect(operationUserFacingStatusLabel(resolveOperationUserFacingStatus(operation))).toBe(
      "Hata",
    );
  });

  it("returns null when there is no latest run", () => {
    expect(
      resolveOperationUserFacingStatus({ latest_run: null, run_settings: {} }),
    ).toBeNull();
  });
});

describe("resolveRunUserFacingStatus", () => {
  it("maps completed → Bitti and cancelled → İptal", () => {
    expect(resolveRunUserFacingStatus(makeRun("completed"))).toBe("completed");
    expect(resolveRunUserFacingStatus(makeRun("cancelled"))).toBe("cancelled");
  });
});
