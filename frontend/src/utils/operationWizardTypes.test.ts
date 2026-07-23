import { describe, expect, it } from "vitest";
import { operationTypeInfo, operationTypeLabels } from "../labels/operationLabels";
import type { OperationTypeCatalogItem, OperationTypeMetadata } from "../types/operation";
import {
  canContinueOperationType,
  getOperationTypeWizardPath,
  sortWizardTypes,
  WIZARD_EXCLUDED_TYPES,
} from "./operationWizardTypes";

function meta(
  type: string,
  overrides: Partial<OperationTypeMetadata> = {},
): OperationTypeMetadata {
  return {
    type,
    label_key: type,
    description_key: `${type}_description`,
    supported_sources: ["fair"],
    default_source: "fair",
    capabilities: {
      supports_pause: false,
      supports_resume: false,
      supports_retry: false,
      supports_schedule: false,
      supports_items: true,
    },
    wizard_steps: [],
    type_config_schema: {},
    run_settings_schema: {},
    available_in_wizard: true,
    handler_registered: false,
    ...overrides,
  };
}

function catalog(
  items: Array<[string, string, number]>,
): OperationTypeCatalogItem[] {
  return items.map(([key, name, sort_order]) => ({
    key,
    name,
    is_active: true,
    sort_order,
    supports_pause: false,
    supports_resume: false,
    supports_retry: false,
    supports_schedule: false,
    supports_items: true,
    updated_at: "2026-01-01T00:00:00Z",
  }));
}

describe("operationWizardTypes", () => {
  it("excludes manual_task from the picker list", () => {
    expect(WIZARD_EXCLUDED_TYPES).toContain("manual_task");
    const sorted = sortWizardTypes(
      [meta("manual_task"), meta("scraper"), meta("email")],
      catalog([
        ["scraper", "Web Scraper", 10],
        ["email", "E-posta", 20],
        ["manual_task", "Manuel Görev", 80],
      ]),
    );
    expect(sorted.map((item) => item.type)).toEqual(["scraper", "email"]);
  });

  it("orders by DB sort_order and uses catalog intersection", () => {
    const sorted = sortWizardTypes(
      [
        meta("whatsapp"),
        meta("enrichment"),
        meta("scraper"),
        meta("email"),
        meta("reminder"),
      ],
      catalog([
        ["scraper", "Web Scraper", 10],
        ["email", "E-posta", 20],
        ["enrichment", "Zenginleştirme", 40],
        ["whatsapp", "WhatsApp", 70],
      ]),
    );
    expect(sorted.map((item) => item.type)).toEqual([
      "scraper",
      "email",
      "enrichment",
      "whatsapp",
    ]);
  });

  it("maps only known per-type wizard routes", () => {
    expect(getOperationTypeWizardPath("scraper")).toBe("/operations/new/scraper");
    expect(getOperationTypeWizardPath("bulk_email")).toBe("/operations/new/bulk-email");
    expect(getOperationTypeWizardPath("email")).toBeNull();
  });

  it("enables continue only for types with a wizard route", () => {
    const map = new Map([
      ["scraper", meta("scraper")],
      ["bulk_email", meta("bulk_email")],
      ["email", meta("email")],
    ]);
    expect(canContinueOperationType("", map)).toBe(false);
    expect(canContinueOperationType("scraper", map)).toBe(true);
    expect(canContinueOperationType("bulk_email", map)).toBe(true);
    expect(canContinueOperationType("email", map)).toBe(false);
  });

  it("keeps scraper picker copy aligned with the product example", () => {
    expect(operationTypeLabels.scraper).toBe("Web Scraper");
    expect(operationTypeInfo.scraper.summary).toBe(
      "Web sitelerinden veri toplama otomasyonu.",
    );
    expect(operationTypeInfo.scraper.purpose).toContain("web sitesinden");
    expect(operationTypeInfo.scraper.how).toContain("Fuar seçilir");
  });
});
