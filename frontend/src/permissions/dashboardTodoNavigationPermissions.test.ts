import { describe, expect, it } from "vitest";
import { canOpenDashboardTodoList, DASHBOARD_TODO_READ } from "./dashboardTodoNavigationPermissions";

describe("dashboard todo navigation permissions", () => {
  it("requires todos.read before offering Todo list navigation", () => {
    expect(canOpenDashboardTodoList([])).toBe(false);
    expect(canOpenDashboardTodoList([DASHBOARD_TODO_READ])).toBe(true);
  });
});
