import React from "react";
import {
  applyImportBatch,
  ApiError,
  getImportBatch,
  listImportRows,
  setImportRowDecision,
  uploadCustomerImport,
} from "../api/imports";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { DataTable } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/EmptyState";
import { LoadingState, TableSkeleton } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/Badge";
import {
  importBatchStatusLabels,
  importDecisionLabels,
  importLabels,
  importRowStatusLabels,
} from "../labels/importLabels";
import { labels } from "../labels";
import type { ApplyImportResponse, ImportBatch, ImportDecision, ImportRow } from "../types/import";
import { importBatchStatusBadgeVariant, importRowStatusBadgeVariant } from "../utils/importBadges";

function contactName(row: ImportRow): string {
  const first = row.normalized_data_json.contact_first_name;
  const last = row.normalized_data_json.contact_last_name;
  if (first || last) {
    return [first, last].filter(Boolean).join(" ");
  }
  return "—";
}

function str(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export function ImportsPage() {
  const [batch, setBatch] = React.useState<ImportBatch | null>(null);
  const [rows, setRows] = React.useState<ImportRow[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [applying, setApplying] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [confirmApply, setConfirmApply] = React.useState(false);
  const [applyResult, setApplyResult] = React.useState<ApplyImportResponse | null>(null);
  const [decisionLoadingId, setDecisionLoadingId] = React.useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const loadBatchData = React.useCallback(async (batchId: string) => {
    setLoading(true);
    setError(null);
    try {
      const [batchData, rowsData] = await Promise.all([
        getImportBatch(batchId),
        listImportRows(batchId),
      ]);
      setBatch(batchData);
      setRows(rowsData.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.loadError);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleUpload = async () => {
    if (!selectedFile) return;
    if (!selectedFile.name.toLowerCase().endsWith(".xlsx")) {
      setError(importLabels.uploadHint);
      return;
    }
    setUploading(true);
    setError(null);
    setSuccess(null);
    setApplyResult(null);
    try {
      const uploaded = await uploadCustomerImport(selectedFile);
      setBatch(uploaded);
      await loadBatchData(uploaded.id);
      setSuccess(`${uploaded.file_name} yüklendi.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.uploadError);
    } finally {
      setUploading(false);
    }
  };

  const handleDecisionChange = async (row: ImportRow, decision: ImportDecision) => {
    if (!batch) return;
    setDecisionLoadingId(row.id);
    setError(null);
    try {
      const updated = await setImportRowDecision(batch.id, row.id, {
        decision,
        match_customer_id: row.match_customer_id ?? undefined,
      });
      setRows((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      const refreshed = await getImportBatch(batch.id);
      setBatch(refreshed);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.decisionError);
    } finally {
      setDecisionLoadingId(null);
    }
  };

  const handleApply = async () => {
    if (!batch) return;
    setApplying(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await applyImportBatch(batch.id);
      setApplyResult(result);
      setBatch(result.batch);
      await loadBatchData(batch.id);
      setSuccess(importLabels.applySuccess);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.applyError);
    } finally {
      setApplying(false);
      setConfirmApply(false);
    }
  };

  const canApply = batch && batch.status !== "applied";
  const skipCount = rows.filter((row) => row.decision === "skip").length;

  return (
    <div className="page">
      <PageHeader title={importLabels.imports} subtitle={batch ? batch.file_name : undefined} />

      <Card>
        <h3 className="section-title">{importLabels.uploadTitle}</h3>
        <div className="filters">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx"
            className="search-input"
            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
            aria-label={importLabels.selectFile}
          />
          <button
            type="button"
            className="btn primary"
            disabled={!selectedFile || uploading}
            onClick={() => void handleUpload()}
          >
            {uploading ? labels.loading : importLabels.upload}
          </button>
        </div>
        <p className="field-hint">{importLabels.uploadHint}</p>
      </Card>

      {error && <div className="banner error">{error}</div>}
      {success && <div className="banner success">{success}</div>}

      {batch && (
        <>
          <Card>
            <h3 className="section-title">{importLabels.previewTitle}</h3>
            <div className="import-summary">
              <div>
                <span>{importLabels.summaryTotal}</span>
                <strong>{batch.total_rows}</strong>
              </div>
              <div>
                <span>{importLabels.summaryValid}</span>
                <strong>{batch.valid_rows}</strong>
              </div>
              <div>
                <span>{importLabels.summaryInvalid}</span>
                <strong>{batch.invalid_rows}</strong>
              </div>
              <div>
                <span>{importLabels.summaryDuplicate}</span>
                <strong>{batch.duplicate_rows}</strong>
              </div>
              <div>
                <span>{importLabels.summaryCreate}</span>
                <strong>{batch.ready_to_create}</strong>
              </div>
              <div>
                <span>{importLabels.summaryUpdate}</span>
                <strong>{batch.ready_to_update}</strong>
              </div>
              <div>
                <span>{importLabels.summarySkip}</span>
                <strong>{skipCount}</strong>
              </div>
            </div>
            <div className="filters">
              <Badge variant={importBatchStatusBadgeVariant(batch.status)}>
                {importBatchStatusLabels[batch.status] ?? batch.status}
              </Badge>
              {canApply && (
                <button
                  type="button"
                  className="btn primary"
                  disabled={applying}
                  onClick={() => setConfirmApply(true)}
                >
                  {importLabels.apply}
                </button>
              )}
            </div>
          </Card>

          {applyResult && (
            <Card>
              <div className="import-summary">
                <div>
                  <span>{importLabels.resultCreated}</span>
                  <strong>{applyResult.created_rows}</strong>
                </div>
                <div>
                  <span>{importLabels.resultUpdated}</span>
                  <strong>{applyResult.updated_rows}</strong>
                </div>
                <div>
                  <span>{importLabels.resultSkipped}</span>
                  <strong>{applyResult.skipped_rows}</strong>
                </div>
                <div>
                  <span>{importLabels.resultInvalid}</span>
                  <strong>{applyResult.invalid_rows}</strong>
                </div>
              </div>
            </Card>
          )}

          {loading ? (
            <TableSkeleton rows={5} cols={10} />
          ) : rows.length === 0 ? (
            <EmptyState
              title={importLabels.emptyTitle}
              description={importLabels.emptyDescription}
            />
          ) : (
            <Card padding="none">
              <DataTable>
                <thead>
                  <tr>
                    <th>{importLabels.colRow}</th>
                    <th>{importLabels.colCompany}</th>
                    <th>{importLabels.colEmail}</th>
                    <th>{importLabels.colPhone}</th>
                    <th>{importLabels.colContact}</th>
                    <th>{importLabels.colStatus}</th>
                    <th>{importLabels.colMatch}</th>
                    <th>{importLabels.colConfidence}</th>
                    <th>{importLabels.colDecision}</th>
                    <th>{importLabels.colErrors}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.id}>
                      <td>{row.row_number}</td>
                      <td>{str(row.normalized_data_json.company_name)}</td>
                      <td>{str(row.normalized_data_json.email)}</td>
                      <td>{str(row.normalized_data_json.phone ?? row.normalized_data_json.mobile_phone)}</td>
                      <td>{contactName(row)}</td>
                      <td>
                        <Badge variant={importRowStatusBadgeVariant(row.status)}>
                          {importRowStatusLabels[row.status] ?? row.status}
                        </Badge>
                      </td>
                      <td>{row.match_customer_name ?? "—"}</td>
                      <td>{row.match_confidence ?? "—"}</td>
                      <td>
                        {batch.status === "applied" ? (
                          row.decision ? importDecisionLabels[row.decision] : "—"
                        ) : (
                          <select
                            className="search-input"
                            value={row.decision ?? ""}
                            disabled={decisionLoadingId === row.id}
                            onChange={(e) => {
                              const value = e.target.value as ImportDecision;
                              if (value) void handleDecisionChange(row, value);
                            }}
                          >
                            <option value="">—</option>
                            {row.status !== "invalid" && (
                              <>
                                <option value="create_new">{importLabels.decisionCreateNew}</option>
                                {(row.match_customer_id || row.status === "possible_duplicate") && (
                                  <option value="update_existing">
                                    {importLabels.decisionUpdateExisting}
                                  </option>
                                )}
                              </>
                            )}
                            <option value="skip">{importLabels.decisionSkip}</option>
                          </select>
                        )}
                      </td>
                      <td>
                        {row.validation_errors_json?.length
                          ? row.validation_errors_json.join("; ")
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </DataTable>
            </Card>
          )}
        </>
      )}

      {!batch && !loading && (
        <EmptyState title={importLabels.emptyTitle} description={importLabels.emptyDescription} />
      )}

      {uploading && <LoadingState message={labels.loading} variant="overlay" />}

      {confirmApply && (
        <ConfirmDialog
          title={importLabels.applyConfirmTitle}
          message={importLabels.applyConfirmMessage}
          confirmLabel={importLabels.apply}
          loading={applying}
          onConfirm={() => void handleApply()}
          onCancel={() => setConfirmApply(false)}
        />
      )}
    </div>
  );
}
