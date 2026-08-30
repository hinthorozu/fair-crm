import { describe, expect, it } from "vitest";
import { QUOTE_EDITOR_READ_REQUIREMENTS } from "./quotePermissions";
import { canOpenTodoQuoteAction } from "./todoQuoteActionPermissions";

describe("todo quote action permissions", () => {
  it("allows the action only when every Quote Editor read permission is granted", () => {
    expect(canOpenTodoQuoteAction(QUOTE_EDITOR_READ_REQUIREMENTS)).toBe(true);

    for (const missing of QUOTE_EDITOR_READ_REQUIREMENTS) {
      expect(
        canOpenTodoQuoteAction(
          QUOTE_EDITOR_READ_REQUIREMENTS.filter((permission) => permission !== missing),
        ),
      ).toBe(false);
    }
  });
});
