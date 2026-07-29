export interface TodoStepFormItem {
  /** Stable local key; UUID when loaded from API. */
  id: string;
  /** Persisted step id when known. */
  serverId: string | null;
  title: string;
}

let localStepSeq = 0;

export function createTodoStepFormItem(title = "", serverId: string | null = null): TodoStepFormItem {
  localStepSeq += 1;
  return {
    id: serverId ?? `local-step-${localStepSeq}-${Date.now()}`,
    serverId,
    title,
  };
}

export function stepsToFormItems(
  steps: Array<{ id: string; title: string }>,
): TodoStepFormItem[] {
  return steps.map((step) => createTodoStepFormItem(step.title, step.id));
}

export function nonEmptyTodoStepFormItems(items: TodoStepFormItem[]): TodoStepFormItem[] {
  return items.filter((item) => item.title.trim().length > 0);
}

export function formItemsToReplacePayload(
  items: TodoStepFormItem[],
): Array<{ id?: string; title: string }> {
  return nonEmptyTodoStepFormItems(items).map((item) => {
    const title = item.title.trim();
    if (item.serverId) {
      return { id: item.serverId, title };
    }
    return { title };
  });
}
