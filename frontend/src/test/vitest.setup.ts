import { readFileSync as originalReadFileSync } from "node:fs";
import fs from "node:fs";
import { normalizeSourceText } from "./normalizeSourceText";

function readSourceFileSync(
  path: Parameters<typeof originalReadFileSync>[0],
  options?: Parameters<typeof originalReadFileSync>[1],
) {
  const result = originalReadFileSync(path, options as never);
  if (typeof result === "string") {
    return normalizeSourceText(result);
  }
  return result;
}

(fs as { readFileSync: typeof originalReadFileSync }).readFileSync =
  readSourceFileSync as typeof originalReadFileSync;
