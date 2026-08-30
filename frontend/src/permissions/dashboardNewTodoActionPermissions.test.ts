import { describe, expect, it } from "vitest";
import {
  canStartDashboardTodoCreate,
  DASHBOARD_TODO_CREATE,
} from "./dashboardNewTodoActionPermissions";

describe("dashboard new todo action permissions", () => {
  it("requires todos.create before offering new todo", () => {
    expect(canStartDashboardTodoCreate([])).toBe(false);
    expect(canStartDashboardTodoCreate([DASHBOARD_TODO_CREATE])).toBe(true);
  });
});
