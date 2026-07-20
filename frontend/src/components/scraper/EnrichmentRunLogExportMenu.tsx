import React from "react";
import { downloadEnrichmentRunLogs } from "../../api/scraper";
import { ApiError } from "../../api/client";
import { scraperLabels } from "../../labels/scraperLabels";

interface EnrichmentRunLogExportMenuProps {
  runId: string;
  disabled?: boolean;
}

export function EnrichmentRunLogExportMenu({ runId, disabled = false }: EnrichmentRunLogExportMenuProps) {
  const [open, setOpen] = React.useState(false);
  const [loadingFormat, setLoadingFormat] = React.useState<"txt" | "json" | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const menuRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const onDocumentClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocumentClick);
    return () => document.removeEventListener("mousedown", onDocumentClick);
  }, [open]);

  const handleExport = async (format: "txt" | "json") => {
    setLoadingFormat(format);
    setError(null);
    setOpen(false);
    try {
      await downloadEnrichmentRunLogs(runId, format);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : scraperLabels.enrichmentRunLogExportFailed);
    } finally {
      setLoadingFormat(null);
    }
  };

  const loading = loadingFormat !== null;

  return (
    <div className="enrichment-run-log-export">
      <div className="run-history-files-menu" ref={menuRef}>
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          aria-haspopup="menu"
          aria-expanded={open}
          disabled={disabled || loading}
          onClick={() => setOpen((value) => !value)}
        >
          {loading ? scraperLabels.enrichmentRunLogExporting : scraperLabels.enrichmentRunLogExport}
        </button>
        {open ? (
          <div className="run-history-files-dropdown" role="menu">
            <button
              type="button"
              role="menuitem"
              className="run-history-files-item"
              disabled={loadingFormat === "txt"}
              onClick={() => void handleExport("txt")}
            >
              {scraperLabels.enrichmentRunLogExportTxt}
            </button>
            <button
              type="button"
              role="menuitem"
              className="run-history-files-item"
              disabled={loadingFormat === "json"}
              onClick={() => void handleExport("json")}
            >
              {scraperLabels.enrichmentRunLogExportJson}
            </button>
          </div>
        ) : null}
      </div>
      {error ? <p className="text-danger enrichment-run-log-export-error">{error}</p> : null}
    </div>
  );
}
