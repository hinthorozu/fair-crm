/** @vitest-environment jsdom */
import React, {act} from "react";
import {createRoot, type Root} from "react-dom/client";
import {afterEach, beforeEach, expect, it, vi} from "vitest";
import {ApiError} from "../api/client";
import {TobbWorkflow} from "./TobbWorkflow";

const h = vi.hoisted(() => ({reviews: [] as unknown[], bulk: vi.fn(), decide: vi.fn(), runs: vi.fn()}));
vi.mock("../api/tobb", () => ({
  listTobbReviews: async () => ({items: h.reviews}), listTobbRuns: (...args: unknown[]) => h.runs(...args),
  listTobbMappings: async () => ({items: []}), listSystemInAppNotifications: async () => [],
  bulkTobbDates: (...args: unknown[]) => h.bulk(...args), decideTobbReview: (...args: unknown[]) => h.decide(...args),
  getTobbRun: vi.fn(), applyTobbPreview: vi.fn(), cancelTobbRun: vi.fn(), retryTobbRun: vi.fn(),
  retryTobbNotification: vi.fn(), changeTobbMapping: vi.fn(),
}));

let root: Root;
let container: HTMLDivElement;
const dateReview = (id: string, name: string, end: string | null) => ({id, fair_id: `fair-${id}`, kind: "dates", name, status: "pending", version: 3,
  stored_values: {start_date: "2026-10-20", end_date: "2026-10-23"},
  proposed_values: {start_date: "2026-11-11", end_date: end}, source_row: {}});

beforeEach(() => {
  h.bulk.mockReset(); h.decide.mockReset();
  h.runs.mockReset(); h.runs.mockResolvedValue({items: []});
  h.reviews = [dateReview("valid", "Geçerli Fuar", "2026-11-14"), dateReview("missing", "Eksik Fuar", null)];
  container = document.createElement("div"); document.body.append(container); root = createRoot(container);
});
afterEach(() => {act(() => root.unmount()); container.remove();});

async function render() {
  await act(async () => {root.render(React.createElement(TobbWorkflow, {runId: null, onRunSelected: vi.fn(), onChanged: vi.fn()})); await Promise.resolve();});
}

function button(text: string) {return [...container.querySelectorAll("button")].find(item => item.textContent === text)!;}

it("submits only selected date versions and retains failed selected rows with reasons", async () => {
  await render();
  expect(button("Seçili Tarihleri Uygula").disabled).toBe(true);
  await act(async () => {
    (container.querySelector("#tobb-review-valid") as HTMLInputElement).click();
    (container.querySelector("#tobb-review-missing") as HTMLInputElement).click();
  });
  h.bulk.mockImplementation(async () => {
    h.reviews = [dateReview("missing", "Eksik Fuar", null)];
    return {items: [{id: "valid", success: true}, {id: "missing", success: false, error: "Bitiş tarihi eksik"}]};
  });
  await act(async () => {button("Seçili Tarihleri Uygula").click(); await Promise.resolve();});
  expect(h.bulk).toHaveBeenCalledWith([{id: "valid", version: 3, decision: "apply"}, {id: "missing", version: 3, decision: "apply"}]);
  expect(container.textContent).toContain("Eksik Fuar: Bitiş tarihi eksik");
  expect(container.querySelector("#tobb-review-valid")).toBeNull();
  expect((container.querySelector("#tobb-review-missing") as HTMLInputElement).checked).toBe(true);
  expect(button("Seçili Tarihleri Koru").disabled).toBe(false);
});

it("reloads the current queue after a stale decision instead of reporting success", async () => {
  h.reviews = [dateReview("valid", "Geçerli Fuar", "2026-11-14")];
  h.decide.mockImplementation(async () => {h.reviews = []; throw new ApiError("İnceleme değişti", 409, {current: {status: "approved"}});});
  await render();
  await act(async () => {button("Uygula").click(); await Promise.resolve();});
  expect(container.textContent).toContain("İnceleme değişti");
  expect(container.textContent).toContain("Bekleyen TOBB önerisi yok.");
  expect(container.textContent).not.toContain("Karar kaydedildi.");
});

it("loads earlier run history without hiding the existing page", async () => {
  const rows = Array.from({length: 51}, (_, i) => ({id: `run-${i}`, status: "completed", run_source: "tobb_weekly",
    started_at: "2026-10-12T03:00:00Z", summary: {phase: "finished", years: [2026], year_results: {}}}));
  h.runs.mockImplementation(async (offset = 0) => ({items: rows.slice(offset, offset + 50)}));
  await render();
  await act(async () => {button("Önceki Çalışmaları Göster").click(); await Promise.resolve();});
  expect(h.runs).toHaveBeenCalledWith(50);
  expect(button("Önceki Çalışmaları Göster")).toBeUndefined();
  const visibleHistory = [...container.querySelectorAll("table")].at(-1)!;
  expect(visibleHistory.querySelectorAll("tbody > tr")).toHaveLength(51);
});
