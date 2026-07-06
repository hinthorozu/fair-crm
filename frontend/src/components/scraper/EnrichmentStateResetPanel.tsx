import React from "react";
import { resetEnrichmentState } from "../../api/scraper";
import { ApiError } from "../../api/client";
import { scraperLabels } from "../../labels/scraperLabels";
import { ConfirmDialog } from "../ui/ConfirmDialog";

export function EnrichmentStateResetPanel() {
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [resetting, setResetting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [successMessage, setSuccessMessage] = React.useState<string | null>(null);

  const handleOpenConfirm = () => {
    setError(null);
    setSuccessMessage(null);
    setConfirmOpen(true);
  };

  const handleConfirmReset = async () => {
    setResetting(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const result = await resetEnrichmentState({ reset_all: true });
      setSuccessMessage(
        scraperLabels.enrichmentStateResetSuccess.replace(
          "{count}",
          result.deleted_count.toLocaleString("tr-TR"),
        ),
      );
      setConfirmOpen(false);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : scraperLabels.enrichmentStateResetFailed;
      setError(message);
      setConfirmOpen(false);
    } finally {
      setResetting(false);
    }
  };

  return (
    <section className="enrichment-state-reset-panel">
      <h3>{scraperLabels.enrichmentStateResetTitle}</h3>
      <p className="form-hint">{scraperLabels.enrichmentStateResetIntro}</p>
      <p className="enrichment-state-reset-info text-muted">{scraperLabels.enrichmentStateResetInfoCrm}</p>

      <div className="enrichment-state-reset-actions">
        <button
          type="button"
          className="btn danger"
          disabled={resetting}
          onClick={handleOpenConfirm}
        >
          {resetting ? scraperLabels.enrichmentStateResetRunning : scraperLabels.enrichmentStateResetAll}
        </button>
      </div>

      {error ? <p className="text-danger">{error}</p> : null}
      {successMessage ? <p className="import-apply-result-success">{successMessage}</p> : null}

      {confirmOpen ? (
        <ConfirmDialog
          title={scraperLabels.enrichmentStateResetConfirmAllTitle}
          message={scraperLabels.enrichmentStateResetConfirmAllMessage}
          confirmLabel={scraperLabels.enrichmentStateResetConfirmAction}
          variant="danger"
          loading={resetting}
          onCancel={() => setConfirmOpen(false)}
          onConfirm={() => void handleConfirmReset()}
        />
      ) : null}
    </section>
  );
}
