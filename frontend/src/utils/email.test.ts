import { describe, expect, it } from "vitest";
import {
  invalidEmailMessage,
  isValidSingleEmail,
  parseManualRecipientInput,
  splitEmailInputParts,
  validateMultiEmailInput,
} from "./email";

describe("isValidSingleEmail", () => {
  it.each([
    "abc @.oxom",
    "abc@.com",
    "abc@domain",
    "abc domain@example.com",
    "@domain.com",
    "abc@",
    "abc..def@domain.com",
    "abc@domain..com",
  ])("rejects %s", (email) => {
    expect(isValidSingleEmail(email)).toBe(false);
  });

  it.each([
    "abc@example.com",
    "info@firma.com.tr",
    "ad.soyad+etiket@example.co.uk",
  ])("accepts %s", (email) => {
    expect(isValidSingleEmail(email)).toBe(true);
  });
});

describe("parseManualRecipientInput", () => {
  it("does not add invalid address and returns the standard error", () => {
    const result = parseManualRecipientInput("abc @.oxom");
    expect(result.emails).toEqual([]);
    expect(result.error).toBe(invalidEmailMessage);
  });

  it("adds a valid address", () => {
    expect(parseManualRecipientInput("abc@example.com")).toEqual({
      emails: ["abc@example.com"],
      error: null,
    });
  });

  it("validates each pasted address and rejects the whole batch if one is invalid", () => {
    const result = parseManualRecipientInput("abc@example.com; abc @.oxom");
    expect(result.emails).toEqual([]);
    expect(result.error).toBe(invalidEmailMessage);
  });

  it("treats Enter/comma/semicolon split paths the same", () => {
    const viaSemicolon = parseManualRecipientInput("a@example.com; b@example.com");
    const viaComma = parseManualRecipientInput("a@example.com, b@example.com");
    expect(viaSemicolon).toEqual(viaComma);
    expect(viaSemicolon.emails).toEqual(["a@example.com", "b@example.com"]);
    expect(splitEmailInputParts("a@example.com;b@example.com")).toEqual([
      "a@example.com",
      "b@example.com",
    ]);
  });

  it("skips duplicates against existing recipients without error", () => {
    expect(parseManualRecipientInput("abc@example.com", ["abc@example.com"])).toEqual({
      emails: [],
      error: null,
    });
  });
});

describe("validateMultiEmailInput", () => {
  it("returns null for valid multi-email input", () => {
    expect(validateMultiEmailInput("info@firma.com.tr; sales@firma.com.tr")).toBeNull();
  });

  it("includes the invalid token in the contact-form style message", () => {
    expect(validateMultiEmailInput("ok@example.com; abc @.oxom")).toBe(
      "Geçersiz e-posta adresi: abc @.oxom",
    );
  });
});
