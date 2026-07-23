import { describe, expect, it } from "vitest";
import type { OperationRun } from "../types/operation";
import {
  extractScraperResult,
  resolveOperationLiveLogTarget,
} from "./operationScraperRun";

function makeRun(overrides: Partial<OperationRun> = {}): OperationRun {
  return {
    id: "op-run-1",
    organization_id: "org-1",
    operation_id: "op-1",
    attempt: 1,
    status: "running",
    progress: 0.1,
    total_items: 10,
    processed_items: 1,
    succeeded_items: 1,
    failed_items: 0,
    started_at: "2026-07-23T10:00:00.000Z",
    finished_at: null,
    error_code: null,
    error_message: null,
    error_details: {},
    core_job_id: null,
    triggered_by: null,
    created_at: "2026-07-23T10:00:00.000Z",
    updated_at: "2026-07-23T10:00:00.000Z",
    ...overrides,
  };
}

describe("extractScraperResult", () => {
  it("returns null when run has empty error_details", () => {
    expect(extractScraperResult(makeRun())).toBeNull();
  });

  it("returns null when result payload is missing", () => {
    expect(
      extractScraperResult(makeRun({ error_details: { message: "failed" } })),
    ).toBeNull();
  });

  it("reads linked scraper_run_id and related fields from result", () => {
    expect(
      extractScraperResult(
        makeRun({
          error_details: {
            result: {
              scraper_run_id: "scraper-run-abc",
              adapter_key: "expocloud",
              import_batch_id: "batch-1",
              total_rows: 42,
              input_url: "https://example.test",
            },
          },
        }),
      ),
    ).toEqual({
      scraper_run_id: "scraper-run-abc",
      adapter_key: "expocloud",
      import_batch_id: "batch-1",
      total_rows: 42,
      input_url: "https://example.test",
    });
  });

  it("ignores non-string scraper_run_id", () => {
    expect(
      extractScraperResult(
        makeRun({
          error_details: {
            result: { scraper_run_id: 123 },
          },
        }),
      ),
    ).toEqual({
      scraper_run_id: null,
      adapter_key: null,
      import_batch_id: null,
      total_rows: null,
      input_url: null,
    });
  });
});

describe("resolveOperationLiveLogTarget", () => {
  it("returns null when no linked scraper run id", () => {
    expect(resolveOperationLiveLogTarget(makeRun(), "expocloud")).toBeNull();
  });

  it("returns null when scraper_run_id is empty string", () => {
    expect(
      resolveOperationLiveLogTarget(
        makeRun({
          error_details: { result: { scraper_run_id: "  ", adapter_key: "expocloud" } },
        }),
        "expocloud",
      ),
    ).toBeNull();
  });

  it("uses linked scraper_run_id (not a guessed latest run)", () => {
    const target = resolveOperationLiveLogTarget(
      makeRun({
        error_details: {
          result: {
            scraper_run_id: "linked-run-id",
            adapter_key: "adapter-from-result",
          },
        },
      }),
      "adapter-from-config",
    );
    expect(target).toEqual({
      scraperRunId: "linked-run-id",
      adapterKey: "adapter-from-result",
    });
  });

  it("falls back to type_config adapter_key when result omits it", () => {
    const target = resolveOperationLiveLogTarget(
      makeRun({
        error_details: {
          result: { scraper_run_id: "linked-run-id" },
        },
      }),
      "adapter-from-config",
    );
    expect(target).toEqual({
      scraperRunId: "linked-run-id",
      adapterKey: "adapter-from-config",
    });
  });

  it("returns null when adapter key cannot be resolved", () => {
    expect(
      resolveOperationLiveLogTarget(
        makeRun({
          error_details: {
            result: { scraper_run_id: "linked-run-id" },
          },
        }),
        null,
      ),
    ).toBeNull();
  });
});
