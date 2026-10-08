/**
 * @vitest-environment jsdom
 */
import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import { FairTable } from "../components/FairList";
import { fairLabels, fairStatusLabels } from "../labels/fairLabels";
import { importLabels } from "../labels/importLabels";
import { participationLabels } from "../labels/participationLabels";
import { labels } from "../labels";
import { systemFairScrapeReady, type Fair } from "../types/fair";
import type { StandardListResponse } from "../types/listTable";
import { FairDetailPage } from "./FairDetailPage";
import { FairsPage, tobbSyncSummary } from "./FairsPage";

const harness = vi.hoisted(() => ({
  isSuperAdmin: false,
  allowPermissions: true,
  listFairs: vi.fn(),
  getFair: vi.fn(),
  compare: vi.fn(),
  runScraper: vi.fn(),
  syncTobb: vi.fn(),
  listDuplicates: vi.fn(),
  previewMerge: vi.fn(),
  mergeFair: vi.fn(),
  keepSeparate: vi.fn(),
  listAdapters: vi.fn(),
  listScraperRuns: vi.fn(),
  listParticipants: vi.fn(),
}));

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    session: {
      accessToken: "token",
      organizationId: "org-1",
      isSuperAdmin: harness.isSuperAdmin,
    },
    isAuthenticated: true,
    login: async () => undefined,
    logout: async () => undefined,
  }),
}));

vi.mock("../hooks/usePermissions", () => ({
  usePermissions: () => ({
    grantedPermissions: [],
    bypass: false,
    can: () => harness.allowPermissions,
    canAny: () => harness.allowPermissions,
  }),
}));

vi.mock("../api/fairs", async () => {
  const actual = await vi.importActual<typeof import("../api/fairs")>("../api/fairs");
  return {
    ...actual,
    listFairs: (...args: unknown[]) => harness.listFairs(...args),
    getFair: (...args: unknown[]) => harness.getFair(...args),
    compareSystemFairImport: (...args: unknown[]) => harness.compare(...args),
    runFairScraper: (...args: unknown[]) => harness.runScraper(...args),
    syncTobbSystemFairs: (...args: unknown[]) => harness.syncTobb(...args),
    listSystemFairDuplicates: (...args: unknown[]) => harness.listDuplicates(...args),
    previewSystemFairMerge: (...args: unknown[]) => harness.previewMerge(...args),
    mergeSystemFair: (...args: unknown[]) => harness.mergeFair(...args),
    keepSystemFairsSeparate: (...args: unknown[]) => harness.keepSeparate(...args),
  };
});

vi.mock("../api/scraper", () => ({
  listAdapters: (...args: unknown[]) => harness.listAdapters(...args),
  listScraperRuns: (...args: unknown[]) => harness.listScraperRuns(...args),
}));

vi.mock("../api/participations", () => ({
  listParticipantsByFair: (...args: unknown[]) => harness.listParticipants(...args),
  createParticipation: vi.fn(),
  updateParticipation: vi.fn(),
  deleteParticipation: vi.fn(),
  moveParticipantsToFair: vi.fn(),
}));

function fair(partial: Partial<Fair> = {}): Fair {
  return {
    id: "fair-1",
    organization_id: partial.origin === "system" ? null : "org-1",
    origin: "organization",
    name: "Win Eurasia",
    organizer: "TÜYAP",
    venue: "Tüyap",
    city: "İstanbul",
    country: "Türkiye",
    start_date: "2026-09-01",
    end_date: "2026-09-05",
    website: null,
    status: "planned",
    description: null,
    adapter_key: "tobb",
    source_url: "https://example.test",
    scraper_config: { page_size: 50 },
    normalized_name: "win eurasia",
    scraped_record_count: null,
    scraped_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    deleted_at: null,
    ...partial,
    display_name: partial.display_name ?? partial.name ?? "Win Eurasia",
  };
}

function listResponse(items: Fair[]): StandardListResponse<Fair> {
  return {
    items,
    pagination: {
      page: 1,
      pageSize: 25,
      totalItems: items.length,
      totalPages: 1,
      hasNext: false,
      hasPrevious: false,
    },
    sorting: { field: "start_date", direction: "desc" },
    filters: {},
  };
}

function buttonByText(root: ParentNode, text: string): HTMLButtonElement | undefined {
  return Array.from(root.querySelectorAll("button")).find((button) =>
    button.textContent?.includes(text),
  );
}

describe("system fair frontend", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    harness.isSuperAdmin = false;
    harness.allowPermissions = true;
    harness.listFairs.mockReset();
    harness.getFair.mockReset();
    harness.compare.mockReset();
    harness.runScraper.mockReset();
    harness.syncTobb.mockReset();
    harness.listDuplicates.mockReset();
    harness.previewMerge.mockReset();
    harness.mergeFair.mockReset();
    harness.keepSeparate.mockReset();
    harness.listDuplicates.mockResolvedValue({ items: [] });
    harness.listAdapters.mockReset();
    harness.listScraperRuns.mockReset();
    harness.listParticipants.mockReset();
    harness.listAdapters.mockResolvedValue({ items: [] });
    harness.listScraperRuns.mockResolvedValue({ items: [] });
    harness.listParticipants.mockResolvedValue({
      items: [],
      pagination: {
        page: 1,
        pageSize: 1,
        totalItems: 0,
        totalPages: 0,
        hasNext: false,
        hasPrevious: false,
      },
      sorting: { field: "company_name", direction: "asc" },
      filters: {},
    });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  async function render(node: React.ReactElement) {
    await act(async () => {
      root.render(node);
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
  }

  it("accepts a nullable organization id on the fair contract", () => {
    const source = readFileSync(path.join(process.cwd(), "src/types/fair.ts"), "utf8");
    expect(source).toContain("organization_id: string | null");
    expect(source).toContain('origin: "organization" | "system"');
    expect(source).toContain("display_name: string");
    expect(source).toContain("scraped_record_count: number | null");
    expect(source).toContain("scraped_at: string | null");
    const system = fair({ origin: "system", organization_id: null });
    expect(system.organization_id).toBeNull();
    expect(systemFairScrapeReady(system)).toBe(false);
    expect(
      systemFairScrapeReady({ scraped_record_count: 427, scraped_at: "2026-09-30T12:00:00Z" }),
    ).toBe(true);
  });

  it("shows the short display name in the list and the official name on detail", async () => {
    const official =
      "AVRASYA AMBALAJ 2026- İSTANBUL 31.ULUSLARARASI AMBALAJ ENDÜSTRİSİ FUARI";
    const system = fair({
      origin: "system",
      name: official,
      display_name: "AVRASYA AMBALAJ 2026 – İSTANBUL",
      city: "İSTANBUL",
    });
    await render(
      React.createElement(FairTable, {
        items: [system],
        onOpenDetail: vi.fn(),
        archivingId: null,
        restoringId: null,
      }),
    );
    expect(container.textContent).toContain("AVRASYA AMBALAJ 2026 – İSTANBUL");
    expect(container.textContent).not.toContain("31.ULUSLARARASI");
    expect(container.textContent).toContain(fairLabels.systemFair);

    harness.getFair.mockResolvedValue(system);
    await render(
      React.createElement(FairDetailPage, {
        fairId: system.id,
        onBack: vi.fn(),
      }),
    );
    for (let attempt = 0; attempt < 8 && !container.textContent?.includes(fairLabels.officialName); attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }
    expect(container.querySelector("h1")?.textContent).toContain("AVRASYA AMBALAJ 2026 – İSTANBUL");
    expect(container.textContent).toContain(fairLabels.officialName);
    expect(container.textContent).toContain(official);
  });

  it("renders the backend status label for system and organization fairs", async () => {
    const past = fair({
      id: "past-system",
      origin: "system",
      name: "OCAK FUARI",
      display_name: "OCAK FUARI",
      status: "completed",
    });
    const running = fair({
      id: "running-system",
      origin: "system",
      name: "BUGÜN FUARI",
      display_name: "BUGÜN FUARI",
      status: "active",
    });
    const organization = fair({
      id: "org-fair",
      origin: "organization",
      name: "Avrasya Ambalaj",
      status: "planned",
    });
    await render(
      React.createElement(FairTable, {
        items: [past, running, organization],
        onOpenDetail: vi.fn(),
        archivingId: null,
        restoringId: null,
      }),
    );
    expect(container.textContent).toContain(fairStatusLabels.completed);
    expect(container.textContent).toContain(fairStatusLabels.active);
    expect(container.textContent).toContain(fairStatusLabels.planned);

    harness.getFair.mockResolvedValue(past);
    await render(
      React.createElement(FairDetailPage, {
        fairId: past.id,
        onBack: vi.fn(),
      }),
    );
    for (let attempt = 0; attempt < 8 && !container.textContent?.includes(fairStatusLabels.completed); attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }
    expect(container.textContent).toContain("OCAK FUARI");
    expect(container.textContent).toContain(fairStatusLabels.completed);
  });

  it("renders a system fair row with indicator, scrape metadata, and no customer management actions", async () => {
    const system = fair({
      origin: "system",
      scraped_record_count: 427,
      scraped_at: "2026-09-30T12:00:00Z",
    });
    await render(
      React.createElement(FairTable, {
        items: [system],
        onEdit: vi.fn(),
        onArchive: vi.fn(),
        onRestore: vi.fn(),
        archivingId: null,
        restoringId: null,
      }),
    );

    expect(container.textContent).toContain(fairLabels.systemFair);
    expect(container.textContent).toContain("427 kayıt");
    expect(container.textContent).toContain(fairLabels.scrapedAt);
    expect(container.textContent).toContain("30.09.2026");
    expect(buttonByText(container, labels.edit)).toBeUndefined();
    expect(buttonByText(container, labels.archive)).toBeUndefined();
    expect(buttonByText(container, labels.restore)).toBeUndefined();
    const compare = buttonByText(container, fairLabels.compareWithCrm);
    expect(compare).toBeTruthy();
    expect(compare?.disabled).toBe(false);
  });

  it("disables compare when a system fair has no scrape result", async () => {
    const onCompare = vi.fn();
    await render(
      React.createElement(FairTable, {
        items: [fair({ origin: "system" })],
        onEdit: vi.fn(),
        onArchive: vi.fn(),
        onRestore: vi.fn(),
        onCompare,
        archivingId: null,
        restoringId: null,
      }),
    );

    const compare = buttonByText(container, fairLabels.compareWithCrm);
    expect(compare?.disabled).toBe(true);
    expect(compare?.title).toBe(fairLabels.compareUnavailable);
    expect(container.textContent).toContain("—");
    compare?.click();
    expect(onCompare).not.toHaveBeenCalled();
  });

  it("keeps organization fair row actions", async () => {
    await render(
      React.createElement(FairTable, {
        items: [fair({ origin: "organization" })],
        onEdit: vi.fn(),
        onArchive: vi.fn(),
        onRestore: vi.fn(),
        archivingId: null,
        restoringId: null,
      }),
    );

    expect(container.textContent).not.toContain(fairLabels.systemFair);
    expect(buttonByText(container, fairLabels.compareWithCrm)).toBeUndefined();
    expect(buttonByText(container, labels.edit)).toBeTruthy();
    expect(buttonByText(container, labels.archive)).toBeTruthy();
  });

  it("starts compare from the list once and opens the existing continue route", async () => {
    const system = fair({
      origin: "system",
      scraped_record_count: 12,
      scraped_at: "2026-09-30T12:00:00Z",
    });
    harness.listFairs.mockResolvedValue(listResponse([system]));
    let release: (value: { batch_id: string }) => void = () => undefined;
    harness.compare.mockImplementation(
      () =>
        new Promise((resolve) => {
          release = resolve;
        }),
    );
    const onContinueImport = vi.fn();
    await render(React.createElement(FairsPage, { onContinueImport }));
    for (let attempt = 0; attempt < 8 && !buttonByText(container, fairLabels.compareWithCrm); attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }

    const compare = buttonByText(container, fairLabels.compareWithCrm);
    expect(compare?.disabled).toBe(false);
    await act(async () => {
      compare?.click();
      compare?.click();
    });
    expect(harness.compare).toHaveBeenCalledTimes(1);
    expect(harness.compare).toHaveBeenCalledWith(system.id);

    await act(async () => {
      release({ batch_id: "batch-9" });
      await Promise.resolve();
    });
    expect(onContinueImport).toHaveBeenCalledWith("batch-9");
  });

  it("shows the compare API error on the fair list", async () => {
    const system = fair({
      origin: "system",
      scraped_record_count: 3,
      scraped_at: "2026-09-30T12:00:00Z",
    });
    harness.listFairs.mockResolvedValue(listResponse([system]));
    harness.compare.mockRejectedValue(new ApiError("karşılaştırma kapalı", 400));
    await render(React.createElement(FairsPage, { onContinueImport: vi.fn() }));
    for (let attempt = 0; attempt < 8 && !buttonByText(container, fairLabels.compareWithCrm); attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }
    await act(async () => {
      buttonByText(container, fairLabels.compareWithCrm)?.click();
      await Promise.resolve();
    });
    expect(container.textContent).toContain("karşılaştırma kapalı");
  });

  it("hides customer system-fair management and continues a ready compare into the wizard", async () => {
    const system = fair({
      origin: "system",
      scraped_record_count: 427,
      scraped_at: "2026-09-30T12:00:00Z",
    });
    harness.getFair.mockResolvedValue(system);
    harness.compare.mockResolvedValue({ batch_id: "batch-1" });
    const onContinueImport = vi.fn();
    await render(
      React.createElement(FairDetailPage, {
        fairId: system.id,
        onBack: vi.fn(),
        onContinueImport,
      }),
    );
    for (let attempt = 0; attempt < 8 && !container.textContent?.includes(system.name); attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }

    expect(container.textContent).toContain(fairLabels.systemFair);
    expect(container.textContent).toContain("427 kayıt");
    expect(container.textContent).toContain("30.09.2026");
    expect(buttonByText(container, labels.edit)).toBeUndefined();
    expect(buttonByText(container, labels.archive)).toBeUndefined();
    expect(buttonByText(container, participationLabels.addCompany)).toBeTruthy();
    expect(buttonByText(container, fairLabels.moveCustomersAction)).toBeUndefined();
    expect(buttonByText(container, importLabels.importFromFair)).toBeUndefined();
    expect(buttonByText(container, fairLabels.runSystemScraper)).toBeUndefined();
    expect(container.textContent).not.toContain(fairLabels.scraperConfig);
    expect(harness.listScraperRuns).not.toHaveBeenCalled();

    await act(async () => {
      buttonByText(container, fairLabels.compareWithCrm)?.click();
      await Promise.resolve();
    });
    expect(harness.compare).toHaveBeenCalledWith(system.id);
    expect(onContinueImport).toHaveBeenCalledWith("batch-1");
  });

  it("blocks a second compare submit while the first request is in flight", async () => {
    const system = fair({
      origin: "system",
      scraped_record_count: 8,
      scraped_at: "2026-09-30T12:00:00Z",
    });
    harness.getFair.mockResolvedValue(system);
    let release: (value: { batch_id: string }) => void = () => undefined;
    harness.compare.mockImplementation(
      () =>
        new Promise((resolve) => {
          release = resolve;
        }),
    );
    await render(
      React.createElement(FairDetailPage, {
        fairId: system.id,
        onBack: vi.fn(),
        onContinueImport: vi.fn(),
      }),
    );
    for (let attempt = 0; attempt < 8 && !buttonByText(container, fairLabels.compareWithCrm); attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }
    const compare = buttonByText(container, fairLabels.compareWithCrm);
    await act(async () => {
      compare?.click();
      compare?.click();
    });
    expect(harness.compare).toHaveBeenCalledTimes(1);
    await act(async () => {
      release({ batch_id: "batch-2" });
    });
  });

  it("shows a compare failure with the existing error banner", async () => {
    const system = fair({
      origin: "system",
      scraped_record_count: 8,
      scraped_at: "2026-09-30T12:00:00Z",
    });
    harness.getFair.mockResolvedValue(system);
    harness.compare.mockRejectedValue(new ApiError("fuar verisi okunamadı", 400));
    await render(React.createElement(FairDetailPage, { fairId: system.id, onBack: vi.fn() }));
    for (let attempt = 0; attempt < 8 && !buttonByText(container, fairLabels.compareWithCrm); attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }
    await act(async () => {
      buttonByText(container, fairLabels.compareWithCrm)?.click();
      await Promise.resolve();
    });
    expect(container.textContent).toContain("fuar verisi okunamadı");
  });

  it("lets a super admin edit system fair config and start the scraper", async () => {
    harness.isSuperAdmin = true;
    const system = fair({
      origin: "system",
      scraped_record_count: 4,
      scraped_at: "2026-09-30T12:00:00Z",
    });
    harness.getFair.mockResolvedValue(system);
    harness.runScraper.mockResolvedValue({ id: "run-1" });
    await render(React.createElement(FairDetailPage, { fairId: system.id, onBack: vi.fn() }));
    for (let attempt = 0; attempt < 8 && !buttonByText(container, fairLabels.runSystemScraper); attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }

    expect(buttonByText(container, labels.edit)).toBeTruthy();
    expect(container.textContent).toContain(fairLabels.scraperConfig);
    await act(async () => {
      buttonByText(container, labels.edit)?.click();
    });
    expect(container.textContent).toContain(fairLabels.editFair);
    expect(container.textContent).toContain(fairLabels.adapter);
    expect(container.textContent).toContain(fairLabels.sourceUrl);

    await act(async () => {
      buttonByText(container, fairLabels.runSystemScraper)?.click();
      await Promise.resolve();
    });
    expect(harness.runScraper).toHaveBeenCalledWith(system.id);
  });

  it("keeps organization fair detail actions and leaves the import wizard resume route in place", async () => {
    harness.getFair.mockResolvedValue(fair({ origin: "organization" }));
    await render(
      React.createElement(FairDetailPage, {
        fairId: "fair-1",
        onBack: vi.fn(),
        onImportParticipants: vi.fn(),
        onContinueImport: vi.fn(),
      }),
    );
    for (let attempt = 0; attempt < 8 && !container.textContent?.includes("Win Eurasia"); attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }

    expect(buttonByText(container, labels.edit)).toBeTruthy();
    expect(buttonByText(container, labels.archive)).toBeTruthy();
    expect(buttonByText(container, participationLabels.addCompany)).toBeTruthy();
    expect(buttonByText(container, fairLabels.moveCustomersAction)).toBeTruthy();
    expect(buttonByText(container, importLabels.importFromFair)).toBeTruthy();
    expect(buttonByText(container, fairLabels.compareWithCrm)).toBeUndefined();
    expect(buttonByText(container, fairLabels.runSystemScraper)).toBeUndefined();
    expect(container.textContent).not.toContain(fairLabels.systemFair);

    const appSource = readFileSync(path.join(process.cwd(), "src/App.tsx"), "utf8");
    const wizardSource = readFileSync(path.join(process.cwd(), "src/pages/ImportWizardPage.tsx"), "utf8");
    expect(appSource).toContain('"/data-integration/imports/continue/:batchId"');
    expect(appSource).toContain("resumeBatchId={parsed.batchId}");
    expect(appSource).toContain("onContinueImport={(batchId) => goToDataIntegration(`/data-integration/imports/continue/${batchId}`)}");
    expect(wizardSource).not.toContain("compare-import");
  });

  async function renderFairs() {
    harness.listFairs.mockResolvedValue(listResponse([fair({ name: "Mevcut Fuar" })]));
    await render(React.createElement(FairsPage, {}));
    for (let attempt = 0; attempt < 8 && !container.textContent?.includes("Mevcut Fuar"); attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }
  }

  function setTobbYear(value: string) {
    const input = container.querySelector("#tobb-sync-year") as HTMLInputElement;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    setter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  it("loads the fair list without sending an explicit sort", async () => {
    await renderFairs();
    const params = harness.listFairs.mock.calls[0]?.[0] as { sortBy?: string | null; sortOrder?: string | null };
    expect(params.sortBy ?? null).toBeNull();
    expect(params.sortOrder ?? null).toBeNull();
  });

  it("shows TOBB sync only to the super admin and sends the selected year", async () => {
    harness.isSuperAdmin = false;
    harness.allowPermissions = true;
    await renderFairs();
    expect(buttonByText(container, fairLabels.syncTobb)).toBeUndefined();

    act(() => {
      root.unmount();
    });
    root = createRoot(container);
    harness.allowPermissions = false;
    await renderFairs();
    expect(buttonByText(container, fairLabels.syncTobb)).toBeUndefined();

    act(() => {
      root.unmount();
    });
    root = createRoot(container);
    harness.isSuperAdmin = true;
    harness.allowPermissions = false;
    await renderFairs();
    expect(buttonByText(container, fairLabels.syncTobb)).toBeTruthy();

    let release: (value: { inserted: number; updated: number; conflicts: number }) => void = () => undefined;
    harness.syncTobb.mockImplementation(
      () =>
        new Promise((resolve) => {
          release = resolve;
        }),
    );
    await act(async () => {
      setTobbYear("2024");
    });
    const sync = buttonByText(container, fairLabels.syncTobb);
    await act(async () => {
      sync?.click();
      sync?.click();
    });
    expect(harness.syncTobb).toHaveBeenCalledTimes(1);
    expect(harness.syncTobb).toHaveBeenCalledWith(2024);
    const callsBeforeResult = harness.listFairs.mock.calls.length;
    await act(async () => {
      release({ inserted: 120, updated: 35, conflicts: 2 });
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(container.textContent).toContain(
      "TOBB güncellemesi tamamlandı: 120 yeni, 35 güncellendi, 2 çakışma.",
    );
    expect(
      tobbSyncSummary({
        inserted: 0,
        updated: 0,
        conflicts: 1,
        conflict_items: [
          {
            name: "X FUARI",
            identity_name: "X FUARI",
            city: "İstanbul",
            fair_ids: ["id-1", "id-2"],
          },
        ],
      }),
    ).toContain("Çakışan fuarlar: X FUARI / İstanbul — id-1, id-2.");
    expect(harness.listFairs.mock.calls.length).toBeGreaterThan(callsBeforeResult);
    expect(container.textContent).toContain("Mevcut Fuar");
  });

  it("shows a TOBB sync failure without refreshing the fair list", async () => {
    harness.isSuperAdmin = true;
    await renderFairs();
    const callsAfterLoad = harness.listFairs.mock.calls.length;
    harness.syncTobb.mockRejectedValue(new ApiError("TOBB calendar request timed out", 400));
    await act(async () => {
      buttonByText(container, fairLabels.syncTobb)?.click();
      await Promise.resolve();
    });
    expect(container.textContent).toContain("TOBB calendar request timed out");
    expect(harness.listFairs.mock.calls.length).toBe(callsAfterLoad);
    expect(container.textContent).toContain("Mevcut Fuar");
  });

  it("shows duplicate system fairs only to a super admin and asks before merge", async () => {
    const group = {
      identity_name: "KYROX MERGE FAIR",
      city: "İstanbul",
      fairs: [
        {
          id: "fair-a",
          name: "KYROX 2026",
          city: "İstanbul",
          start_date: "2026-10-01",
          end_date: "2026-10-04",
          organizer: "TOBB",
          website: "https://a.test",
          external_id: "2026:1",
          source: "tobb",
          participations: 1,
          todos: 2,
          quotes: 3,
          imports: 4,
          scraper_runs: 5,
          has_scraper_config: false,
        },
        {
          id: "fair-b",
          name: "KYROX 2027",
          city: "İstanbul",
          start_date: "2027-10-01",
          end_date: "2027-10-04",
          organizer: "TOBB",
          website: null,
          external_id: "2027:2",
          source: "tobb",
          participations: 0,
          todos: 0,
          quotes: 0,
          imports: 0,
          scraper_runs: 0,
          has_scraper_config: true,
        },
      ],
    };
    harness.listDuplicates.mockResolvedValue({ items: [group] });
    await renderFairs();
    expect(container.textContent).not.toContain(fairLabels.duplicateReviewTitle);

    harness.isSuperAdmin = true;
    await renderFairs();
    expect(container.textContent).toContain(fairLabels.duplicateReviewTitle);
    expect(container.textContent).toContain("KYROX 2026");
    expect(container.textContent).toContain("Katılım 1");
    expect(container.textContent).toContain(fairLabels.duplicateScraperConfig);

    const keep = container.querySelector<HTMLInputElement>('input[name="keep-KYROX MERGE FAIR|İstanbul"]');
    const merge = container.querySelectorAll<HTMLInputElement>(
      'input[name="merge-KYROX MERGE FAIR|İstanbul"]',
    );
    harness.previewMerge.mockResolvedValue({
      participations: 0,
      todos: 0,
      quotes: 0,
      activities: 0,
      imports: 0,
      scraper_runs: 0,
      email_batches: 0,
      mail_operations: 0,
      operations: 0,
      blocking_conflicts: [],
    });
    await act(async () => {
      keep?.click();
      merge[1]?.click();
      await Promise.resolve();
    });
    await act(async () => {
      buttonByText(container, fairLabels.duplicateMergeAction)?.click();
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(harness.previewMerge).toHaveBeenCalledWith("fair-b", "fair-a");
    expect(container.textContent).toContain(fairLabels.duplicateMergeConfirm);
    expect(harness.mergeFair).not.toHaveBeenCalled();
  });
});
