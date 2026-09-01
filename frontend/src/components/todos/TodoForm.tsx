import React from "react";
import { ApiError } from "../../api/client";
import { CustomerEntitySelect } from "../CustomerEntitySelect";
import { FairEntitySelect } from "../FairEntitySelect";
import { isoToLocalDatetime, localDatetimeToIso } from "../ActivityForm";
import {
  FieldError,
  FormField,
  FormGrid,
  SelectInput,
  TextareaInput,
  TextInput,
} from "../ui/form";
import { useReportFormDirty } from "../../hooks/useModalForm";
import {
  isCreatableTodoCategory,
  todoCategoryLabels,
  todoCategoryOptions,
  todoFormStatusLabels,
  todoFormStatusOptions,
  todoLabels,
  todoPriorityLabels,
  todoPriorityOptions,
} from "../../labels/todoLabels";
import type {
  CreateTodoPayload,
  CreatableTodoCategory,
  Todo,
  TodoFormStatus,
  TodoPriority,
  UpdateTodoPayload,
} from "../../types/todo";
import {
  createTodoStepFormItem,
  type TodoStepFormItem,
} from "../../utils/todoStepForm";
import { TodoStepFieldList } from "./TodoStepFieldList";
import { config } from "../../config";
import {
  getGrantedCorePermissions,
  hasGrantedCorePermission,
  type GrantedPermissionCollection,
} from "../../permissions/corePermissions";
import { CUSTOMER_READ } from "../../permissions/customerPermissions";
import { FAIR_READ } from "../../permissions/fairPermissions";
import { TODO_PERMISSION_UPDATE } from "../../permissions/todoPermissions";

export const TODO_FORM_ID = "todo-entity-form";

const STAND_WORK_DEFAULT_STEPS = [
  "Sözleşme İmzalandı mı?",
  "Ön Ödeme",
  "Kalan Ödeme",
  "Fatura Kesilecek Mi?",
  "Tasarım Son Haline Geldi Mi?",
  "Elektrik Planı Çizildi Mi?",
  "Karolajlı Plan Formu Çizildi Mi?",
  "Eşleşme Yapıldı Mı?",
  "Malzeme Listei Çıktı Mı?",
  "Ekstra Liste + Sipariş",
  "Zemin Liste + Sipariş",
  "Görsel Ölçüleri Müşteriye Verildi Mi?",
  "Müşteriden Logo, Görsel V.S. Alındı Mı?",
  "Görsellerin Kontrolleri Yapıldı Mı?",
  "Reklam (Logo, Görsel VS Baskıya Gönderildi Mi?",
  "Elektrik Sipariş",
] as const;

function appendStandWorkDefaultSteps(items: TodoStepFormItem[]): TodoStepFormItem[] {
  const existingTitles = new Set(items.map((item) => item.title.trim().toLocaleLowerCase("tr-TR")));
  const missing = STAND_WORK_DEFAULT_STEPS.filter(
    (title) => !existingTitles.has(title.trim().toLocaleLowerCase("tr-TR")),
  );
  if (missing.length === 0) return items;
  return [...items, ...missing.map((title) => createTodoStepFormItem(title))];
}

export interface TodoFormValues {
  title: string;
  description: string;
  status: TodoFormStatus;
  priority: TodoPriority;
  category: CreatableTodoCategory;
  deadline: string;
  assignee_user_id: string;
  customer_id: string;
  source_fair_id: string;
  steps: TodoStepFormItem[];
}

export const defaultTodoFormValues = (): TodoFormValues => ({
  title: "",
  description: "",
  status: "todo",
  priority: "normal",
  category: "genel_gorev",
  deadline: "",
  assignee_user_id: "",
  customer_id: "",
  source_fair_id: "",
  steps: [],
});

export function todoToFormValues(
  todo: Todo,
  steps: TodoStepFormItem[] = [],
): TodoFormValues {
  const status: TodoFormStatus =
    todo.status === "todo" || todo.status === "in_progress" || todo.status === "cancelled"
      ? todo.status
      : "todo";
  const category: CreatableTodoCategory = isCreatableTodoCategory(todo.category)
    ? todo.category
    : "genel_gorev";
  return {
    title: todo.title,
    description: todo.description ?? "",
    status,
    priority: todo.priority,
    category,
    deadline: isoToLocalDatetime(todo.deadline),
    assignee_user_id: todo.assignee_user_id ?? "",
    customer_id: todo.customer_id ?? "",
    source_fair_id: todo.source_fair_id ?? "",
    steps,
  };
}

export function formValuesToCreatePayload(values: TodoFormValues): CreateTodoPayload {
  return {
    title: values.title.trim(),
    description: values.description.trim() || null,
    status: values.status,
    priority: values.priority,
    category: values.category,
    deadline: values.deadline ? localDatetimeToIso(values.deadline) : null,
    assignee_user_id: values.assignee_user_id.trim() || null,
    customer_id: values.customer_id.trim() || null,
    source_fair_id: values.source_fair_id.trim() || null,
  };
}

export function formValuesToUpdatePayload(values: TodoFormValues): UpdateTodoPayload {
  return {
    title: values.title.trim(),
    description: values.description.trim() || null,
    status: values.status,
    priority: values.priority,
    category: values.category,
    deadline: values.deadline ? localDatetimeToIso(values.deadline) : null,
    assignee_user_id: values.assignee_user_id.trim() || null,
    customer_id: values.customer_id.trim() || null,
    source_fair_id: values.source_fair_id.trim() || null,
  };
}

export function canEditTodo(todo: Todo): boolean {
  return todo.status !== "done" && todo.status !== "archived";
}

export function canUseTodoCustomerSelector(granted: GrantedPermissionCollection): boolean {
  return hasGrantedCorePermission(granted, CUSTOMER_READ);
}

export function canUseTodoFairSelector(granted: GrantedPermissionCollection): boolean {
  return hasGrantedCorePermission(granted, FAIR_READ);
}

interface TodoFormProps {
  initial?: TodoFormValues;
  /** Hydrate when the edited todo (or create session) changes — not on fresh `initial` refs. */
  hydrateKey?: string;
  onSubmit: (values: TodoFormValues) => Promise<void>;
  onSavingChange?: (saving: boolean) => void;
}

export function TodoForm({
  initial,
  hydrateKey = "create",
  onSubmit,
  onSavingChange,
}: TodoFormProps) {
  const [values, setValues] = React.useState<TodoFormValues>(
    () => initial ?? defaultTodoFormValues(),
  );
  const [baseline, setBaseline] = React.useState<TodoFormValues>(
    () => initial ?? defaultTodoFormValues(),
  );
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const grantedPermissions = getGrantedCorePermissions();
  const canCustomersRead =
    config.devBypassEnabled || canUseTodoCustomerSelector(grantedPermissions);
  const canFairsRead = config.devBypassEnabled || canUseTodoFairSelector(grantedPermissions);
  const canManageSteps =
    config.devBypassEnabled || hasGrantedCorePermission(grantedPermissions, TODO_PERMISSION_UPDATE);

  useReportFormDirty(values, baseline);

  React.useEffect(() => {
    const next = initial ?? defaultTodoFormValues();
    setValues(next);
    setBaseline(next);
    setError(null);
    // Hydrate only when the edited todo (or create session) changes —
    // not when parent re-renders with a fresh `initial` object reference.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional: hydrateKey only
  }, [hydrateKey]);

  React.useEffect(() => {
    onSavingChange?.(saving);
  }, [saving, onSavingChange]);

  const requiresCustomerAndFair = values.category === "teklif" || values.category === "stand_work";

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!values.title.trim()) {
      setError(todoLabels.titleRequired);
      return;
    }
    if (requiresCustomerAndFair && (!values.customer_id || !values.source_fair_id)) {
      if ((!values.customer_id && !canCustomersRead) || (!values.source_fair_id && !canFairsRead)) {
        setError(todoLabels.entityReadPermissionRequired);
        return;
      }
      setError(
        values.category === "stand_work"
          ? "Stand İşleri görevi için müşteri ve kaynak fuar zorunludur."
          : "Teklif görevi için müşteri ve kaynak fuar zorunludur.",
      );
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit(canManageSteps ? values : { ...values, steps: [] });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : todoLabels.loadError);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form id={TODO_FORM_ID} onSubmit={(event) => void handleSubmit(event)}>
      <FormGrid>
        <FormField label={todoLabels.fieldTitle} htmlFor="todo-title" required fullWidth>
          <TextInput
            id="todo-title"
            value={values.title}
            onChange={(event) => setValues((prev) => ({ ...prev, title: event.target.value }))}
            required
          />
        </FormField>
        <FormField label={todoLabels.fieldDescription} htmlFor="todo-description" fullWidth>
          <TextareaInput
            id="todo-description"
            value={values.description}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, description: event.target.value }))
            }
            rows={4}
          />
        </FormField>
        <FormField label={todoLabels.fieldStatus} htmlFor="todo-status">
          <SelectInput
            id="todo-status"
            value={values.status}
            onChange={(event) =>
              setValues((prev) => ({
                ...prev,
                status: event.target.value as TodoFormStatus,
              }))
            }
          >
            {todoFormStatusOptions.map((status) => (
              <option key={status} value={status}>
                {todoFormStatusLabels[status]}
              </option>
            ))}
          </SelectInput>
        </FormField>
        <FormField label={todoLabels.fieldPriority} htmlFor="todo-priority">
          <SelectInput
            id="todo-priority"
            value={values.priority}
            onChange={(event) =>
              setValues((prev) => ({
                ...prev,
                priority: event.target.value as TodoPriority,
              }))
            }
          >
            {todoPriorityOptions.map((priority) => (
              <option key={priority} value={priority}>
                {todoPriorityLabels[priority]}
              </option>
            ))}
          </SelectInput>
        </FormField>
        <FormField label={todoLabels.fieldCategory} htmlFor="todo-category">
          <SelectInput
            id="todo-category"
            value={values.category}
            onChange={(event) => {
              const category = event.target.value as CreatableTodoCategory;
              setValues((prev) => ({
                ...prev,
                category,
                steps:
                  canManageSteps && category === "stand_work" && prev.category !== "stand_work"
                    ? appendStandWorkDefaultSteps(prev.steps)
                    : prev.steps,
              }));
            }}
          >
            {todoCategoryOptions.map((category) => (
              <option key={category} value={category}>
                {todoCategoryLabels[category]}
              </option>
            ))}
          </SelectInput>
        </FormField>
        <FormField label={todoLabels.fieldDeadline} htmlFor="todo-deadline">
          <TextInput
            id="todo-deadline"
            type="datetime-local"
            value={values.deadline}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, deadline: event.target.value }))
            }
          />
        </FormField>
        <FormField
          label={todoLabels.fieldCustomer}
          htmlFor="todo-customer"
          fullWidth
          hint={todoLabels.fieldCustomerHint}
          required={requiresCustomerAndFair}
        >
          {canCustomersRead ? (
            <CustomerEntitySelect
              id="todo-customer"
              value={values.customer_id}
              onChange={(customerId) =>
                setValues((prev) => ({ ...prev, customer_id: customerId }))
              }
              placeholder={todoLabels.fieldCustomerPlaceholder}
              allowClear
            />
          ) : (
            <FieldError>{todoLabels.customerReadPermissionRequired}</FieldError>
          )}
        </FormField>
        <FormField
          label={todoLabels.fieldSourceFair}
          htmlFor="todo-source-fair"
          fullWidth
          hint={todoLabels.fieldSourceFairHint}
          required={requiresCustomerAndFair}
        >
          {canFairsRead ? (
            <FairEntitySelect
              id="todo-source-fair"
              value={values.source_fair_id}
              onChange={(fairId) =>
                setValues((prev) => ({ ...prev, source_fair_id: fairId }))
              }
              placeholder={todoLabels.fieldSourceFairPlaceholder}
              allowClear
            />
          ) : (
            <FieldError>{todoLabels.fairReadPermissionRequired}</FieldError>
          )}
        </FormField>
        <FormField label={todoLabels.fieldAssignee} htmlFor="todo-assignee" fullWidth>
          <TextInput
            id="todo-assignee"
            value={values.assignee_user_id}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, assignee_user_id: event.target.value }))
            }
            placeholder="00000000-0000-0000-0000-000000000000"
          />
        </FormField>
        {canManageSteps ? (
          <TodoStepFieldList
            items={values.steps}
            onChange={(steps) => setValues((prev) => ({ ...prev, steps }))}
          />
        ) : null}
        {error ? <FieldError className="span-2">{error}</FieldError> : null}
      </FormGrid>
    </form>
  );
}
