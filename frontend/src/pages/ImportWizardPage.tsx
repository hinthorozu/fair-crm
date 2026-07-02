import React from "react";
import {
  ApiError,
  applyImportDecisions,
  bulkAssignRowDecisions,
  configureImportHeader,
  getImportBatch,
  listImportRows,
  setColumnMapping,
  setImportRowDecision,
  uploadRawImport,
  getMappingPreview,
  selectImportSheet,
} from "../api/dataIntegration";
import { getFair } from "../api/fairs";
import { FairEntitySelect } from "../components/FairEntitySelect";
import { listParticipantsByFair } from "../api/participations";
import { Card } from "../components/ui/Card";
import { DataTableShell } from "../components/ui/DataTable";
import { EmptyState } from "../components/ui/EmptyState";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { ServerDataTableFrame } from "../components/ui/ServerDataTableFrame";
import { Badge } from "../components/ui/Badge";
import { useServerDataTable, type ServerTableFetchParams } from "../hooks/useServerDataTable";
import { DEFAULT_PAGE } from "../types/listTable";
import {
  importBatchStatusLabels,
  importDecisionLabels,
  importLabels,
  importMatchStatusLabels,
  importMatchTypeLabels,
  importMatchExplanationLabels,
  importRowStatusLabels,
  WIZARD_CONTINUE_STEPS,
  WIZARD_SETUP_STEPS,
  type WizardStepId,
} from "../labels/importLabels";
import type {
  ColumnMappingPayload,
  ImportBatch,
  ImportDecision,
  ImportRow,
  PreviewFilter,
  PreviewSortBy,
  UploadRawImportResponse,
  ExcelHeaderMode,
  MappingColumnPreview,
} from "../types/import";
import { uiLabels } from "../labels/uiLabels";
import { dataIntegrationLabels } from "../labels/dataIntegrationLabels";
import { WIZARD_MAPPING_FIELDS as MAPPING_FIELDS } from "../types/import";
import type { Fair } from "../types/fair";
import { importBatchStatusBadgeVariant, importRowStatusBadgeVariant } from "../utils/importBadges";
import { formatMatchConfidence, getImportMatchStatus } from "../utils/importMatchStatus";
import {
  canResumeDecisions,
  canResumeSetup,
  isTerminalBatchStatus,
  setupStepIndexForStatus,
} from "../utils/importResume";
import {
  ExcelMappingGrid,
  columnFieldMapToMappings,
  extractFieldMappingsFromColumnConfig,
  isMappingGridValid,
  mappingsToColumnFieldMap,
} from "../components/imports/ExcelMappingGrid";
import { MergeDiffViewer } from "../components/imports/MergeDiffViewer";

interface ImportWizardPageProps {
  preselectedFairId?: string;
  resumeBatchId?: string;
  onUploadComplete?: () => void;
  onMappingSaved?: () => void;
  onFinished?: () => void;
}

function str(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

const APPLY_SUMMARY_ONLY_MESSAGES = new Set(["Karar verilmemiş"]);

function isApplySummaryOnlyMessage(message: string): boolean {
  const normalized = message.trim();
  if (APPLY_SUMMARY_ONLY_MESSAGES.has(normalized)) return true;
  if (normalized.includes("karar verilmemiş")) return true;
  if (normalized.includes("işlenmedi")) return true;
  if (normalized.includes("atlandı")) return true;
  return false;
}

export function ImportWizardPage({
  preselectedFairId,
  resumeBatchId,
  onUploadComplete,
  onMappingSaved,
  onFinished,
}: ImportWizardPageProps) {
  const [wizardMode, setWizardMode] = React.useState<"setup" | "continue">("setup");
  const isContinueMode = wizardMode === "continue";
  const [isSetupResume, setIsSetupResume] = React.useState(false);
  const activeSteps = isContinueMode ? WIZARD_CONTINUE_STEPS : WIZARD_SETUP_STEPS;
  const [stepIndex, setStepIndex] = React.useState(0);
  const [batchId, setBatchId] = React.useState<string | null>(null);
  const [batch, setBatch] = React.useState<ImportBatch | null>(null);
  const [uploadPreview, setUploadPreview] = React.useState<UploadRawImportResponse | null>(null);
  const [selectedFairId, setSelectedFairId] = React.useState<string>(preselectedFairId ?? "");
  const [selectedFair, setSelectedFair] = React.useState<Fair | null>(null);
  const [participantCount, setParticipantCount] = React.useState<number | null>(null);
  const [hasHeaderRow, setHasHeaderRow] = React.useState(true);
  const [headerMode, setHeaderMode] = React.useState<ExcelHeaderMode>("first_row_header");
  const [manualHeaderRow, setManualHeaderRow] = React.useState(1);
  const [availableSheets, setAvailableSheets] = React.useState<string[]>([]);
  const [selectedSheet, setSelectedSheet] = React.useState<string>("");
  const [mappings, setMappings] = React.useState<Record<string, number>>({});
  const [columnFieldMap, setColumnFieldMap] = React.useState<Record<number, string>>({});
  const [gridColumns, setGridColumns] = React.useState<{ index: number; letter: string; header: string | null }[]>([]);
  const [gridRows, setGridRows] = React.useState<unknown[][]>([]);
  const [gridMeta, setGridMeta] = React.useState<{ totalDataRows?: number; previewRowCount?: number }>({});
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedRowIds, setSelectedRowIds] = React.useState<Set<string>>(() => new Set());
  const [bulkAssignDecision, setBulkAssignDecision] = React.useState<ImportDecision | "">("");
  const [bulkAssignRunning, setBulkAssignRunning] = React.useState(false);
  const [bulkAssignResultMessage, setBulkAssignResultMessage] = React.useState<string | null>(null);
  const [bulkAssignErrors, setBulkAssignErrors] = React.useState<
    Array<{ row_id: string; row_number: number; message: string }>
  >([]);
  const [applyRunning, setApplyRunning] = React.useState(false);
  const [applyResult, setApplyResult] = React.useState<{
    processed_count: number;
    not_processed_count: number;
    failed_count: number;
    errors: Array<{ row_id: string; row_number: number; message: string }>;
  } | null>(null);
  const fileRef = React.useRef<HTMLInputElement>(null);
  const [mappingColumns, setMappingColumns] = React.useState<MappingColumnPreview[]>([]);
  const [showAllSamples, setShowAllSamples] = React.useState(false);

  const currentStep = activeSteps[stepIndex]?.id ?? "upload";
  const isPreviewStep = currentStep === "decisions";
  const isImportComplete =
    batch?.status === "completed" || batch?.status === "applied";
  const processedRowCount = batch
    ? batch.created_rows + batch.updated_rows + batch.skipped_rows
    : 0;
  const isBatchAnalyzed =
    batch?.status === "analyzed" ||
    batch?.status === "decision_required" ||
    batch?.status === "applying" ||
    batch?.status === "previewed";

  const decisionListFilters = React.useMemo(
    () => (isPreviewStep ? { filter: "pending" } : {}),
    [isPreviewStep],
  );

  const fetchDecisionRows = React.useCallback(
    (params: ServerTableFetchParams) => {
      const activeFilter = params.filters?.filter;
      return listImportRows(batchId!, {
        ...params,
        filters: {
          ...params.filters,
          filter: activeFilter || (isPreviewStep ? "pending" : undefined),
        },
      });
    },
    [batchId, isPreviewStep],
  );

  const previewTable = useServerDataTable<ImportRow>({
    fetchFn: fetchDecisionRows,
    defaultSort: { field: "company_name", direction: "asc" },
    defaultFilters: decisionListFilters,
    filterKeys: ["filter"],
    enabled: Boolean(batchId) && isPreviewStep && isBatchAnalyzed,
  });

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
    if (preselectedFairId) {
      setSelectedFairId(preselectedFairId);
      void loadFairDetails(preselectedFairId);
      if (!isContinueMode && stepIndex < 1) setStepIndex(0);
    }
  }, [preselectedFairId, loadFairDetails, stepIndex, isContinueMode]);

  const hydrateBatchForResume = React.useCallback((b: ImportBatch) => {
    if (b.available_sheets?.length) setAvailableSheets(b.available_sheets);
    if (b.selected_sheet_name) setSelectedSheet(b.selected_sheet_name);
    if (b.header_mode) {
      setHeaderMode(b.header_mode);
      setHasHeaderRow(b.header_mode !== "no_header");
    }
    if (b.header_row_index != null) setManualHeaderRow(b.header_row_index + 1);
    const savedMappings = extractFieldMappingsFromColumnConfig(b.column_mapping_json);
    if (Object.keys(savedMappings).length > 0) {
      setColumnFieldMap(mappingsToColumnFieldMap(savedMappings));
      setMappings(
        Object.fromEntries(Object.entries(savedMappings).map(([k, v]) => [k, v.value])),
      );
    }
  }, []);

  React.useEffect(() => {
    if (!resumeBatchId) return;
    setBatchId(resumeBatchId);
    void (async () => {
      try {
        const b = await getImportBatch(resumeBatchId);
        setBatch(b);
        if (isTerminalBatchStatus(b.status)) {
          onFinished?.();
          return;
        }
        if (canResumeDecisions(b.status)) {
          setWizardMode("continue");
          setIsSetupResume(false);
          setStepIndex(0);
        } else if (canResumeSetup(b.status)) {
          setWizardMode("setup");
          setIsSetupResume(true);
          hydrateBatchForResume(b);
          setStepIndex(setupStepIndexForStatus(b.status));
        } else {
          onFinished?.();
          return;
        }
        if (b.fair_id) {
          setSelectedFairId(b.fair_id);
          void loadFairDetails(b.fair_id);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : importLabels.loadError);
      }
    })();
  }, [resumeBatchId, loadFairDetails, hydrateBatchForResume, onFinished]);

  React.useEffect(() => {
    if (selectedFairId) void loadFairDetails(selectedFairId);
  }, [selectedFairId, loadFairDetails]);

  const refreshMappingPreview = React.useCallback(async () => {
    if (!batchId) return;
    const headerRowIndex = headerMode === "manual_header_row" ? manualHeaderRow - 1 : undefined;
    try {
      const preview = await getMappingPreview(batchId, {
        header_mode: headerMode,
        header_row_index: headerRowIndex,
      });
      setMappingColumns(preview.columns);
      if (preview.grid) {
        setGridColumns(preview.grid.columns);
        setGridRows(preview.grid.rows);
        setGridMeta({
          totalDataRows: preview.grid.total_data_rows,
          previewRowCount: preview.grid.preview_row_count,
        });
      }
    } catch {
      /* keep existing preview */
    }
  }, [batchId, headerMode, manualHeaderRow]);

  React.useEffect(() => {
    if (!batchId) return;
    void refreshMappingPreview();
  }, [batchId, refreshMappingPreview]);

  const refreshBatch = async (id: string) => {
    const b = await getImportBatch(id);
    setBatch(b);
  };

  React.useEffect(() => {
    if (!batchId || currentStep !== "mapping") return;
    void refreshMappingPreview();
  }, [batchId, currentStep, refreshMappingPreview]);

  const handleUpload = async () => {
    if (!selectedFile || !selectedFairId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await uploadRawImport(selectedFairId, selectedFile);
      setBatchId(result.batch_id);
      setUploadPreview(result);
      setAvailableSheets(result.available_sheets ?? []);
      setSelectedSheet(result.selected_sheet_name ?? result.available_sheets?.[0] ?? "");
      const mode = result.suggested_mapping.header_mode ?? (result.suggested_mapping.has_header_row ? "first_row_header" : "no_header");
      setHeaderMode(mode);
      setHasHeaderRow(mode !== "no_header");
      setManualHeaderRow((result.suggested_mapping.header_row_index ?? 0) + 1);
      const initial: Record<string, number> = {};
      for (const [k, v] of Object.entries(result.suggested_mapping.mappings)) {
        initial[k] = v.value;
      }
      setMappings(initial);
      setColumnFieldMap(mappingsToColumnFieldMap(result.suggested_mapping.mappings));
      setMappingColumns(result.mapping_columns ?? []);
      onUploadComplete?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.uploadError);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveMapping = async () => {
    if (!batchId || !isMappingGridValid(columnFieldMap)) {
      setError("Firma Adı eşleştirmesi zorunludur ve aynı alan iki kolona atanamaz.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const mappingPayload = columnFieldMapToMappings(columnFieldMap);
      const payload: ColumnMappingPayload = {
        has_header_row: headerMode !== "no_header",
        header_mode: headerMode,
        header_row_index: headerMode === "manual_header_row" ? manualHeaderRow - 1 : headerMode === "first_row_header" ? 0 : null,
        mappings: mappingPayload,
      };
      await setColumnMapping(batchId, payload);
      (onMappingSaved ?? onFinished)?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.loadError);
    } finally {
      setLoading(false);
    }
  };

  const handleSheetConfirm = async () => {
    if (!batchId || !selectedSheet) return;
    setLoading(true);
    setError(null);
    try {
      const res = await selectImportSheet(batchId, selectedSheet);
      const sm = res.suggested_mapping as { header_mode?: ExcelHeaderMode; mappings?: Record<string, { value: number }> };
      if (sm.header_mode) setHeaderMode(sm.header_mode);
      if (sm.mappings) {
        setMappings(
          Object.fromEntries(Object.entries(sm.mappings).map(([k, v]) => [k, v.value])),
        );
        setColumnFieldMap(mappingsToColumnFieldMap(sm.mappings));
      }
      if (res.mapping_columns) setMappingColumns(res.mapping_columns);
      setStepIndex(3);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.loadError);
    } finally {
      setLoading(false);
    }
  };

  const handleHeaderConfirm = async () => {
    if (!batchId) return;
    setLoading(true);
    setError(null);
    try {
      await configureImportHeader(batchId, {
        has_header_row: headerMode !== "no_header",
        header_mode: headerMode,
        header_row_index: headerMode === "manual_header_row" ? manualHeaderRow - 1 : headerMode === "first_row_header" ? 0 : null,
      });
      await refreshMappingPreview();
      setStepIndex(4);
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
      await refreshBatch(batchId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.decisionError);
    }
  };

  const previewFilter =
    (previewTable.filters.filter as PreviewFilter | undefined) ||
    (isPreviewStep ? "pending" : "all");

  const pageRowIds = React.useMemo(
    () => previewTable.items.map((row) => row.id),
    [previewTable.items],
  );
  const allPageRowsSelected =
    pageRowIds.length > 0 && pageRowIds.every((id) => selectedRowIds.has(id));
  const somePageRowsSelected = pageRowIds.some((id) => selectedRowIds.has(id));

  const toggleRowSelection = (rowId: string, checked: boolean) => {
    setSelectedRowIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(rowId);
      else next.delete(rowId);
      return next;
    });
  };

  const togglePageSelection = (checked: boolean) => {
    setSelectedRowIds((prev) => {
      const next = new Set(prev);
      for (const id of pageRowIds) {
        if (checked) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  };

  const handleBulkAssignDecisions = async () => {
    if (!batchId || bulkAssignRunning || !bulkAssignDecision || selectedRowIds.size === 0) return;
    setBulkAssignRunning(true);
    setBulkAssignResultMessage(null);
    setBulkAssignErrors([]);
    setError(null);
    try {
      const result = await bulkAssignRowDecisions(
        batchId,
        Array.from(selectedRowIds),
        bulkAssignDecision,
      );
      setBulkAssignResultMessage(
        importLabels.bulkAssignResult(result.updated_count, result.skipped_count),
      );
      setBulkAssignErrors(result.errors);
      await previewTable.refresh();
      await refreshBatch(batchId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.decisionError);
    } finally {
      setBulkAssignRunning(false);
    }
  };

  const handleApplyDecisions = async () => {
    if (!batchId || applyRunning) return;
    setApplyRunning(true);
    setApplyResult(null);
    setError(null);
    try {
      const result = await applyImportDecisions(batchId, {
        filter: previewFilter,
        search: previewTable.search || undefined,
      });
      const executionErrors = result.errors.filter(
        (item) => !isApplySummaryOnlyMessage(item.message),
      );
      setApplyResult({
        processed_count: result.processed_count,
        not_processed_count: result.not_processed_count,
        failed_count: executionErrors.length > 0 ? executionErrors.length : result.failed_count,
        errors: executionErrors,
      });
      setSelectedRowIds(new Set());
      const pendingFilters = { ...previewTable.filters, filter: "pending" };
      previewTable.setFilters(pendingFilters);
      await previewTable.refresh({ filters: pendingFilters, page: DEFAULT_PAGE });
      await refreshBatch(batchId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : importLabels.decisionError);
    } finally {
      setApplyRunning(false);
    }
  };

  const renderPreviewControls = () => (
    <div className="preview-controls">
      <div className="preview-filters">
        {(
          [
            ["pending", importLabels.previewFilterPending],
            ["all", importLabels.previewFilterAll],
            ["applied", importLabels.previewFilterApplied],
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
            onClick={() => previewTable.setFilter("filter", key)}
          >
            {importLabels.previewFilterWithCount(label, previewTable.filterCounts?.[key] ?? 0)}
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

  const renderAnalyzeResultTable = () => {
    if (previewTable.loading) {
      return <LoadingState message="Satırlar yükleniyor…" />;
    }
    if (previewTable.items.length === 0) {
      return (
        <EmptyState
          title="Satır bulunamadı"
          description="Analiz sonucu boş. Kolon eşleştirmesini ve Excel verisini kontrol edin."
        />
      );
    }
    return (
      <DataTableShell>
        <table className="data-table import-analyze-table">
          <thead>
            <tr>
              <th>{importLabels.colRow}</th>
              <th>{importLabels.colCompany}</th>
              <th>{importLabels.colStatus}</th>
              <th>{importLabels.colMatch}</th>
              <th>{importLabels.colMatchType}</th>
              <th>{importLabels.colConfidence}</th>
            </tr>
          </thead>
          <tbody>
            {previewTable.items.map((row) => {
              const matchStatus = getImportMatchStatus(row);
              return (
                <tr key={row.id}>
                  <td>{row.row_number}</td>
                  <td>{str(row.normalized_data_json?.company_name)}</td>
                  <td>{importMatchStatusLabels[matchStatus] ?? matchStatus}</td>
                  <td>{row.match_customer_name ?? "—"}</td>
                  <td>
                    {row.match_reason
                      ? importMatchTypeLabels[row.match_reason] ?? row.match_reason
                      : "—"}
                  </td>
                  <td>{formatMatchConfidence(row.match_confidence)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </DataTableShell>
    );
  };

  const renderBulkDecisionPanel = () => (
    <div className="bulk-decision-panel">
      <h4>{importLabels.bulkDecisionPanelTitle}</h4>
      <div className="bulk-decision-panel-controls">
        <label className="bulk-decision-field">
          <span>{importLabels.bulkDecisionActionLabel}</span>
          <select
            className="form-select"
            value={bulkAssignDecision}
            onChange={(e) => setBulkAssignDecision(e.target.value as ImportDecision | "")}
            disabled={bulkAssignRunning || applyRunning}
          >
            <option value="">—</option>
            {Object.entries(importDecisionLabels).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="btn btn-secondary"
          disabled={
            bulkAssignRunning
            || applyRunning
            || selectedRowIds.size === 0
            || !bulkAssignDecision
          }
          onClick={() => void handleBulkAssignDecisions()}
        >
          {bulkAssignRunning ? importLabels.bulkAssignRunning : importLabels.bulkAssignSelected}
        </button>
        {selectedRowIds.size > 0 && (
          <span className="text-muted">{importLabels.selectedCount(selectedRowIds.size)}</span>
        )}
      </div>
      {bulkAssignResultMessage && (
        <p className="text-muted import-bulk-result">{bulkAssignResultMessage}</p>
      )}
      {bulkAssignErrors.length > 0 && (
        <div className="import-apply-errors">
          <strong>{importLabels.bulkAssignErrorsTitle}</strong>
          <ul>
            {bulkAssignErrors.map((item) => (
              <li key={item.row_id}>
                #{item.row_number}: {item.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  const renderMergePreviewList = (editable: boolean) => (
    <div className="merge-preview-list">
      {editable && previewTable.items.length > 0 && (
        <div className="merge-preview-select-all">
          <label className="merge-preview-checkbox-label">
            <input
              type="checkbox"
              checked={allPageRowsSelected}
              ref={(el) => {
                if (el) el.indeterminate = !allPageRowsSelected && somePageRowsSelected;
              }}
              onChange={(e) => togglePageSelection(e.target.checked)}
              aria-label={importLabels.selectAllOnPage}
            />
            {importLabels.selectAllOnPage}
          </label>
          {selectedRowIds.size > 0 && (
            <span className="text-muted">{importLabels.selectedCount(selectedRowIds.size)}</span>
          )}
        </div>
      )}
      {previewTable.items.length === 0 && !previewTable.loading ? (
        <EmptyState title="Satır yok" description="Filtreye uygun satır bulunamadı." />
      ) : (
        previewTable.items.map((row) => (
          <div key={row.id} className="merge-preview-item">
            <div className="merge-preview-meta">
              {editable && (
                <input
                  type="checkbox"
                  className="merge-preview-row-checkbox"
                  checked={selectedRowIds.has(row.id)}
                  onChange={(e) => toggleRowSelection(row.id, e.target.checked)}
                  aria-label={`Satır ${row.row_number} seç`}
                />
              )}
              <span>#{row.row_number}</span>
              <Badge variant={importRowStatusBadgeVariant(row.status)}>
                {importRowStatusLabels[row.status] ?? row.status}
              </Badge>
              {row.match_confidence != null && (
                <span className="text-muted">Güven: {row.match_confidence}%</span>
              )}
              {typeof row.normalized_data_json?._match_explanation === "string" && (
                <span className="text-muted import-match-explanation">
                  {row.normalized_data_json._match_explanation
                    .split(", ")
                    .map((code) => importMatchExplanationLabels[code] ?? code)
                    .join(" · ")}
                </span>
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

  const renderStepper = () => (
    <div className="wizard-stepper">
      {activeSteps.map((s, i) => (
        <span key={s.id} className={`wizard-step ${i === stepIndex ? "active" : i < stepIndex ? "done" : ""}`}>
          {i + 1}. {s.label}
        </span>
      ))}
    </div>
  );

  const renderSheet = () => (
    <Card>
      <h3>{dataIntegrationLabels.sheetTitle}</h3>
      <p className="text-muted">{dataIntegrationLabels.sheetSubtitle}</p>
      {availableSheets.length > 0 ? (
        <div className="form-field">
          <label>{dataIntegrationLabels.sheetTitle}</label>
          <select
            className="form-select"
            value={selectedSheet}
            onChange={(e) => setSelectedSheet(e.target.value)}
          >
            {availableSheets.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      ) : (
        <p>{selectedSheet || "—"}</p>
      )}
    </Card>
  );

  const renderHeader = () => (
    <Card>
      <h3>{dataIntegrationLabels.headerModeTitle}</h3>
      <div className="header-toggle">
        <label>
          <input
            type="radio"
            checked={headerMode === "first_row_header"}
            onChange={() => {
              setHeaderMode("first_row_header");
              setHasHeaderRow(true);
            }}
          />
          {dataIntegrationLabels.headerFirstRow}
        </label>
        <label>
          <input
            type="radio"
            checked={headerMode === "no_header"}
            onChange={() => {
              setHeaderMode("no_header");
              setHasHeaderRow(false);
            }}
          />
          {dataIntegrationLabels.headerNoHeader}
        </label>
        <label>
          <input
            type="radio"
            checked={headerMode === "manual_header_row"}
            onChange={() => {
              setHeaderMode("manual_header_row");
              setHasHeaderRow(true);
            }}
          />
          {dataIntegrationLabels.headerManualRow}
        </label>
      </div>
      {headerMode === "manual_header_row" && (
        <div className="form-field">
          <label>{dataIntegrationLabels.manualHeaderRowLabel}</label>
          <input
            type="number"
            min={1}
            className="form-input"
            value={manualHeaderRow}
            onChange={(e) => setManualHeaderRow(Number(e.target.value) || 1)}
          />
        </div>
      )}
    </Card>
  );

  const renderMappingGrid = () => (
    <Card>
      <h3>{importLabels.mappingTitle}</h3>
      <p className="text-muted">Her Excel kolonunu CRM alanına eşleştirin. Firma Adı zorunludur.</p>
      <ExcelMappingGrid
        columns={gridColumns}
        rows={gridRows}
        columnFieldMap={columnFieldMap}
        onColumnFieldChange={(colIndex, field) =>
          setColumnFieldMap((prev) => ({ ...prev, [colIndex]: field }))
        }
        totalDataRows={gridMeta.totalDataRows}
        previewRowCount={gridMeta.previewRowCount}
      />
      {!isMappingGridValid(columnFieldMap) && (
        <p className="form-error" role="status">
          Firma Adı eşleştirmesi zorunludur ve aynı alan iki kolona atanamaz.
        </p>
      )}
    </Card>
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
      {isSetupResume && batch ? (
        <>
          <p className="text-muted">{importLabels.uploadResumeHint}</p>
          <p>
            <strong>{batch.file_name}</strong>
          </p>
        </>
      ) : (
        <>
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
        </>
      )}
      {uploadPreview && availableSheets.length > 1 && (
        <div className="form-field">
          <label>{dataIntegrationLabels.sheetTitle}</label>
          <select
            className="form-select"
            value={selectedSheet}
            onChange={async (e) => {
              const sheet = e.target.value;
              setSelectedSheet(sheet);
              if (!batchId) return;
              try {
                const res = await selectImportSheet(batchId, sheet);
                setHasHeaderRow(Boolean(res.suggested_mapping?.has_header_row));
                const sm = res.suggested_mapping as { header_mode?: ExcelHeaderMode; mappings?: Record<string, { value: number }> };
                if (sm.header_mode) setHeaderMode(sm.header_mode);
                const initial: Record<string, number> = {};
                for (const [k, v] of Object.entries(sm.mappings ?? {})) {
                  initial[k] = v.value;
                }
                setMappings(initial);
                if (res.mapping_columns) setMappingColumns(res.mapping_columns);
                if (res.detected_headers && uploadPreview) {
                  setUploadPreview({ ...uploadPreview, detected_headers: res.detected_headers });
                }
              } catch {
                /* best effort */
              }
            }}
          >
            {availableSheets.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      )}
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
        <FairEntitySelect
          value={selectedFairId}
          onChange={setSelectedFairId}
          placeholder={importLabels.fairSelect}
        />
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
          <input
            type="radio"
            checked={headerMode === "first_row_header"}
            onChange={() => {
              setHeaderMode("first_row_header");
              setHasHeaderRow(true);
            }}
          />
          {dataIntegrationLabels.headerFirstRow}
        </label>
        <label>
          <input
            type="radio"
            checked={headerMode === "no_header"}
            onChange={() => {
              setHeaderMode("no_header");
              setHasHeaderRow(false);
            }}
          />
          {dataIntegrationLabels.headerNoHeader}
        </label>
        <label>
          <input
            type="radio"
            checked={headerMode === "manual_header_row"}
            onChange={() => {
              setHeaderMode("manual_header_row");
              setHasHeaderRow(true);
            }}
          />
          {dataIntegrationLabels.headerManualRow}
        </label>
      </div>
      {headerMode === "manual_header_row" && (
        <div className="form-field">
          <label>{dataIntegrationLabels.manualHeaderRowLabel}</label>
          <input
            type="number"
            min={1}
            className="form-input"
            value={manualHeaderRow}
            onChange={(e) => setManualHeaderRow(Number(e.target.value) || 1)}
          />
        </div>
      )}
      <DataTableShell>
        <table className="mapping-table">
          <thead>
            <tr>
              <th>{importLabels.mappingCrmField}</th>
              <th>{importLabels.mappingSourceColumn}</th>
              <th>{importLabels.mappingSourcePreview}</th>
            </tr>
          </thead>
          <tbody>
            {MAPPING_FIELDS.map((field) => {
              const mappedIndex = mappings[field.key];
              const mappedColumn = mappingColumns.find((col) => col.index === mappedIndex);
              return (
                <tr key={field.key}>
                  <td className="mapping-crm-field">
                    {field.label}
                    {field.required && " *"}
                  </td>
                  <td>
                    <select
                      className="form-select"
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
                  <td className="mapping-preview-cell">
                    <MappingFieldPreview column={mappedColumn} showAll={showAllSamples} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </DataTableShell>
      {hasExpandableSamples && (
        <button
          type="button"
          className="btn btn-link mapping-expand-samples"
          onClick={() => setShowAllSamples((prev) => !prev)}
        >
          {showAllSamples ? importLabels.mappingShowLessSamples : importLabels.mappingShowMoreSamples}
        </button>
      )}
    </Card>
  );

  const renderAnalyze = () => (
    <Card>
      <h3>{importLabels.analyzeTitle}</h3>
      {batch && (
        <p>
          {isBatchAnalyzed
            ? `${batch.total_rows} satır analiz edildi`
            : `${batch.total_rows} ham satır yüklendi — analiz henüz çalıştırılmadı`}
          {" · "}
          Durum:{" "}
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
      {!isBatchAnalyzed ? (
        <EmptyState
          title="Analiz gerekli"
          description="Önizleme için önce analiz adımını tamamlayın."
        />
      ) : (
        <>
          {renderPreviewControls()}
          {!batchId ? (
            <EmptyState title="Satır yok" description="Önce analiz çalıştırın." />
          ) : (
            <>
              {renderAnalyzeResultTable()}
              <ServerDataTableFrame table={previewTable} skeletonRows={3}>
                {renderMergePreviewList(false)}
              </ServerDataTableFrame>
            </>
          )}
        </>
      )}
    </Card>
  );

  const renderDecisions = () => {
    const decisionBusy = applyRunning || bulkAssignRunning || loading;

    if (isImportComplete && batch) {
      return (
        <Card>
          <div className="import-complete-banner">
            <h3>✅ {importLabels.importCompletedTitle}</h3>
            <p>{importLabels.importCompletedMessage(processedRowCount)}</p>
            <p className="text-muted">{importLabels.importCompletedNoPending}</p>
            <button type="button" className="btn btn-primary" onClick={() => onFinished?.()}>
              {importLabels.importCompletedBack}
            </button>
          </div>
        </Card>
      );
    }

    return (
      <Card>
        <h3>{importLabels.decisionsTitle}</h3>
        {!isBatchAnalyzed ? (
          <EmptyState
            title="Analiz gerekli"
            description="Karar adımı için önce analizi tamamlayın."
          />
        ) : (
          <>
            {renderBulkDecisionPanel()}
            <div className="bulk-actions">
              <button
                type="button"
                className="btn btn-primary"
                disabled={decisionBusy || previewTable.items.length === 0}
                onClick={() => void handleApplyDecisions()}
              >
                {decisionBusy ? importLabels.applyRunning : importLabels.applyAllList}
              </button>
              {applyResult && (
                <div className="import-apply-result">
                  <p className="import-apply-result-title">{importLabels.applyCompletedTitle}</p>
                  {applyResult.processed_count > 0 && (
                    <p className="import-apply-result-success">
                      ✅ {importLabels.applyProcessedCount(applyResult.processed_count)}
                    </p>
                  )}
                  {applyResult.not_processed_count > 0 && (
                    <p className="import-apply-result-info">
                      ℹ {importLabels.applyNotProcessedCount(applyResult.not_processed_count)}
                    </p>
                  )}
                  {applyResult.errors.length > 0 && (
                    <div className="import-apply-errors">
                      <p className="import-apply-result-warning">
                        ⚠ {importLabels.applyFailedCount(applyResult.errors.length)}
                      </p>
                      <ul>
                        {applyResult.errors.map((item) => (
                          <li key={item.row_id}>
                            #{item.row_number} {item.message}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
            {renderPreviewControls()}
            <ServerDataTableFrame table={previewTable} skeletonRows={3}>
              {renderMergePreviewList(!decisionBusy)}
            </ServerDataTableFrame>
          </>
        )}
      </Card>
    );
  };

  const setupStepContent: Record<string, React.ReactNode> = {
    fair: renderFair(),
    upload: renderUpload(),
    sheet: renderSheet(),
    header: renderHeader(),
    mapping: renderMappingGrid(),
  };

  const continueStepContent: Record<string, React.ReactNode> = {
    decisions: renderDecisions(),
  };

  const stepContent = isContinueMode ? continueStepContent : setupStepContent;

  const canNext = () => {
    if (isContinueMode) return true;
    if (currentStep === "fair") return !!selectedFairId;
    if (currentStep === "upload") return isSetupResume || !!selectedFile;
    if (currentStep === "sheet") return !!selectedSheet;
    if (currentStep === "mapping") return isMappingGridValid(columnFieldMap);
    return true;
  };

  const handleNext = () => {
    if (isContinueMode) return;
    if (currentStep === "upload") {
      if (isSetupResume) {
        setStepIndex((i) => i + 1);
        return;
      }
      if (selectedFile && selectedFairId) {
        void handleUpload();
      }
      return;
    }
    if (currentStep === "sheet") {
      void handleSheetConfirm();
      return;
    }
    if (currentStep === "header") {
      void handleHeaderConfirm();
      return;
    }
    if (currentStep === "mapping") {
      void handleSaveMapping();
      return;
    }
    if (stepIndex < activeSteps.length - 1) setStepIndex((i) => i + 1);
  };

  const nextButtonLabel =
    currentStep === "mapping" ? "Kaydet ve Listeye Dön" : importLabels.next;

  return (
    <div className="import-wizard">
      <PageHeader title={importLabels.wizardTitle} subtitle={importLabels.wizardSubtitle} />
      {renderStepper()}
      {error && <p className="form-error">{error}</p>}
      {loading ? <LoadingState message="Yükleniyor…" /> : stepContent[currentStep]}
      <div className="wizard-nav">
        <button
          type="button"
          className="btn btn-secondary"
          disabled={stepIndex === 0}
          onClick={() => setStepIndex(Math.max(0, stepIndex - 1))}
        >
          {importLabels.back}
        </button>
        {!(isContinueMode && currentStep === "decisions") && (
          <button
            type="button"
            className="btn btn-primary"
            disabled={!canNext() || loading}
            onClick={handleNext}
          >
            {nextButtonLabel}
          </button>
        )}
      </div>
    </div>
  );
}
