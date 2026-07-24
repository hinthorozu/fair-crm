import { describe, expect, it } from "vitest";
import { formatBulkEmailRecipientDisplay } from "./bulkEmailRecipientDisplay";

describe("formatBulkEmailRecipientDisplay", () => {
  it("formats contact as name - company", () => {
    expect(
      formatBulkEmailRecipientDisplay({
        source: "contact",
        recipient_name: "Ahmet Yılmaz",
        company_name: "ERMED",
      }),
    ).toBe("Ahmet Yılmaz - ERMED");
  });

  it("formats non-contact (customer) as company only", () => {
    expect(
      formatBulkEmailRecipientDisplay({
        source: "customer",
        recipient_name: "Ahmet Yılmaz",
        company_name: "ERMED",
      }),
    ).toBe("ERMED");
  });

  it("formats manual from company_name without inventing fields", () => {
    expect(
      formatBulkEmailRecipientDisplay({
        source: "manual",
        recipient_name: null,
        company_name: "someone@example.com",
      }),
    ).toBe("someone@example.com");
  });

  it("formats excel from recipient_name (col1) without inventing", () => {
    expect(
      formatBulkEmailRecipientDisplay({
        source: "excel",
        recipient_name: "Ahmet Yılmaz",
        company_name: "Ahmet Yılmaz",
      }),
    ).toBe("Ahmet Yılmaz");
    expect(
      formatBulkEmailRecipientDisplay({
        source: "excel",
        recipient_name: "ERMED TIP MEDİKAL",
        company_name: "ERMED TIP MEDİKAL",
      }),
    ).toBe("ERMED TIP MEDİKAL");
    expect(
      formatBulkEmailRecipientDisplay({
        source: "excel",
        recipient_name: null,
        company_name: "list@example.com",
      }),
    ).toBe("list@example.com");
  });

  it("falls back to available real fields for incomplete contact rows", () => {
    expect(
      formatBulkEmailRecipientDisplay({
        source: "contact",
        recipient_name: "Ahmet Yılmaz",
        company_name: null,
      }),
    ).toBe("Ahmet Yılmaz");
    expect(
      formatBulkEmailRecipientDisplay({
        source: "contact",
        recipient_name: "  ",
        company_name: "ERMED",
      }),
    ).toBe("ERMED");
  });
});
