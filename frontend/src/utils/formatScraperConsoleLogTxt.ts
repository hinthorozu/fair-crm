import type { ScraperRunLog } from "../types/scraper";
import { formatScraperLogStepLabel } from "./scraperLogStepLabels";

export function formatScraperConsoleTime(value: string): string {
  return new Date(value).toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function formatScraperConsoleLogBlock(
  log: Pick<ScraperRunLog, "created_at" | "step" | "message">,
  enrichmentMode = false,
): string {
  const time = formatScraperConsoleTime(log.created_at);
  const step = formatScraperLogStepLabel(log.step, enrichmentMode);
  return `${time} [${step}]\n${log.message}`;
}

export function formatScraperConsoleLogExport(
  logs: Pick<ScraperRunLog, "created_at" | "step" | "message">[],
  enrichmentMode = false,
): string {
  if (logs.length === 0) {
    return "";
  }
  return `${logs.map((log) => formatScraperConsoleLogBlock(log, enrichmentMode)).join("\n\n")}\n`;
}
