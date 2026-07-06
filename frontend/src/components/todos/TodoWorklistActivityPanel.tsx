import React from "react";
import { isoToLocalDatetime, localDatetimeToIso } from "../ActivityForm";
import {
  FormActions,
  FormField,
  FormGrid,
  SelectInput,
  TextareaInput,
} from "../ui/form";
import { Card } from "../ui/Card";
import { todoWorklistLabels } from "../../labels/todoWorklistLabels";
import type {
  RecordTodoWorklistActivityPayload,
  TodoWorklistModalContext,
  TodoWorklistOutcomeOption,
} from "../../types/todoWorklist";

interface TodoWorklistActivityPanelProps {
  context: TodoWorklistModalContext | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  onSave: (payload: RecordTodoWorklistActivityPayload) => Promise<void>;
}

export function TodoWorklistActivityPanel({
  context,
  loading,
  saving,
  error,
  onSave,
}: TodoWorklistActivityPanelProps) {
  const [outcomeId, setOutcomeId] = React.useState("");
  const [note, setNote] = React.useState("");
  const [followUpAt, setFollowUpAt] = React.useState("");
  const [actionRequired, setActionRequired] = React.useState(false);
  const [dataProblem, setDataProblem] = React.useState(false);

  React.useEffect(() => {
    if (!context) {
      setOutcomeId("");
      setNote("");
      setFollowUpAt("");
      setActionRequired(false);
      setDataProblem(false);
      return;
    }
    setOutcomeId("");
    setNote("");
    setFollowUpAt("");
    setActionRequired(false);
    setDataProblem(false);
  }, [context?.customer_id]);

  const handleOutcomeChange = (value: string) => {
    setOutcomeId(value);
    const selected = context?.outcomes.find((item) => item.id === value);
    if (selected) {
      setActionRequired(selected.requires_action);
      setDataProblem(selected.marks_data_problem);
    }
  };

  const buildPayload = (): RecordTodoWorklistActivityPayload | null => {
    if (!outcomeId || !note.trim()) return null;
    return {
      outcome_id: outcomeId,
      note: note.trim(),
      follow_up_at: followUpAt ? localDatetimeToIso(followUpAt) : null,
      action_required: actionRequired,
      data_problem: dataProblem,
    };
  };

  const handleSubmit = async (advanceToNext: boolean) => {
    const payload = buildPayload();
    if (!payload) return;
    await onSave({ ...payload, advance_to_next: advanceToNext });
  };

  if (loading) {
    return (
      <Card className="todo-worklist-panel">
        <p>{todoWorklistLabels.loadError}</p>
      </Card>
    );
  }

  if (!context) {
    return (
      <Card className="todo-worklist-panel">
        <p className="muted">{todoWorklistLabels.selectCustomerHint}</p>
      </Card>
    );
  }

  return (
    <Card className="todo-worklist-panel">
      <h3>{todoWorklistLabels.activityPanelTitle}</h3>
      <p className="todo-worklist-panel-customer">
        <strong>{context.customer_name}</strong>
        {(context.city || context.country) && (
          <span className="muted">
            {" "}
            — {[context.city, context.country].filter(Boolean).join(" / ")}
          </span>
        )}
      </p>
      <dl className="todo-worklist-panel-summary">
        <div>
          <dt>{todoWorklistLabels.colPhone}</dt>
          <dd>{context.phone_summary || "—"}</dd>
        </div>
        <div>
          <dt>{todoWorklistLabels.colEmail}</dt>
          <dd>{context.email_summary || "—"}</dd>
        </div>
      </dl>

      {context.recent_activities.length > 0 && (
        <div className="todo-worklist-recent">
          <h4>{todoWorklistLabels.recentActivities}</h4>
          <ul>
            {context.recent_activities.map((activity) => (
              <li key={activity.id}>
                <strong>{activity.subject}</strong>
                {activity.description ? `: ${activity.description}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      <FormGrid columns={1}>
        <FormField label={todoWorklistLabels.outcomeLabel} required>
          <SelectInput
            value={outcomeId}
            onChange={(e) => handleOutcomeChange(e.target.value)}
            aria-label={todoWorklistLabels.outcomeLabel}
          >
            <option value="">{todoWorklistLabels.outcomePlaceholder}</option>
            {context.outcomes.map((outcome: TodoWorklistOutcomeOption) => (
              <option key={outcome.id} value={outcome.id}>
                {outcome.name}
              </option>
            ))}
          </SelectInput>
        </FormField>

        <FormField label={todoWorklistLabels.noteLabel} required>
          <TextareaInput
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={todoWorklistLabels.notePlaceholder}
            rows={4}
          />
        </FormField>

        <FormField label={todoWorklistLabels.followUpLabel}>
          <input
            type="datetime-local"
            className="input"
            value={followUpAt}
            onChange={(e) => setFollowUpAt(e.target.value)}
          />
        </FormField>

        <FormField label={todoWorklistLabels.actionRequiredLabel}>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={actionRequired}
              onChange={(e) => setActionRequired(e.target.checked)}
            />
            {todoWorklistLabels.actionRequiredLabel}
          </label>
        </FormField>
        <FormField label={todoWorklistLabels.dataProblemLabel}>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={dataProblem}
              onChange={(e) => setDataProblem(e.target.checked)}
            />
            {todoWorklistLabels.dataProblemLabel}
          </label>
        </FormField>
      </FormGrid>

      {error && <p className="form-error">{error}</p>}

      <FormActions>
        <button
          type="button"
          className="btn primary"
          disabled={saving || !outcomeId || !note.trim()}
          onClick={() => void handleSubmit(false)}
        >
          {todoWorklistLabels.save}
        </button>
        <button
          type="button"
          className="btn secondary"
          disabled={saving || !outcomeId || !note.trim()}
          onClick={() => void handleSubmit(true)}
        >
          {todoWorklistLabels.saveAndNext}
        </button>
      </FormActions>
    </Card>
  );
}

export function formatWorklistDateTime(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("tr-TR");
}
