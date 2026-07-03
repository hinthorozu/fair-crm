import React from "react";
import { getDataOperationRun, ApiError } from "../api/dataOperations";
import { adminLabels } from "../labels/adminLabels";
import { DataOperationAnalyzeResultPage } from "./DataOperationAnalyzeResultPage";
import { DataOperationDuplicateResultPage } from "./DataOperationDuplicateResultPage";

const DUPLICATE_OPERATION_KEY = "duplicate_customer_analysis";
const DUPLICATE_DATASET_KIND = "duplicate_customer_groups";

function isDuplicateResultRun(
  operationKey: string | null | undefined,
  datasetKind: string | null | undefined,
): boolean {
  return operationKey === DUPLICATE_OPERATION_KEY || datasetKind === DUPLICATE_DATASET_KIND;
}

interface DataOperationRunResultPageProps {
  runId: string;
  operationKey?: string | null;
  onBack: () => void;
}

export function DataOperationRunResultPage({
  runId,
  operationKey: operationKeyFromRoute,
  onBack,
}: DataOperationRunResultPageProps) {
  const [resolvedOperationKey, setResolvedOperationKey] = React.useState<string | null>(
    operationKeyFromRoute ?? null,
  );
  const [resolvedDatasetKind, setResolvedDatasetKind] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(!operationKeyFromRoute);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setResolvedOperationKey(operationKeyFromRoute ?? null);
    if (operationKeyFromRoute) {
      setLoading(false);
    }
  }, [operationKeyFromRoute]);

  React.useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const run = await getDataOperationRun(runId);
        if (cancelled) return;
        setResolvedOperationKey(run.operation_key);
        setResolvedDatasetKind(
          run.dataset_kind ?? (run.summary_json?.dataset_kind as string | undefined) ?? null,
        );
        setError(null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : adminLabels.dataOpLoadError);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  if (loading && !operationKeyFromRoute) {
    return <p className="text-muted">{adminLabels.dataOpLoading}</p>;
  }

  if (error && !resolvedOperationKey) {
    return <p className="text-danger">{error}</p>;
  }

  if (isDuplicateResultRun(resolvedOperationKey, resolvedDatasetKind)) {
    return <DataOperationDuplicateResultPage runId={runId} onBack={onBack} />;
  }

  return <DataOperationAnalyzeResultPage runId={runId} onBack={onBack} />;
}
