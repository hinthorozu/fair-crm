import React from "react";
import type {
  DuplicateGroupCustomerDetail,
  DuplicateGroupMergePreview,
} from "../../types/dataOperations";
import { adminLabels } from "../../labels/adminLabels";
import { CopyableCustomerId } from "./CopyableCustomerId";

const SCALAR_FIELD_ROWS: Array<{
  key: keyof DuplicateGroupMergePreview["scalar_fields"];
  label: string;
}> = [
  { key: "company_name", label: adminLabels.dataOpColCompanyName },
  { key: "legal_name", label: adminLabels.dataOpColLegalName },
  { key: "trade_name", label: adminLabels.dataOpColTradeName },
  { key: "city", label: adminLabels.dataOpColCity },
  { key: "country", label: adminLabels.dataOpColCountry },
];

function CommunicationSection({
  title,
  items,
}: {
  title: string;
  items: DuplicateGroupMergePreview["emails"];
}) {
  return (
    <section className="duplicate-group-summary-section">
      <p className="duplicate-group-summary-section-label">
        {title} ({items.length})
      </p>
      {items.length === 0 ? (
        <p className="text-muted duplicate-group-summary-empty">—</p>
      ) : (
        <ul className="duplicate-group-summary-comm-list">
          {items.map((item) => (
            <li key={`${item.source_row_id}-${item.value}`}>
              <span className="duplicate-group-summary-check" aria-hidden="true">
                ✓
              </span>
              <span className="duplicate-group-summary-comm-value">{item.value}</span>
              {item.is_primary && (
                <span className="detail-primary-badge">{adminLabels.dataOpPrimary}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export interface MergePreviewSummaryContentProps {
  preview: DuplicateGroupMergePreview;
  groupCustomers?: DuplicateGroupCustomerDetail[];
  showCustomersToDelete?: boolean;
  showWarnings?: boolean;
  showSurvivingCustomer?: boolean;
}

export function MergePreviewSummaryContent({
  preview,
  groupCustomers = [],
  showCustomersToDelete = false,
  showWarnings = true,
  showSurvivingCustomer = true,
}: MergePreviewSummaryContentProps) {
  const customersById = React.useMemo(
    () => new Map(groupCustomers.map((customer) => [customer.id, customer])),
    [groupCustomers],
  );

  return (
    <>
      {showSurvivingCustomer && (
        <section className="duplicate-group-summary-section">
          <p className="duplicate-group-summary-section-label">{adminLabels.dataOpSurvivingCustomer}</p>
          <div className="duplicate-group-surviving-customer">
            <strong>{preview.merged_customer.display_name}</strong>
            <CopyableCustomerId value={preview.surviving_customer_id} />
          </div>
        </section>
      )}

      {showCustomersToDelete && (
        <section className="duplicate-group-summary-section">
          <p className="duplicate-group-summary-section-label">
            {adminLabels.dataOpMergeConfirmCustomersToDeleteList} ({preview.customers_to_archive.length})
          </p>
          {preview.customers_to_archive.length === 0 ? (
            <p className="text-muted duplicate-group-summary-empty">—</p>
          ) : (
            <ul className="duplicate-group-summary-comm-list">
              {preview.customers_to_archive.map((customerId) => {
                const customer = customersById.get(customerId);
                return (
                  <li key={customerId}>
                    <strong>{customer?.company_name ?? customerId}</strong>
                    <CopyableCustomerId value={customerId} />
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      )}

      <section className="duplicate-group-summary-section">
        <p className="duplicate-group-summary-section-label">{adminLabels.dataOpSummaryIdentityFields}</p>
        <dl className="duplicate-group-summary-identity-list">
          {SCALAR_FIELD_ROWS.map((field) => (
            <div key={field.key} className="duplicate-group-summary-identity-row">
              <dt>{field.label}</dt>
              <dd>
                <span>{preview.scalar_fields[field.key] ?? "—"}</span>
              </dd>
            </div>
          ))}
        </dl>
      </section>

      {showWarnings &&
        preview.warnings.map((warning, index) => (
          <div
            key={`${warning.code}-${index}`}
            className="banner warning duplicate-group-summary-banner"
            role="status"
          >
            {warning.message}
          </div>
        ))}

      <CommunicationSection title={adminLabels.dataOpSummarySelectedEmails} items={preview.emails} />
      <CommunicationSection title={adminLabels.dataOpSummarySelectedPhones} items={preview.phones} />
      <CommunicationSection title={adminLabels.dataOpSummarySelectedWebsites} items={preview.websites} />

      <section className="duplicate-group-summary-section">
        <p className="duplicate-group-summary-section-label">{adminLabels.dataOpSummaryParticipations}</p>
        <div className="duplicate-group-summary-participation-stats">
          <span>
            {adminLabels.dataOpSummaryTotalParticipationRows}:{" "}
            <strong>{preview.participation_summary.total_participation_rows}</strong>
          </span>
          <span>
            {adminLabels.dataOpSummaryUniqueFairs}:{" "}
            <strong>{preview.participation_summary.unique_fairs}</strong>
          </span>
        </div>
        {preview.participation_summary.fair_names.length > 0 && (
          <ul className="duplicate-group-summary-comm-list">
            {preview.participation_summary.fair_names.map((fairName) => (
              <li key={fairName}>{fairName}</li>
            ))}
          </ul>
        )}
        <p className="text-muted duplicate-group-summary-participation-note">
          {adminLabels.dataOpSummaryParticipationNote}
        </p>
      </section>

      <section className="duplicate-group-summary-section duplicate-group-summary-result">
        <p className="duplicate-group-summary-section-label">{adminLabels.dataOpSummaryMergeResult}</p>
        <ul className="duplicate-group-summary-result-list">
          <li>
            {adminLabels.dataOpColCustomerCount}: {preview.statistics.customers_before} →{" "}
            {preview.statistics.customers_after}
          </li>
          <li>
            {adminLabels.dataOpColEmail}: {preview.statistics.emails_before} →{" "}
            {preview.statistics.emails_after}
          </li>
          <li>
            {adminLabels.dataOpColPhone}: {preview.statistics.phones_before} →{" "}
            {preview.statistics.phones_after}
          </li>
          <li>
            {adminLabels.dataOpColWebsite}: {preview.statistics.websites_before} →{" "}
            {preview.statistics.websites_after}
          </li>
        </ul>
      </section>
    </>
  );
}
