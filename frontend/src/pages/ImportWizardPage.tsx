import React from "react";
import {
  analyzeImportBatch,
  ApiError,
  applyImportBatch,
  bulkRowDecision,
  getImportBatch,
  listImportRows,
  setColumnMapping,
  setImportRowDecision,
  uploadRawImport,
} from "../api/imports";
import { getFair, listFairs } from "../api/fairs";
import { listParticipantsByFair } from "../api/participations";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { DataTableShell } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/EmptyState";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { ServerDataTableFrame } from "../components/ui/ServerDataTableFrame";
import { Badge } from "../components/ui/Badge";
import { useServerDataTable } from "../hooks/useServerDataTable";
import {
  importBatchStatusLabels,
  importDecisionLabels,
  importLabels,
  importRowStatusLabels,
  WIZARD_STEPS,
  type WizardStepId,
} from "../labels/importLabels";
import type {
  ApplyImportResponse,
  BulkDecisionAction,
  ColumnMappingPayload,
  ImportBatch,
  ImportDecision,
  ImportRow,
  PreviewFilter,
  PreviewSortBy,
  UploadRawImportResponse,
} from "../types/import";
import { WIZARD_MAPPING_FIELDS as MAPPING_FIELDS } from "../types/import";
import type { Fair } from "../types/fair";
import { importBatchStatusBadgeVariant, importRowStatusBadgeVariant } from "../utils/importBadges";
import { MergeDiffViewer } from "../components/imports/MergeDiffViewer";

interface ImportWizardPageProps {
  preselectedFairId?: string;
}

function str(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

export function ImportWizardPage({ preselectedFairId }: ImportWizardPageProps) {
  const [stepIndex, setStepIndex] = React.useState(0);
  const [batchId, setBatchId] = React.useState<string | null>(null);
  const [batch, setBatch] = React.useState<ImportBatch | null>(null);
  const [uploadPreview, setUploadPreview] = React.useState<UploadRawImportResponse | null>(null);
  const [fairs, setFairs] = React.useState<Fair[]>([]);
  const [selectedFairId, setSelectedFairId] = React.useState<string>(preselectedFairId ?? "");
  const [selectedFair, setSelectedFair] = React.useState<Fair | null>(null);
  const [participantCount, setParticipantCount] = React.useState<number | null>(null);
  const [hasHeaderRow, setHasHeaderRow] = React.useState(true);
  const [mappings, setMappings] = React.useState<Record<string, number>>({});
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [confirmApply, setConfirmApply] = React.useState(false);
  const [applyResult, setApplyResult] = React.useState<ApplyImportResponse | null>(null);
  const fileRef = React.useRef<HTMLInputElement>(null);

  const currentStep = WIZARD_STEPS[stepIndex]?.id ?? "source";
  const isPreviewStep = currentStep === "preview" || currentStep === "decisions";

  const previewTable = useServerDataTable<ImportRow>({
    fetchFn: (params) => listImportRows(batchId!, params),
    defaultSort: { field: "company_name", direction: "asc" },
    filterKeys: ["filter"],
    enabled: Boolean(batchId) && isPreviewStep,
  });

  const loadFairs = React.useCallback(async () => {
    try {
      const res = await listFairs({ page: 1, page_size: 100, status: "active" });
      setFairs(res.items);
    } catch {
      /* best effort */
    }
  }, []);

  const loadFairDetails = React.useCallback(async (fairId: string) => {
    try {
      const fair = await getFair(fairId);
      setSelectedFair(fair);
      const parts = await listParticipantsByFair(fairId, { page: 1, pageSize: 1 });
      setParticipantCount(parts.pagination.totalItems);
    } catch {
      setSelectedFair(null);
    }
  }, []);

  React.useEffect(() => {
    void loadFairs();
  }, [loadFairs]);

  React.useEffect(() => {
    if (preselectedFairId) {
      setSelectedFairId(preselectedFairId);
      void loadFairDetails(preselectedFairId);
      if (stepIndex < 2) setStepIndex(1);
    }
  }, [preselectedFairId, loadFairDetails, stepIndex]);

  React.useEffect(() => {
    if (selectedFairId) void loadFairDetails(selectedFairId);
  }, [selectedFairId, loadFairDetails]);

  const refreshBatch = async (id: string) => {
    const b = await getImportBatch(id);
    setBatch(b);
  };

  const handleUpload = async () => {
    if (!selectedFile || !selectedFairId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await uploadRawImport(selectedFairId, selectedFile);
      setBatchId(result.batch_id);
      setUploadPreview(result);
      setHasHeaderRow(result.suggested_mapping.has_header_row);
      const initial: Record<string, number> = {};
      for (const [k, v] of Object.entries(result.suggested_mapping.mappings)) {
        initial[k] = v.value;
      }
      setMappings(initial);
      setStepIndex(3);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.uploadError);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveMapping = async () => {
    if (!batchId || mappings.company_name === undefined) {
      setError("Firma Adı eşleştirmesi zorunludur.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const payload = {
        has_header_row: hasHeaderRow,
        mappings: Object.fromEntries(
          Object.entries(mappings).map(([k, v]) => [k, { type: "column_index" as const, value: v }]),
        ),
      };
      await setColumnMapping(batchId, payload);
      setStepIndex(4);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.loadError);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!batchId) return;
    setLoading(true);
    setError(null);
    try {
      await analyzeImportBatch(batchId);
      await refreshBatch(batchId);
      setStepIndex(5);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.loadError);
    } finally {
      setLoading(false);
    }
  };

  const handleDecision = async (row: ImportRow, decision: ImportDecision) => {
    if (!batchId) return;
    try {
      await setImportRowDecision(batchId, row.id, { decision });
      await previewTable.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.decisionError);
    }
  };

  const previewFilter = (previewTable.filters.filter as PreviewFilter | undefined) || "all";

  const renderPreviewControls = () => (
    <div className="preview-controls">
      <div className="preview-filters">
        {(
          [
            ["all", importLabels.previewFilterAll],
            ["new", importLabels.previewFilterNew],
            ["will_update", importLabels.previewFilterUpdate],
            ["duplicate", importLabels.previewFilterDuplicate],
            ["invalid", importLabels.previewFilterInvalid],
            ["skip", importLabels.previewFilterSkip],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={`btn btn-sm ${previewFilter === key ? "btn-primary" : "btn-secondary"}`}
            onClick={() => previewTable.setFilter("filter", key === "all" ? "" : key)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="preview-search-sort">
        <input
          type="search"
          className="form-input"
          placeholder={importLabels.previewSearch}
          value={previewTable.search}
          onChange={(e) => previewTable.setSearch(e.target.value)}
        />
        <select
          className="form-select"
          value={previewTable.sorting.field || "company_name"}
          onChange={(e) =>
            previewTable.setSorting(e.target.value as PreviewSortBy, previewTable.sorting.direction)
          }
        >
          <option value="confidence">{importLabels.previewSortConfidence}</option>
          <option value="company_name">{importLabels.previewSortCompany}</option>
          <option value="status">{importLabels.previewSortStatus}</option>
        </select>
        <select
          className="form-select"
          value={previewTable.sorting.direction}
          onChange={(e) =>
            previewTable.setSorting(
              previewTable.sorting.field || "company_name",
              e.target.value as "asc" | "desc",
            )
          }
        >
          <option value="asc">Artan</option>
          <option value="desc">Azalan</option>
        </select>
      </div>
    </div>
  );

  const renderMergePreviewList = (editable: boolean) => (
    <div className="merge-preview-list">
      {previewTable.items.length === 0 && !previewTable.loading ? (
        <EmptyState title="Satır yok" description="Filtreye uygun satır bulunamadı." />
      ) : (
        previewTable.items.map((row) => (
          <div key={row.id} className="merge-preview-item">
            <div className="merge-preview-meta">
              <span>#{row.row_number}</span>
              <Badge variant={importRowStatusBadgeVariant(row.status)}>
                {importRowStatusLabels[row.status] ?? row.status}
              </Badge>
              {row.match_confidence != null && (
                <span className="text-muted">Güven: {row.match_confidence}%</span>
              )}
              {editable && (
                <select
                  className="form-select merge-decision-select"
                  value={row.decision ?? ""}
                  onChange={(e) => void handleDecision(row, e.target.value as ImportDecision)}
                >
                  <option value="">—</option>
                  {Object.entries(importDecisionLabels).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              )}
            </div>
            <MergeDiffViewer row={row} />
            {row.validation_errors_json?.length ? (
              <p className="form-error">{row.validation_errors_json.join("; ")}</p>
            ) : null}
          </div>
        ))
      )}
    </div>
  );

  const handleBulk = async (action: BulkDecisionAction) => {
    if (!batchId) return;
    setLoading(true);
    try {
      await bulkRowDecision(batchId, action);
      await previewTable.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.decisionError);
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    if (!batchId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await applyImportBatch(batchId);
      setApplyResult(result);
      setBatch(result.batch);
      setStepIndex(8);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.applyError);
    } finally {
      setLoading(false);
      setConfirmApply(false);
    }
  };

  const columnOptions = uploadPreview?.raw_columns.map((col) => {
    const header =
      hasHeaderRow && uploadPreview.detected_headers[col.index]
        ? `${uploadPreview.detected_headers[col.index]} (${col.letter})`
        : `Kolon ${col.letter}`;
    return { index: col.index, label: header };
  }) ?? [];

  const renderStepper = () => (
    <div className="wizard-stepper">
      {WIZARD_STEPS.map((s, i) => (
        <span key={s.id} className={`wizard-step ${i === stepIndex ? "active" : i < stepIndex ? "done" : ""}`}>
          {i + 1}. {s.label}
        </span>
      ))}
    </div>
  );

  const renderSource = () => (
    <Card>
      <h3>{importLabels.sourceTitle}</h3>
      <div className="source-grid">
        <button type="button" className="source-card active" onClick={() => setStepIndex(1)}>
          <strong>{importLabels.sourceExcel}</strong>
          <Badge variant="success">Aktif</Badge>
        </button>
        {["PDF", "Scraper", "Veritabanı"].map((label) => (
          <div key={label} className="source-card disabled">
            <strong>{label}</strong>
            <Badge variant="neutral">{importLabels.sourceSoon}</Badge>
          </div>
        ))}
      </div>
    </Card>
  );

  const renderUpload = () => (
    <Card>
      <h3>{importLabels.uploadTitle}</h3>
      <p className="text-muted">{importLabels.uploadHint}</p>
      <input
        ref={fileRef}
        type="file"
        accept=".xlsx"
        hidden
        onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
      />
      <button type="button" className="btn btn-secondary" onClick={() => fileRef.current?.click()}>
        {importLabels.selectFile}
      </button>
      {selectedFile && <p>{selectedFile.name}</p>}
      {uploadPreview && (
        <DataTableShell>
          <table>
            <tbody>
              {uploadPreview.sample_rows.slice(0, 5).map((row, ri) => (
                <tr key={ri}>
                  {(row as unknown[]).map((cell, ci) => (
                    <td key={ci}>{str(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </DataTableShell>
      )}
    </Card>
  );

  const renderFair = () => (
    <Card>
      <h3>{importLabels.fairTitle}</h3>
      <p className="text-muted">{importLabels.fairSubtitle}</p>
      {preselectedFairId && selectedFair ? (
        <div className="fair-info-card">
          <strong>{selectedFair.name}</strong>
          <div>{selectedFair.start_date} – {selectedFair.end_date}</div>
          <div>{selectedFair.location ?? "—"}</div>
          <div>{importLabels.fairParticipants}: {participantCount ?? "—"}</div>
        </div>
      ) : (
        <select
          value={selectedFairId}
          onChange={(e) => setSelectedFairId(e.target.value)}
          className="form-select"
        >
          <option value="">{importLabels.fairSelect}</option>
          {fairs.map((f) => (
            <option key={f.id} value={f.id}>{f.name}</option>
          ))}
        </select>
      )}
      {selectedFair && !preselectedFairId && (
        <div className="fair-info-card">
          <strong>{selectedFair.name}</strong>
          <div>{selectedFair.location ?? "—"}</div>
          <div>{importLabels.fairParticipants}: {participantCount ?? "—"}</div>
        </div>
      )}
    </Card>
  );

  const renderMapping = () => (
    <Card>
      <h3>{importLabels.mappingTitle}</h3>
      <p className="text-muted">{importLabels.mappingSubtitle}</p>
      <div className="header-toggle">
        <label>
          <input type="radio" checked={hasHeaderRow} onChange={() => setHasHeaderRow(true)} />
          {importLabels.headerYes}
        </label>
        <label>
          <input type="radio" checked={!hasHeaderRow} onChange={() => setHasHeaderRow(false)} />
          {importLabels.headerNo}
        </label>
      </div>
      <DataTableShell>
        <table>
          <thead>
            <tr>
              <th>CRM Alanı</th>
              <th>Kaynak Kolonu</th>
            </tr>
          </thead>
          <tbody>
            {MAPPING_FIELDS.map((field) => (
              <tr key={field.key}>
                <td>
                  {field.label}
                  {field.required && " *"}
                </td>
                <td>
                  <select
                    value={mappings[field.key] ?? ""}
                    onChange={(e) => {
                      const val = e.target.value;
                      setMappings((prev) => {
                        const next = { ...prev };
                        if (val === "") delete next[field.key];
                        else next[field.key] = Number(val);
                        return next;
                      });
                    }}
                  >
                    <option value="">{importLabels.noMapping}</option>
                    {columnOptions.map((opt) => (
                      <option key={opt.index} value={opt.index}>{opt.label}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </DataTableShell>
    </Card>
  );

  const renderAnalyze = () => (
    <Card>
      <h3>{importLabels.analyzeTitle}</h3>
      {batch && (
        <p>
          {batch.total_rows} satır · Durum:{" "}
          <Badge variant={importBatchStatusBadgeVariant(batch.status)}>
            {importBatchStatusLabels[batch.status] ?? batch.status}
          </Badge>
        </p>
      )}
      <button type="button" className="btn btn-primary" disabled={loading} onClick={() => void handleAnalyze()}>
        {loading ? importLabels.analyzeRunning : importLabels.analyzeRun}
      </button>
    </Card>
  );

  const renderPreview = () => (
    <Card>
      <h3>{importLabels.previewTitle}</h3>
      {selectedFair && <p>Hedef fuar: <strong>{selectedFair.name}</strong></p>}
      {renderPreviewControls()}
      {!batchId ? (
        <EmptyState title="Satır yok" description="Önce analiz çalıştırın." />
      ) : (
        <>
          <ServerDataTableFrame table={previewTable} skeletonRows={3}>
            {renderMergePreviewList(false)}
          </ServerDataTableFrame>
        </>
      )}
    </Card>
  );

  const renderDecisions = () => (
    <Card>
      <h3>{importLabels.decisionsTitle}</h3>
      <div className="bulk-actions">
        <button type="button" className="btn btn-secondary" onClick={() => void handleBulk("create_all_new")}>
          {importLabels.bulkCreateNew}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => void handleBulk("link_all_existing")}>
          {importLabels.bulkLinkExisting}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => void handleBulk("update_all_duplicates")}>
          {importLabels.bulkUpdateDuplicates}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => void handleBulk("skip_invalid")}>
          {importLabels.bulkSkipInvalid}
        </button>
      </div>
      {renderPreviewControls()}
      <ServerDataTableFrame table={previewTable} skeletonRows={3}>
        {renderMergePreviewList(true)}
      </ServerDataTableFrame>
    </Card>
  );

  const renderApply = () => (
    <Card>
      <h3>{importLabels.applyTitle}</h3>
      {batch && (
        <ul>
          <li>Oluşturulacak: {batch.ready_to_create}</li>
          <li>Güncellenecek: {batch.ready_to_update}</li>
          <li>Atlanacak: {previewTable.items.filter((r) => r.decision === "skip").length}</li>
        </ul>
      )}
      <button type="button" className="btn btn-primary" onClick={() => setConfirmApply(true)}>
        {importLabels.applyConfirmTitle}
      </button>
    </Card>
  );

  const renderSummary = () => (
    <Card>
      <h3>{importLabels.summaryTitle}</h3>
      {applyResult && (
        <div className="import-summary">
          <div><strong>{importLabels.resultCreated}:</strong> {applyResult.created_rows}</div>
          <div><strong>{importLabels.resultUpdated}:</strong> {applyResult.updated_rows}</div>
          <div><strong>{importLabels.resultParticipationCreated}:</strong> {applyResult.created_participations}</div>
          <div><strong>{importLabels.resultParticipationUpdated}:</strong> {applyResult.updated_participations}</div>
          <div><strong>{importLabels.resultContacts}:</strong> {applyResult.created_contacts}</div>
          <div><strong>{importLabels.resultSkipped}:</strong> {applyResult.skipped_rows}</div>
          <div><strong>{importLabels.resultInvalid}:</strong> {applyResult.invalid_rows}</div>
        </div>
      )}
      <button
        type="button"
        className="btn btn-primary"
        onClick={() => {
          setStepIndex(0);
          setBatchId(null);
          setBatch(null);
          setUploadPreview(null);
          setApplyResult(null);
          setSelectedFile(null);
        }}
      >
        {importLabels.newImport}
      </button>
    </Card>
  );

  const stepContent: Record<WizardStepId, React.ReactNode> = {
    source: renderSource(),
    upload: renderUpload(),
    fair: renderFair(),
    mapping: renderMapping(),
    analyze: renderAnalyze(),
    preview: renderPreview(),
    decisions: renderDecisions(),
    apply: renderApply(),
    summary: renderSummary(),
  };

  const canNext = () => {
    if (currentStep === "fair") return !!selectedFairId;
    if (currentStep === "upload") return !!selectedFile;
    if (currentStep === "mapping") return mappings.company_name !== undefined;
    return true;
  };

  const handleNext = () => {
    if (currentStep === "upload" && selectedFile && selectedFairId) {
      void handleUpload();
      return;
    }
    if (currentStep === "mapping") {
      void handleSaveMapping();
      return;
    }
    if (currentStep === "analyze" && (batch?.total_rows ?? 0) > 0) {
      setStepIndex(5);
      return;
    }
    if (stepIndex < WIZARD_STEPS.length - 1) setStepIndex(stepIndex + 1);
  };

  return (
    <div className="import-wizard">
      <PageHeader title={importLabels.wizardTitle} subtitle={importLabels.wizardSubtitle} />
      {renderStepper()}
      {error && <p className="form-error">{error}</p>}
      {loading && currentStep !== "analyze" ? <LoadingState message="Yükleniyor…" /> : stepContent[currentStep]}
      <div className="wizard-nav">
        <button
          type="button"
          className="btn btn-secondary"
          disabled={stepIndex === 0 || currentStep === "summary"}
          onClick={() => setStepIndex(Math.max(0, stepIndex - 1))}
        >
          {importLabels.back}
        </button>
        {currentStep !== "summary" && currentStep !== "apply" && (
          <button
            type="button"
            className="btn btn-primary"
            disabled={!canNext() || loading}
            onClick={handleNext}
          >
            {importLabels.next}
          </button>
        )}
        {currentStep === "apply" && null}
      </div>
      <ConfirmDialog
        open={confirmApply}
        title={importLabels.applyConfirmTitle}
        message={importLabels.applyConfirmMessage}
        confirmLabel={importLabels.applyConfirmTitle}
        onConfirm={() => void handleApply()}
        onCancel={() => setConfirmApply(false)}
      />
    </div>
  );
}
