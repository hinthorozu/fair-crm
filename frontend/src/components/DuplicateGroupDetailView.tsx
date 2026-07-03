import React from "react";
import type { DuplicateGroupCustomerDetail, DuplicateGroupMergePreview, DuplicateGroupParticipation } from "../types/dataOperations";
import { previewDuplicateGroupMerge, executeDuplicateGroupMerge, ApiError } from "../api/dataOperations";
import { customerStatusLabels } from "../labels";
import { customerStatusBadgeVariant } from "../utils/badges";
import type { CustomerStatus } from "../types/customer";
import { adminLabels } from "../labels/adminLabels";
import { Badge } from "./ui/Badge";
import { CopyableCustomerId } from "./duplicateMerge/CopyableCustomerId";
import { MergeSummaryPanel } from "./duplicateMerge/MergeSummaryPanel";
import { MergeCustomersConfirmModal } from "./duplicateMerge/MergeCustomersConfirmModal";
import { buildMergePreviewRequest } from "./duplicateMerge/mergePreviewRequest";
import {
  allCommunicationKeys,
  commSelectionKey,
  COMM_CHANNELS,
  countCustomerCommunicationSelections,
  countTotalParticipations,
  countUniqueFairs,
  createDefaultMergeSelectionState,
  getScalarFieldValue,
  sanitizeMergeSelectionState,
  SCALAR_FIELDS,
  type CommChannel,
  type CommSelectionKey,
  type ScalarFieldKey,
  winnerCommunicationKeys,
} from "./duplicateMerge/mergeSelectionState";

const PREVIEW_DEBOUNCE_MS = 400;

const SCALAR_FIELD_LABELS: Record<ScalarFieldKey, string> = {
  company_name: adminLabels.dataOpColCompanyName,
  legal_name: adminLabels.dataOpColLegalName,
  trade_name: adminLabels.dataOpColTradeName,
  city: adminLabels.dataOpColCity,
  country: adminLabels.dataOpColCountry,
};

const COMM_FIELD_LABELS: Record<CommChannel, string> = {
  email: adminLabels.dataOpColEmail,
  phone: adminLabels.dataOpColPhone,
  website: adminLabels.dataOpColWebsite,
};

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR");
}

function formatGroupByLabel(groupBy: string): string {
  if (groupBy === "company_name") return adminLabels.dataOpGroupByCompanyName;
  if (groupBy === "email") return adminLabels.dataOpGroupByEmail;
  if (groupBy === "website") return adminLabels.dataOpGroupByWebsite;
  if (groupBy === "phone") return adminLabels.dataOpGroupByPhone;
  return groupBy;
}

function pickSuggestedWinnerId(customers: DuplicateGroupCustomerDetail[]): string | null {
  if (customers.length === 0) return null;

  const sorted = [...customers].sort((a, b) => {
    const participationDiff = b.participations.length - a.participations.length;
    if (participationDiff !== 0) return participationDiff;

    const createdDiff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    if (createdDiff !== 0) return createdDiff;

    return a.id.localeCompare(b.id);
  });

  return sorted[0]?.id ?? null;
}

interface DuplicateGroupDetailViewProps {
  runId: string;
  groupKey: string;
  groupBy?: string;
  customers: DuplicateGroupCustomerDetail[];
  loading: boolean;
  error: string | null;
  onMergeSuccess?: (payload: { groupKey: string }) => void;
}

interface CustomerFieldProps {
  label: string;
  value: React.ReactNode;
}

function CustomerField({ label, value }: CustomerFieldProps) {
  return (
    <div className="duplicate-group-kv">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

interface ScalarMergeFieldProps {
  fieldKey: ScalarFieldKey;
  fieldLabel: string;
  customerId: string;
  selectedCustomerId: string;
  value: string | null;
  onSelect: (field: ScalarFieldKey, customerId: string) => void;
}

function ScalarMergeField({
  fieldKey,
  fieldLabel,
  customerId,
  selectedCustomerId,
  value,
  onSelect,
}: ScalarMergeFieldProps) {
  const selected = selectedCustomerId === customerId;
  const inputId = `merge-field-${fieldKey}-${customerId}`;

  return (
    <label
      htmlFor={inputId}
      className={`duplicate-group-merge-field${selected ? " is-selected" : ""}`}
    >
      <span className="duplicate-group-merge-field-control">
        <input
          id={inputId}
          type="radio"
          name={`merge-field-${fieldKey}`}
          className="duplicate-group-merge-field-radio"
          checked={selected}
          onChange={() => onSelect(fieldKey, customerId)}
        />
        <span className="duplicate-group-merge-field-label">{fieldLabel}</span>
      </span>
      <span className="duplicate-group-merge-field-value">{value ?? "—"}</span>
    </label>
  );
}

interface CommunicationMergeFieldProps {
  channel: CommChannel;
  fieldLabel: string;
  customer: DuplicateGroupCustomerDetail;
  selections: Set<CommSelectionKey>;
  onToggle: (key: CommSelectionKey, checked: boolean) => void;
}

function commItemValue(
  channel: CommChannel,
  item: DuplicateGroupCustomerDetail["emails"][number] | DuplicateGroupCustomerDetail["phones"][number] | DuplicateGroupCustomerDetail["websites"][number],
): string {
  if (channel === "email" && "email" in item) return item.email;
  if (channel === "phone" && "phone" in item) return item.phone;
  if ("website" in item) return item.website;
  return "";
}

function CommunicationMergeField({
  channel,
  fieldLabel,
  customer,
  selections,
  onToggle,
}: CommunicationMergeFieldProps) {
  const items =
    channel === "email"
      ? customer.emails
      : channel === "phone"
        ? customer.phones
        : customer.websites;

  return (
    <div className="duplicate-group-merge-field duplicate-group-merge-field-comm">
      <span className="duplicate-group-merge-field-label">{fieldLabel}</span>
      {items.length === 0 ? (
        <span className="duplicate-group-merge-field-value">—</span>
      ) : (
        <ul className="duplicate-group-comm-checklist">
          {items.map((item) => {
            const key = commSelectionKey(customer.id, item.id);
            const checked = selections.has(key);
            const inputId = `merge-comm-${channel}-${key}`;
            const value = commItemValue(channel, item);

            return (
              <li key={item.id}>
                <label htmlFor={inputId} className={`duplicate-group-comm-check${checked ? " is-selected" : ""}`}>
                  <input
                    id={inputId}
                    type="checkbox"
                    checked={checked}
                    onChange={(event) => onToggle(key, event.target.checked)}
                  />
                  <span className="duplicate-group-comm-check-value">{value}</span>
                  {item.is_primary && (
                    <span className="detail-primary-badge">{adminLabels.dataOpPrimary}</span>
                  )}
                </label>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function ParticipationRow({ participation }: { participation: DuplicateGroupParticipation }) {
  return (
    <li className="duplicate-group-participation-row">
      <span className="duplicate-group-participation-fair">{participation.fair_name}</span>
      <span className="duplicate-group-participation-meta">
        <span className="duplicate-group-participation-meta-item">
          <span className="duplicate-group-participation-meta-label">{adminLabels.dataOpColFairYear}</span>
          <span>{participation.fair_year ?? "—"}</span>
        </span>
        <span className="duplicate-group-participation-meta-item">
          <span className="duplicate-group-participation-meta-label">{adminLabels.dataOpColHall}</span>
          <span>{participation.hall ?? "—"}</span>
        </span>
        <span className="duplicate-group-participation-meta-item">
          <span className="duplicate-group-participation-meta-label">{adminLabels.dataOpColStand}</span>
          <span>{participation.stand ?? "—"}</span>
        </span>
      </span>
    </li>
  );
}

export function DuplicateGroupDetailView({
  runId,
  groupKey,
  groupBy,
  customers,
  loading,
  error,
  onMergeSuccess,
}: DuplicateGroupDetailViewProps) {
  const suggestedWinnerId = React.useMemo(() => pickSuggestedWinnerId(customers), [customers]);
  const uniqueFairs = React.useMemo(() => countUniqueFairs(customers), [customers]);
  const totalParticipations = React.useMemo(() => countTotalParticipations(customers), [customers]);

  const [mergeState, setMergeState] = React.useState(() =>
    createDefaultMergeSelectionState(customers, suggestedWinnerId ?? customers[0]?.id ?? ""),
  );
  const [expandedCustomerIds, setExpandedCustomerIds] = React.useState<Set<string>>(() => new Set());
  const [mergePreview, setMergePreview] = React.useState<DuplicateGroupMergePreview | null>(null);
  const [previewLoading, setPreviewLoading] = React.useState(false);
  const [previewError, setPreviewError] = React.useState<string | null>(null);
  const [mergeExecuting, setMergeExecuting] = React.useState(false);
  const [mergeConfirmOpen, setMergeConfirmOpen] = React.useState(false);
  const [mergeExecuteError, setMergeExecuteError] = React.useState<string | null>(null);
  const [mergeSuccessMessage, setMergeSuccessMessage] = React.useState<string | null>(null);
  const mergeCompletedRef = React.useRef(false);
  const mergeStateRef = React.useRef(mergeState);
  const previewRequestIdRef = React.useRef(0);
  const groupContextKeyRef = React.useRef(`${runId}:${groupKey}`);
  const hadCustomersRef = React.useRef(customers.length > 0);
  const [previewSelectionKey, setPreviewSelectionKey] = React.useState<string | null>(null);

  const groupContextKey = `${runId}:${groupKey}`;

  const mergeSelectionKey = React.useMemo(
    () =>
      JSON.stringify({
        survivingCustomerId: mergeState.survivingCustomerId,
        scalarSelections: mergeState.scalarSelections,
        communicationSelections: [...mergeState.communicationSelections].sort(),
      }),
    [mergeState],
  );

  React.useEffect(() => {
    mergeStateRef.current = mergeState;
  }, [mergeState]);

  React.useEffect(() => {
    const contextChanged = groupContextKeyRef.current !== groupContextKey;
    groupContextKeyRef.current = groupContextKey;
    const customersBecameAvailable = !hadCustomersRef.current && customers.length > 0;
    hadCustomersRef.current = customers.length > 0;

    const resetPreviewState = () => {
      mergeCompletedRef.current = false;
      setMergeConfirmOpen(false);
      setMergePreview(null);
      setPreviewError(null);
      setPreviewLoading(false);
      setPreviewSelectionKey(null);
      setMergeExecuting(false);
      setMergeExecuteError(null);
      setMergeSuccessMessage(null);
      previewRequestIdRef.current += 1;
    };

    if (customers.length === 0) {
      if (contextChanged) {
        setMergeState(createDefaultMergeSelectionState([], ""));
        setExpandedCustomerIds(new Set());
        resetPreviewState();
      }
      return;
    }

    const survivingCustomerId = suggestedWinnerId ?? customers[0]?.id ?? "";

    if (contextChanged || customersBecameAvailable) {
      setMergeState(createDefaultMergeSelectionState(customers, survivingCustomerId));
      setExpandedCustomerIds(survivingCustomerId ? new Set([survivingCustomerId]) : new Set());
      resetPreviewState();
      return;
    }

    setMergeState((current) => sanitizeMergeSelectionState(customers, current));
  }, [groupContextKey, suggestedWinnerId, customers]);

  React.useEffect(() => {
    if (!runId || !groupKey || customers.length === 0 || mergeExecuting) {
      return;
    }

    const selectionKeyAtRequest = mergeSelectionKey;
    const customersForRequest = customers;
    const timer = window.setTimeout(() => {
      const requestId = ++previewRequestIdRef.current;
      setPreviewLoading(true);
      setPreviewError(null);

      const requestState = sanitizeMergeSelectionState(customersForRequest, mergeStateRef.current);

      void previewDuplicateGroupMerge(
        groupKey,
        buildMergePreviewRequest(runId, requestState, customersForRequest),
      )
        .then((preview) => {
          if (requestId !== previewRequestIdRef.current) {
            return;
          }
          setMergePreview(preview);
          setPreviewSelectionKey(selectionKeyAtRequest);
        })
        .catch((err) => {
          if (requestId !== previewRequestIdRef.current) {
            return;
          }
          setMergePreview(null);
          setPreviewSelectionKey(null);
          setPreviewError(err instanceof ApiError ? err.message : adminLabels.dataOpRunError);
        })
        .finally(() => {
          if (requestId !== previewRequestIdRef.current) {
            return;
          }
          setPreviewLoading(false);
        });
    }, PREVIEW_DEBOUNCE_MS);

    return () => {
      window.clearTimeout(timer);
    };
  }, [mergeSelectionKey, runId, groupKey, customers, mergeExecuting]);

  const survivingCustomer = customers.find((customer) => customer.id === mergeState.survivingCustomerId);
  const previewMatchesSelection = previewSelectionKey === mergeSelectionKey;

  const handleMergeRequest = React.useCallback(() => {
    if (mergeExecuting || mergeCompletedRef.current || !mergePreview?.is_valid || !previewMatchesSelection) {
      return;
    }
    setMergeConfirmOpen(true);
  }, [mergeExecuting, mergePreview?.is_valid, previewMatchesSelection]);

  const handleMergeExecute = React.useCallback(async () => {
    if (mergeExecuting || mergeCompletedRef.current || !mergePreview?.is_valid || !previewMatchesSelection) {
      return;
    }

    setMergeExecuting(true);
    setMergeExecuteError(null);
    setMergeSuccessMessage(null);

    try {
      const requestState = sanitizeMergeSelectionState(customers, mergeStateRef.current);
      const result = await executeDuplicateGroupMerge(
        groupKey,
        buildMergePreviewRequest(runId, requestState, customers),
      );
      const survivingId = result?.surviving_customer?.id;
      if (!survivingId) {
        throw new ApiError(adminLabels.dataOpMergeExecuteError, 500, result);
      }

      mergeCompletedRef.current = true;
      setMergeConfirmOpen(false);
      setMergeExecuteError(null);
      setMergeExecuting(false);

      if (onMergeSuccess) {
        onMergeSuccess({ groupKey });
        return;
      }

      setMergeSuccessMessage(adminLabels.dataOpMergeSuccess);
    } catch (err) {
      setMergeExecuteError(
        err instanceof ApiError ? err.message : adminLabels.dataOpMergeExecuteError,
      );
      setMergeExecuting(false);
    }
  }, [
    customers,
    groupKey,
    mergeExecuting,
    mergePreview?.is_valid,
    onMergeSuccess,
    previewMatchesSelection,
    runId,
  ]);

  const handleScalarSelect = React.useCallback((field: ScalarFieldKey, customerId: string) => {
    setMergeState((current) => ({
      ...current,
      scalarSelections: {
        ...current.scalarSelections,
        [field]: customerId,
      },
    }));
  }, []);

  const handleCommToggle = React.useCallback((key: CommSelectionKey, checked: boolean) => {
    setMergeState((current) => {
      const communicationSelections = new Set(current.communicationSelections);
      if (checked) {
        communicationSelections.add(key);
      } else {
        communicationSelections.delete(key);
      }
      return { ...current, communicationSelections };
    });
  }, []);

  const handleSelectAll = React.useCallback(
    (channel: CommChannel) => {
      setMergeState((current) => {
        const communicationSelections = new Set(current.communicationSelections);
        for (const key of allCommunicationKeys(customers, channel)) {
          communicationSelections.add(key);
        }
        return { ...current, communicationSelections };
      });
    },
    [customers],
  );

  const handleResetToWinner = React.useCallback(
    (channel: CommChannel) => {
      setMergeState((current) => {
        const communicationSelections = new Set(current.communicationSelections);
        for (const key of allCommunicationKeys(customers, channel)) {
          communicationSelections.delete(key);
        }
        for (const key of winnerCommunicationKeys(
          customers,
          channel,
          current.survivingCustomerId,
        )) {
          communicationSelections.add(key);
        }
        return { ...current, communicationSelections };
      });
    },
    [customers],
  );

  const handleExpandAll = React.useCallback(() => {
    setExpandedCustomerIds(new Set(customers.map((customer) => customer.id)));
  }, [customers]);

  const handleCollapseAll = React.useCallback(() => {
    setExpandedCustomerIds(
      suggestedWinnerId ? new Set([suggestedWinnerId]) : new Set(),
    );
  }, [suggestedWinnerId]);

  const toggleCustomerExpanded = React.useCallback((customerId: string) => {
    setExpandedCustomerIds((current) => {
      const next = new Set(current);
      if (next.has(customerId)) {
        next.delete(customerId);
      } else {
        next.add(customerId);
      }
      return next;
    });
  }, []);

  const handleSetSurvivingCustomer = React.useCallback((customerId: string) => {
    setMergeState((current) => ({
      ...current,
      survivingCustomerId: customerId,
    }));
    setExpandedCustomerIds((current) => new Set(current).add(customerId));
  }, []);

  if (error) {
    return <p className="text-danger">{error}</p>;
  }

  if (loading) {
    return <p className="text-muted">{adminLabels.dataOpLoading}</p>;
  }

  return (
    <div className="duplicate-group-detail">
      <div className="data-operation-summary-grid duplicate-group-summary-grid">
        <div className="data-operation-summary-card card">
          <p className="data-operation-summary-label">
            {adminLabels.dataOpColGroupKey}
            {groupBy ? ` (${formatGroupByLabel(groupBy)})` : ""}
          </p>
          <p className="data-operation-summary-value duplicate-group-summary-key">
            <code>{groupKey}</code>
          </p>
        </div>
        <div className="data-operation-summary-card card">
          <p className="data-operation-summary-label">{adminLabels.dataOpColCustomerCount}</p>
          <p className="data-operation-summary-value">{customers.length}</p>
        </div>
        <div className="data-operation-summary-card card">
          <p className="data-operation-summary-label">{adminLabels.dataOpSummaryTotalParticipationRows}</p>
          <p className="data-operation-summary-value">{totalParticipations}</p>
        </div>
        <div className="data-operation-summary-card card">
          <p className="data-operation-summary-label">{adminLabels.dataOpSummaryUniqueFairs}</p>
          <p className="data-operation-summary-value">{uniqueFairs}</p>
        </div>
        <div className="data-operation-summary-card card">
          <p className="data-operation-summary-label">{adminLabels.dataOpSummaryFairParticipations}</p>
          <p className="data-operation-summary-value">{totalParticipations}</p>
        </div>
      </div>

      <div className="banner info duplicate-group-merge-notice" role="status">
        {adminLabels.dataOpDuplicateGroupMergeNotice}
      </div>

      <div className="duplicate-group-detail-body">
        <div className="duplicate-group-detail-main">
          <div className="duplicate-group-merge-intro card">
            <h3 className="duplicate-group-merge-intro-title">{adminLabels.dataOpMergeSelectFieldsTitle}</h3>
            <p className="duplicate-group-merge-intro-hint text-muted">
              {adminLabels.dataOpMergeSelectFieldsHint}
            </p>
            <div className="duplicate-group-merge-intro-actions">
              <button type="button" className="btn link" onClick={handleExpandAll}>
                {adminLabels.dataOpExpandAll}
              </button>
              <span className="duplicate-group-intro-separator">|</span>
              <button type="button" className="btn link" onClick={handleCollapseAll}>
                {adminLabels.dataOpCollapseAll}
              </button>
            </div>
            <div className="duplicate-group-comm-bulk-actions">
              {COMM_CHANNELS.map((channel) => (
                <div key={channel} className="duplicate-group-comm-bulk-action">
                  <span className="duplicate-group-comm-bulk-label">{COMM_FIELD_LABELS[channel]}:</span>
                  <button
                    type="button"
                    className="btn link"
                    onClick={() => handleSelectAll(channel)}
                  >
                    {adminLabels.dataOpSelectAll}
                  </button>
                  <span className="duplicate-group-intro-separator">·</span>
                  <button
                    type="button"
                    className="btn link"
                    onClick={() => handleResetToWinner(channel)}
                  >
                    {adminLabels.dataOpResetToWinner}
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="duplicate-group-customers">
            {customers.map((customer, index) => {
              const isSuggestedWinner = customer.id === suggestedWinnerId;
              const isSurviving = customer.id === mergeState.survivingCustomerId;
              const isExpanded = expandedCustomerIds.has(customer.id);
              const selectedCommCount = countCustomerCommunicationSelections(
                customer,
                mergeState.communicationSelections,
              );

              return (
                <section
                  key={customer.id}
                  className={`card duplicate-group-customer-card${
                    isSuggestedWinner ? " duplicate-group-customer-card-winner" : ""
                  }${isExpanded ? " is-expanded" : " is-collapsed"}`}
                >
                  <div className="duplicate-group-customer-header">
                    <div className="duplicate-group-customer-header-main">
                      <span className="duplicate-group-customer-index">{index + 1}</span>
                      <h3 className="duplicate-group-customer-title">{customer.company_name}</h3>
                    </div>
                    <div className="duplicate-group-customer-header-actions">
                      <div className="duplicate-group-customer-badges">
                        <Badge variant={customerStatusBadgeVariant(customer.status as CustomerStatus)}>
                          {customerStatusLabels[customer.status as CustomerStatus] ?? customer.status}
                        </Badge>
                        {isSuggestedWinner && (
                          <Badge variant="success">
                            {adminLabels.dataOpDuplicateGroupSuggestedWinnerBadge}
                          </Badge>
                        )}
                        {isSurviving && (
                          <Badge variant="info">{adminLabels.dataOpSurvivingCustomer}</Badge>
                        )}
                      </div>
                      {!isSurviving && (
                        <button
                          type="button"
                          className="btn link"
                          onClick={() => handleSetSurvivingCustomer(customer.id)}
                        >
                          {adminLabels.dataOpSetAsSurviving}
                        </button>
                      )}
                      <button
                        type="button"
                        className="btn link duplicate-group-card-toggle"
                        onClick={() => toggleCustomerExpanded(customer.id)}
                        aria-expanded={isExpanded}
                      >
                        {isExpanded ? adminLabels.dataOpCollapseCard : adminLabels.dataOpExpandCard}
                      </button>
                    </div>
                  </div>

                  <div className="duplicate-group-customer-collapsed-meta">
                    <CopyableCustomerId value={customer.id} />
                    {!isExpanded && selectedCommCount > 0 && (
                      <span className="text-muted">
                        {adminLabels.dataOpSelectedCommunicationsCount}: {selectedCommCount}
                      </span>
                    )}
                  </div>

                  {isExpanded && (
                    <div className="duplicate-group-customer-body">
                      <div className="duplicate-group-merge-fields">
                        {SCALAR_FIELDS.map((field) => (
                          <ScalarMergeField
                            key={field.key}
                            fieldKey={field.key}
                            fieldLabel={SCALAR_FIELD_LABELS[field.key]}
                            customerId={customer.id}
                            selectedCustomerId={mergeState.scalarSelections[field.key]}
                            value={getScalarFieldValue(customer, field.key)}
                            onSelect={handleScalarSelect}
                          />
                        ))}
                        {COMM_CHANNELS.map((channel) => (
                          <CommunicationMergeField
                            key={channel}
                            channel={channel}
                            fieldLabel={COMM_FIELD_LABELS[channel]}
                            customer={customer}
                            selections={mergeState.communicationSelections}
                            onToggle={handleCommToggle}
                          />
                        ))}
                      </div>

                      <dl className="duplicate-group-readonly-grid">
                        <CustomerField
                          label={adminLabels.dataOpColCustomerId}
                          value={<CopyableCustomerId value={customer.id} />}
                        />
                        <CustomerField
                          label={adminLabels.dataOpColCreatedAt}
                          value={formatDateTime(customer.created_at)}
                        />
                      </dl>

                      <div className="duplicate-group-participations">
                        <p className="duplicate-group-participations-title">
                          {adminLabels.dataOpDuplicateGroupParticipations}
                        </p>
                        {customer.participations.length === 0 ? (
                          <p className="duplicate-group-empty-participations" role="status">
                            {adminLabels.dataOpDuplicateGroupNoParticipations}
                          </p>
                        ) : (
                          <ul className="duplicate-group-participation-list">
                            {customer.participations.map((participation, participationIndex) => (
                              <ParticipationRow
                                key={`${customer.id}-${participation.fair_name}-${participationIndex}`}
                                participation={participation}
                              />
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  )}
                </section>
              );
            })}
          </div>
        </div>

        <MergeSummaryPanel
          suggestedWinnerId={suggestedWinnerId}
          survivingCustomerId={mergeState.survivingCustomerId}
          survivingCustomerName={survivingCustomer?.company_name ?? "—"}
          survivingParticipationCount={survivingCustomer?.participations.length ?? 0}
          preview={mergePreview}
          previewLoading={previewLoading}
          previewMatchesSelection={previewMatchesSelection}
          previewError={previewError}
          mergeExecuting={mergeExecuting}
          mergeExecuteError={mergeExecuteError}
          mergeSuccessMessage={mergeSuccessMessage}
          onMergeExecute={handleMergeRequest}
        />
      </div>

      <MergeCustomersConfirmModal
        open={mergeConfirmOpen}
        preview={mergePreview?.is_valid && previewMatchesSelection ? mergePreview : null}
        groupCustomers={customers}
        merging={mergeExecuting}
        onClose={() => {
          if (!mergeExecuting) {
            setMergeConfirmOpen(false);
          }
        }}
        onConfirm={() => void handleMergeExecute()}
      />

      <div className="banner info duplicate-group-dedup-notice" role="status">
        {adminLabels.dataOpMergeDedupNotice}
      </div>
    </div>
  );
}
