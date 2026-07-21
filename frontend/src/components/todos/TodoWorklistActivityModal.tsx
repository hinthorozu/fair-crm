import React from "react";
import { localDatetimeToIso } from "../ActivityForm";
import { Badge } from "../ui/Badge";
import { DetailEmail, DetailPhone, detailText } from "../ui/DetailFields";
import {
  CheckboxField,
  FormField,
  FormGrid,
  FormSection,
  SelectInput,
  TextareaInput,
  TextInput,
} from "../ui/form";
import { FormModal } from "../ui/form/FormModal";
import { LoadingState } from "../ui/LoadingState";
import { useModalFormCancel, useReportFormDirty } from "../../hooks/useModalForm";
import { todoLabels } from "../../labels/todoLabels";
import {
  todoWorklistLabels,
  worklistStatusBadgeVariant,
  worklistStatusLabels,
} from "../../labels/todoWorklistLabels";
import type {
  RecordTodoWorklistActivityPayload,
  TodoWorklistModalActivity,
  TodoWorklistModalContext,
} from "../../types/todoWorklist";
import { ManualTaskMailModal } from "./ManualTaskMailModal";
import { Banner } from "../ui/Banner";

const EMPTY_FORM = {
  outcomeId: "",
  note: "",
  followUpAt: "",
  actionRequired: false,
  dataProblem: false,
};

const RECENT_ACTIVITY_LIMIT = 3;

interface TodoWorklistActivityModalProps {
  open: boolean;
  context: TodoWorklistModalContext | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (payload: RecordTodoWorklistActivityPayload) => Promise<void>;
}

function formatWorklistDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("tr-TR");
}

function RecentActivitiesSection({ activities }: { activities: TodoWorklistModalActivity[] }) {
  if (activities.length === 0) {
    return null;
  }

  const visible = activities.slice(0, RECENT_ACTIVITY_LIMIT);
  const overflowCount = activities.length - visible.length;

  return (
    <FormSection title={todoWorklistLabels.recentActivities}>
      <ul className="todo-worklist-recent-compact">
        {visible.map((activity) => (
          <li key={activity.id} className="todo-worklist-recent-item">
            <time className="todo-worklist-recent-date" dateTime={activity.activity_date}>
              {formatWorklistDateTime(activity.activity_date)}
            </time>
            <div className="todo-worklist-recent-body">
              <span className="todo-worklist-recent-subject">{activity.subject}</span>
              {activity.description ? (
                <span className="todo-worklist-recent-description">{activity.description}</span>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
      {overflowCount > 0 ? (
        <p className="field-hint">
          {todoWorklistLabels.recentActivitiesOverflow.replace("{count}", String(overflowCount))}
        </p>
      ) : null}
    </FormSection>
  );
}

function CustomerSummarySection({ context }: { context: TodoWorklistModalContext }) {
  const location = [context.city, context.country].filter(Boolean).join(" / ");
  const status = context.worklist_row?.primary_status;

  return (
    <FormSection title={todoWorklistLabels.sectionCustomer}>
      <div className="todo-worklist-customer-summary">
        <div className="todo-worklist-customer-heading">
          <h4 className="todo-worklist-customer-name">{context.customer_name}</h4>
          {status ? (
            <Badge variant={worklistStatusBadgeVariant(status)}>
              {worklistStatusLabels[status]}
            </Badge>
          ) : null}
        </div>
        <dl className="detail-grid compact">
          <div>
            <dt>{todoWorklistLabels.colCityCountry}</dt>
            <dd>{detailText(location || null)}</dd>
          </div>
          <div>
            <dt>{todoWorklistLabels.colPhone}</dt>
            <dd>
              <DetailPhone value={context.phone_summary} />
            </dd>
          </div>
          <div>
            <dt>{todoWorklistLabels.colEmail}</dt>
            <dd>
              <DetailEmail value={context.email_summary} />
            </dd>
          </div>
        </dl>
      </div>
    </FormSection>
  );
}

export function TodoWorklistActivityModal({
  open,
  context,
  loading,
  saving,
  error,
  onClose,
  onSave,
}: TodoWorklistActivityModalProps) {
  const requestClose = useModalFormCancel(onClose);
  const [outcomeId, setOutcomeId] = React.useState("");
  const [note, setNote] = React.useState("");
  const [followUpAt, setFollowUpAt] = React.useState("");
  const [actionRequired, setActionRequired] = React.useState(false);
  const [dataProblem, setDataProblem] = React.useState(false);
  const [mailModalOpen, setMailModalOpen] = React.useState(false);
  const [mailSuccess, setMailSuccess] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!context) {
      setOutcomeId("");
      setNote("");
      setFollowUpAt("");
      setActionRequired(false);
      setDataProblem(false);
      setMailModalOpen(false);
      setMailSuccess(null);
      return;
    }
    setOutcomeId("");
    setNote("");
    setFollowUpAt("");
    setActionRequired(false);
    setDataProblem(false);
    setMailModalOpen(false);
    setMailSuccess(null);
  }, [context?.customer_id]);

  const formValues = React.useMemo(
    () => ({
      outcomeId,
      note,
      followUpAt,
      actionRequired,
      dataProblem,
    }),
    [outcomeId, note, followUpAt, actionRequired, dataProblem],
  );
  useReportFormDirty(formValues, EMPTY_FORM);

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

  const canSubmit = Boolean(outcomeId && note.trim()) && !saving;
  const modalTitle = context?.customer_name ?? todoWorklistLabels.activityPanelTitle;

  if (!open) return null;

  return (
    <>
      <FormModal title={modalTitle} onClose={requestClose} size="lg">
        {loading ? (
          <div className="todo-worklist-modal-loading">
            <LoadingState variant="inline" />
          </div>
        ) : !context ? (
          <>
            <Banner variant="error" className="form-form-alert">{error ?? todoWorklistLabels.loadError}</Banner>
            <div className="form-actions span-2">
              <button type="button" className="btn secondary" onClick={requestClose}>
                {todoLabels.cancel}
              </button>
            </div>
          </>
        ) : (
          <form
            className="todo-worklist-activity-form crm-form crm-form--standard"
            onSubmit={(event) => {
              event.preventDefault();
              void handleSubmit(false);
            }}
          >
            {error ? <Banner variant="error" className="form-form-alert">{error}</Banner> : null}
            {mailSuccess ? <Banner variant="success" className="form-form-alert">{mailSuccess}</Banner> : null}

            <CustomerSummarySection context={context} />
            <div className="todo-worklist-mail-action-row">
              <button
                type="button"
                className="btn secondary"
                onClick={() => setMailModalOpen(true)}
                disabled={saving}
              >
                {todoWorklistLabels.mailSendAction}
              </button>
            </div>
            <RecentActivitiesSection activities={context.recent_activities} />

            <FormSection title={todoWorklistLabels.sectionNewActivity}>
              <FormGrid>
                <FormField label={todoWorklistLabels.outcomeLabel} htmlFor="worklist-outcome" required fullWidth>
                  <SelectInput
                    id="worklist-outcome"
                    value={outcomeId}
                    onChange={(event) => handleOutcomeChange(event.target.value)}
                    disabled={saving}
                    required
                  >
                    <option value="">{todoWorklistLabels.outcomePlaceholder}</option>
                    {context.outcomes.map((outcome) => (
                      <option key={outcome.id} value={outcome.id}>
                        {outcome.name}
                      </option>
                    ))}
                  </SelectInput>
                </FormField>

                <FormField label={todoWorklistLabels.noteLabel} htmlFor="worklist-note" required fullWidth>
                  <TextareaInput
                    id="worklist-note"
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    placeholder={todoWorklistLabels.notePlaceholder}
                    rows={4}
                    disabled={saving}
                    required
                  />
                </FormField>

                <FormField label={todoWorklistLabels.followUpLabel} htmlFor="worklist-follow-up">
                  <TextInput
                    id="worklist-follow-up"
                    type="datetime-local"
                    value={followUpAt}
                    onChange={(event) => setFollowUpAt(event.target.value)}
                    disabled={saving}
                  />
                </FormField>
              </FormGrid>
            </FormSection>

            <FormSection title={todoWorklistLabels.sectionFlags}>
              <FormGrid>
                <CheckboxField
                  id="worklist-action-required"
                  label={todoWorklistLabels.actionRequiredLabel}
                  hint={todoWorklistLabels.actionRequiredHint}
                  checked={actionRequired}
                  disabled={saving}
                  onChange={setActionRequired}
                />
                <CheckboxField
                  id="worklist-data-problem"
                  label={todoWorklistLabels.dataProblemLabel}
                  hint={todoWorklistLabels.dataProblemHint}
                  checked={dataProblem}
                  disabled={saving}
                  onChange={setDataProblem}
                />
              </FormGrid>
            </FormSection>

            <div className="form-actions span-2 todo-worklist-modal-actions">
              <button type="button" className="btn secondary" onClick={requestClose} disabled={saving}>
                {todoLabels.cancel}
              </button>
              <button
                type="button"
                className="btn secondary"
                disabled={!canSubmit}
                onClick={() => void handleSubmit(true)}
              >
                {todoWorklistLabels.saveAndNext}
              </button>
              <button type="submit" className="btn primary" disabled={!canSubmit}>
                {saving ? todoWorklistLabels.saving : todoWorklistLabels.save}
              </button>
            </div>
          </form>
        )}
      </FormModal>

      {context ? (
        <ManualTaskMailModal
          open={mailModalOpen}
          todoId={context.todo_id}
          customerId={context.customer_id}
          customerName={context.customer_name}
          onClose={() => setMailModalOpen(false)}
          onQueued={(message) => setMailSuccess(message)}
        />
      ) : null}
    </>
  );
}

export { formatWorklistDateTime };
