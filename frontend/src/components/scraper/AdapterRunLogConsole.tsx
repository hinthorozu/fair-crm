import React from "react";
import {
  downloadScraperRunOutput,
  listScraperRunLogs,
  openScraperRunOutput,
  runAdapterTest,
} from "../../api/scraper";
import { ApiError } from "../../api/client";
import { Badge } from "../ui/Badge";
import { scraperLabels } from "../../labels/scraperLabels";
import { runStatusBadgeVariant, runStatusLabel } from "../../utils/scraperBadges";
import type { ScraperRunLog } from "../../types/scraper";

const POLL_INTERVAL_MS = 2000;

interface AdapterRunLogConsoleProps {
  adapterKey: string;
  focusRunId?: string | null;
  outputJson?: boolean;
  outputExcel?: boolean;
}

function formatConsoleTime(value: string): string {
  return new Date(value).toLocaleTimeString("tr-TR");
}

function formatStepLabel(step: string): string {
  if (step === "browser/open_url") return "Browser";
  return step.replace(/_/g, " ");
}

export function AdapterRunLogConsole({
  adapterKey,
  focusRunId,
  outputJson = true,
  outputExcel = false,
}: AdapterRunLogConsoleProps) {
  const [inputUrl, setInputUrl] = React.useState("");
  const [maxPagesInput, setMaxPagesInput] = React.useState("");
  const [activeRunId, setActiveRunId] = React.useState<string | null>(null);
  const [logs, setLogs] = React.useState<ScraperRunLog[]>([]);
  const [runStatus, setRunStatus] = React.useState<string | null>(null);
  const [totalRows, setTotalRows] = React.useState(0);
  const [outputJsonAvailable, setOutputJsonAvailable] = React.useState(false);
  const [outputExcelAvailable, setOutputExcelAvailable] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [running, setRunning] = React.useState(false);
  const [polling, setPolling] = React.useState(false);
  const [outputLoading, setOutputLoading] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const lastLogIdRef = React.useRef<string | null>(null);
  const consoleRef = React.useRef<HTMLDivElement>(null);

  const selectedRunId = activeRunId ?? focusRunId ?? null;

  const resetOutputs = React.useCallback(() => {
    setTotalRows(0);
    setOutputJsonAvailable(false);
    setOutputExcelAvailable(false);
  }, []);

  const loadLogs = React.useCallback(async (runId: string, incremental: boolean) => {
    setLoading(!incremental);
    setError(null);
    try {
      const response = await listScraperRunLogs(runId, {
        after_id: incremental ? lastLogIdRef.current ?? undefined : undefined,
        limit: 500,
      });
      setRunStatus(response.run_status);
      setTotalRows(response.total_rows);
      setOutputJsonAvailable(response.output_json_available);
      setOutputExcelAvailable(response.output_excel_available);
      if (incremental && lastLogIdRef.current) {
        if (response.items.length > 0) {
          setLogs((current) => [...current, ...response.items]);
          lastLogIdRef.current = response.items[response.items.length - 1]?.id ?? lastLogIdRef.current;
        }
      } else {
        setLogs(response.items);
        lastLogIdRef.current = response.items[response.items.length - 1]?.id ?? null;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : scraperLabels.loadError);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (!selectedRunId) {
      setLogs([]);
      setRunStatus(null);
      resetOutputs();
      lastLogIdRef.current = null;
      return;
    }
    lastLogIdRef.current = null;
    void loadLogs(selectedRunId, false);
  }, [selectedRunId, loadLogs, resetOutputs]);

  React.useEffect(() => {
    if (!selectedRunId || runStatus !== "running") {
      setPolling(false);
      return;
    }
    setPolling(true);
    const timer = window.setInterval(() => {
      void loadLogs(selectedRunId, true);
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [selectedRunId, runStatus, loadLogs]);

  React.useEffect(() => {
    if (!selectedRunId || runStatus !== "completed") {
      return;
    }
    void loadLogs(selectedRunId, true);
  }, [selectedRunId, runStatus, loadLogs]);

  React.useEffect(() => {
    if (!consoleRef.current) return;
    consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
  }, [logs]);

  const handleRun = React.useCallback(async () => {
    const url = inputUrl.trim();
    if (!url) {
      setError(scraperLabels.testUrlRequired);
      return;
    }
    const trimmedMaxPages = maxPagesInput.trim();
    let maxPages: number | undefined;
    if (trimmedMaxPages) {
      const parsed = Number.parseInt(trimmedMaxPages, 10);
      if (!Number.isFinite(parsed) || parsed < 1) {
        setError(scraperLabels.testMaxPagesInvalid);
        return;
      }
      maxPages = parsed;
    }
    setRunning(true);
    setError(null);
    setLogs([]);
    setRunStatus("running");
    resetOutputs();
    lastLogIdRef.current = null;
    try {
      const run = await runAdapterTest(adapterKey, url, {
        outputJson,
        outputExcel,
        maxPages,
      });
      setActiveRunId(run.id);
    } catch (err) {
      setRunStatus(null);
      setError(err instanceof ApiError ? err.message : scraperLabels.testRunError);
    } finally {
      setRunning(false);
    }
  }, [adapterKey, inputUrl, maxPagesInput, outputExcel, outputJson, resetOutputs]);

  const handleOutputAction = React.useCallback(
    async (action: "download" | "open", kind: "json" | "excel") => {
      if (!selectedRunId) return;
      const actionKey = `${action}-${kind}`;
      setOutputLoading(actionKey);
      setError(null);
      try {
        const fileName = kind === "json" ? `${selectedRunId}.json` : `${selectedRunId}.xlsx`;
        if (action === "download") {
          await downloadScraperRunOutput(selectedRunId, kind, fileName);
        } else {
          await openScraperRunOutput(selectedRunId, kind);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : scraperLabels.testOutputDownloadError);
      } finally {
        setOutputLoading(null);
      }
    },
    [selectedRunId],
  );

  const showOutputs =
    runStatus === "completed" && (outputJsonAvailable || outputExcelAvailable || totalRows > 0);

  return (
    <div className="adapter-console">
      <div className="adapter-console-form">
        <label className="adapter-console-url-label" htmlFor="adapter-test-url">
          {scraperLabels.testUrlLabel}
        </label>
        <div className="adapter-console-url-row">
          <input
            id="adapter-test-url"
            className="input adapter-console-url-input"
            type="url"
            placeholder={scraperLabels.testUrlPlaceholder}
            value={inputUrl}
            disabled={running || runStatus === "running"}
            onChange={(event) => setInputUrl(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void handleRun();
              }
            }}
          />
          <button
            type="button"
            className="btn primary"
            disabled={running || runStatus === "running" || !inputUrl.trim()}
            onClick={() => void handleRun()}
          >
            {running || runStatus === "running" ? scraperLabels.testRunning : scraperLabels.testRun}
          </button>
        </div>
        <label className="adapter-console-url-label" htmlFor="adapter-test-max-pages">
          {scraperLabels.testMaxPagesLabel}
        </label>
        <input
          id="adapter-test-max-pages"
          className="input adapter-console-max-pages-input"
          type="number"
          min={1}
          step={1}
          inputMode="numeric"
          placeholder={scraperLabels.testMaxPagesPlaceholder}
          value={maxPagesInput}
          disabled={running || runStatus === "running"}
          onChange={(event) => setMaxPagesInput(event.target.value)}
        />
        <p className="form-hint">{scraperLabels.testMaxPagesHint}</p>
      </div>

      {runStatus ? (
        <div className="adapter-console-status">
          <span className="text-muted">{scraperLabels.testStatusLabel}</span>
          <Badge variant={runStatusBadgeVariant(runStatus)}>{runStatusLabel(runStatus)}</Badge>
          {polling ? <span className="text-muted adapter-console-polling">{scraperLabels.consolePolling}</span> : null}
        </div>
      ) : null}

      {showOutputs ? (
        <div className="adapter-console-outputs">
          <p className="adapter-console-output-summary">{scraperLabels.testOutputRecordCount(totalRows)}</p>
          <div className="adapter-console-output-links">
            {outputJsonAvailable ? (
              <div className="adapter-console-output-group">
                <span className="adapter-console-output-label">JSON</span>
                <button
                  type="button"
                  className="btn link"
                  disabled={outputLoading !== null}
                  onClick={() => void handleOutputAction("download", "json")}
                >
                  {outputLoading === "download-json" ? "…" : scraperLabels.testOutputJsonDownload}
                </button>
                <button
                  type="button"
                  className="btn link"
                  disabled={outputLoading !== null}
                  onClick={() => void handleOutputAction("open", "json")}
                >
                  {outputLoading === "open-json" ? "…" : scraperLabels.testOutputJsonOpen}
                </button>
              </div>
            ) : null}
            {outputExcelAvailable ? (
              <div className="adapter-console-output-group">
                <span className="adapter-console-output-label">Excel</span>
                <button
                  type="button"
                  className="btn link"
                  disabled={outputLoading !== null}
                  onClick={() => void handleOutputAction("download", "excel")}
                >
                  {outputLoading === "download-excel" ? "…" : scraperLabels.testOutputExcelDownload}
                </button>
                <button
                  type="button"
                  className="btn link"
                  disabled={outputLoading !== null}
                  onClick={() => void handleOutputAction("open", "excel")}
                >
                  {outputLoading === "open-excel" ? "…" : scraperLabels.testOutputExcelOpen}
                </button>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {error ? <p className="text-danger">{error}</p> : null}

      <div ref={consoleRef} className="adapter-console-log" aria-live="polite">
        {!selectedRunId ? (
          <p className="text-muted">{scraperLabels.testConsoleHint}</p>
        ) : null}
        {loading && logs.length === 0 ? <p className="text-muted">Yükleniyor…</p> : null}
        {logs.map((log) => (
          <div key={log.id} className={`adapter-console-line adapter-console-${log.level}`}>
            <span className="adapter-console-time">{formatConsoleTime(log.created_at)}</span>
            <span className="adapter-console-step">[{formatStepLabel(log.step)}]</span>
            <span className="adapter-console-message">{log.message}</span>
          </div>
        ))}
        {selectedRunId && !loading && logs.length === 0 && runStatus === "running" ? (
          <p className="text-muted">{scraperLabels.testWaitingLogs}</p>
        ) : null}
      </div>
    </div>
  );
}
