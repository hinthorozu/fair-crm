import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { canAccessApplicationPath } from "./navigationPermissions";
import {
  canReadQuoteEditor,
  QUOTE_EDITOR_READ_REQUIREMENTS,
} from "./quotePermissions";

const quoteEditorSource = readFileSync(
  fileURLToPath(new URL("../pages/QuoteEditorPage.tsx", import.meta.url)),
  "utf-8",
);

describe("Quote Editor read permission consistency", () => {
  it("requires every lookup permission for the quote editor route", () => {
    const granted = [...QUOTE_EDITOR_READ_REQUIREMENTS];

    expect(canReadQuoteEditor(granted)).toBe(true);
    expect(canAccessApplicationPath("/todos/todo-1/quote", granted)).toBe(true);

    for (const missing of QUOTE_EDITOR_READ_REQUIREMENTS) {
      const partial = granted.filter((permission) => permission !== missing);
      expect(canReadQuoteEditor(partial), missing).toBe(false);
      expect(canAccessApplicationPath("/todos/todo-1/quote", partial), missing).toBe(false);
    }
  });

  it("keeps ordinary todo detail access scoped to todos.read", () => {
    expect(canAccessApplicationPath("/todos/todo-1", ["fair_crm.todos.read"])).toBe(true);
    expect(canAccessApplicationPath("/todos/todo-1", [])).toBe(false);
  });

  it("fails closed before the first quote editor API lookup", () => {
    const guardIndex = quoteEditorSource.indexOf("if (!canReadQuoteEditor(permissions))");
    const firstLookupIndex = quoteEditorSource.indexOf("const task = await getTodo(todoId);");

    expect(guardIndex).toBeGreaterThan(-1);
    expect(firstLookupIndex).toBeGreaterThan(-1);
    expect(guardIndex).toBeLessThan(firstLookupIndex);
  });
});
