import React from "react";
import { listScraperRunLogs } from "../../api/scraper";
import { scraperLabels } from "../../labels/scraperLabels";
import type { ScraperRun, ScraperRunLog } from "../../types/scraper";

const POLL_INTERVAL_MS = 2000;

interface AdapterRunLogConsoleProps {
  runs: ScraperRun[];
  selectedRunId: string | null;
  onSelectRunId: (runId: string) => void;
}

function formatConsoleTime(value: string): string {
  return new Date(value).toLocaleTimeString("tr-TR");
}

function formatStepLabel(step: string): string {
  if (step === "browser/open_url") return "Browser";
  return step.replace(/_/g, " ");
}

export function AdapterRunLogConsole({
  runs,
  selectedRunId,
  onSelectRunId,
}: AdapterRunLogConsoleProps) {
  const [logs, setLogs] = React.useState<ScraperRunLog[]>([]);
  const [runStatus, setRunStatus] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [polling, setPolling] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const lastLogIdRef = React.useRef<string | null>(null);
  const consoleRef = React.useRef<HTMLDivElement>(null);

  const loadLogs = React.useCallback(async (runId: string, incremental: boolean) => {
    setLoading(!incremental);
    setError(null);
    try {
      const response = await listScraperRunLogs(runId, {
        after_id: incremental ? lastLogIdRef.current ?? undefined : undefined,
        limit: 500,
      });
      setRunStatus(response.run_status);
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
      lastLogIdRef.current = null;
      return;
    }
    lastLogIdRef.current = null;
    void loadLogs(selectedRunId, false);
  }, [selectedRunId, loadLogs]);

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
    if (!consoleRef.current) return;
    consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
  }, [logs]);

  return (
    <div className="adapter-console">
      <div className="adapter-console-toolbar">
        <select
          className="adapter-console-run-select"
          value={selectedRunId ?? ""}
          onChange={(event) => onSelectRunId(event.target.value)}
          aria-label={scraperLabels.consoleSelectRun}
        >
          <option value="">{scraperLabels.consoleSelectRun}</option>
          {runs.map((run) => (
            <option key={run.id} value={run.id}>
              {new Date(run.started_at).toLocaleString("tr-TR")} — {run.status}
            </option>
          ))}
        </select>
        {polling ? <span className="text-muted adapter-console-polling">{scraperLabels.consolePolling}</span> : null}
      </div>

      {error ? <p className="text-danger">{error}</p> : null}

      {!selectedRunId ? (
        <p className="text-muted">{scraperLabels.consoleEmpty}</p>
      ) : (
        <div ref={consoleRef} className="adapter-console-log" aria-live="polite">
          {loading && logs.length === 0 ? <p className="text-muted">Yükleniyor…</p> : null}
          {logs.map((log) => (
            <div key={log.id} className={`adapter-console-line adapter-console-${log.level}`}>
              <span className="adapter-console-time">{formatConsoleTime(log.created_at)}</span>
              <span className="adapter-console-step">[{formatStepLabel(log.step)}]</span>
              <span className="adapter-console-message">{log.message}</span>
            </div>
          ))}
          {!loading && logs.length === 0 ? <p className="text-muted">{scraperLabels.consoleEmpty}</p> : null}
        </div>
      )}
    </div>
  );
}
