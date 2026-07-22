import { describe, expect, it } from "vitest";
import {
  activityTypeSelectOptions,
  formValuesToUpdatePayload,
  type ActivityFormValues,
} from "./ActivityForm";

const baseValues = (): ActivityFormValues => ({
  type: "call",
  subject: "Subject",
  description: "Note",
  activity_date: "2026-07-22T10:00:00.000Z",
  follow_up_date: null,
  status: "completed",
  source: "system",
  contact_id: null,
  is_active: true,
});

describe("activityTypeSelectOptions", () => {
  it("includes task_completed so the select can show Diğer", () => {
    expect(activityTypeSelectOptions("task_completed")).toEqual(["task_completed"]);
  });

  it("uses manual options for editable types", () => {
    const options = activityTypeSelectOptions("call");
    expect(options).toContain("call");
    expect(options).toContain("other");
    expect(options).not.toContain("task_completed");
  });
});

describe("formValuesToUpdatePayload", () => {
  it("omits type when task_completed so PATCH cannot overwrite to call", () => {
    const payload = formValuesToUpdatePayload({
      ...baseValues(),
      type: "task_completed",
    });
    expect(payload.type).toBeUndefined();
    expect(payload.subject).toBe("Subject");
    expect(payload.status).toBe("completed");
  });

  it("includes type for manual activity types", () => {
    const payload = formValuesToUpdatePayload(baseValues());
    expect(payload.type).toBe("call");
  });
});
