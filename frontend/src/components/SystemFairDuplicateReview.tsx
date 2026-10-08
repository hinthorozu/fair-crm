import React from "react";
import { ApiError } from "../api/client";
import {
  keepSystemFairsSeparate,
  listSystemFairDuplicates,
  mergeSystemFair,
  previewSystemFairMerge,
  type SystemFairDuplicateGroup,
  type SystemFairMergePreview,
} from "../api/fairs";
import { fairLabels } from "../labels/fairLabels";
import { Banner } from "./ui/Banner";
import { Card } from "./ui/Card";
import { ConfirmDialog } from "./ui/ConfirmDialog";
import { RadioField } from "./ui/form";

type Selection = { keepId: string; mergeId: string };

function counts(fair: SystemFairDuplicateGroup["fairs"][number]): string {
  return [
    `Katılım ${fair.participations}`,
    `Görev ${fair.todos}`,
    `Teklif ${fair.quotes}`,
    `Import ${fair.imports}`,
    `Scraper ${fair.scraper_runs}`,
  ].join(" · ");
}

export function SystemFairDuplicateReview({ onChanged }: { onChanged: () => void }) {
  const [groups, setGroups] = React.useState<SystemFairDuplicateGroup[]>([]);
  const [selection, setSelection] = React.useState<Record<string, Selection>>({});
  const [preview, setPreview] = React.useState<SystemFairMergePreview | null>(null);
  const [pending, setPending] = React.useState<{ sourceId: string; targetId: string } | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(async () => {
    const result = await listSystemFairDuplicates();
    setGroups(result.items);
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    void listSystemFairDuplicates()
      .then((result) => {
        if (!cancelled) setGroups(result.items);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : fairLabels.loadError);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (groups.length === 0 && !error) return null;

  const choose = (key: string, role: "keepId" | "mergeId", fairId: string) => {
    setPreview(null);
    setSelection((current) => {
      const next = { ...(current[key] ?? { keepId: "", mergeId: "" }), [role]: fairId };
      if (role === "keepId" && next.mergeId === fairId) next.mergeId = "";
      if (role === "mergeId" && next.keepId === fairId) next.keepId = "";
      return { ...current, [key]: next };
    });
  };

  const requestMerge = async (key: string) => {
    const chosen = selection[key];
    if (!chosen?.keepId || !chosen.mergeId || busy) return;
    setBusy(true);
    setError(null);
    try {
      const result = await previewSystemFairMerge(chosen.mergeId, chosen.keepId);
      setPreview(result);
      if (result.blocking_conflicts.length === 0) {
        setPending({ sourceId: chosen.mergeId, targetId: chosen.keepId });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fairLabels.duplicateMergeError);
    } finally {
      setBusy(false);
    }
  };

  const confirmMerge = async () => {
    if (!pending) return;
    setBusy(true);
    setError(null);
    try {
      await mergeSystemFair(pending.sourceId, pending.targetId);
      setPending(null);
      setPreview(null);
      setSelection({});
      await load();
      onChanged();
    } catch (err) {
      setPending(null);
      setError(err instanceof ApiError ? err.message : fairLabels.duplicateMergeError);
    } finally {
      setBusy(false);
    }
  };

  const keepSeparate = async (group: SystemFairDuplicateGroup) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await keepSystemFairsSeparate(group.fairs.map((fair) => fair.id));
      setPreview(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fairLabels.duplicateKeepSeparateError);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card as="section" aria-label={fairLabels.duplicateReviewTitle}>
      <h2 className="form-section-title">{fairLabels.duplicateReviewTitle}</h2>
      {error && <Banner variant="error">{error}</Banner>}
      {groups.map((group) => {
        const key = `${group.identity_name}|${group.city ?? ""}`;
        const chosen = selection[key] ?? { keepId: "", mergeId: "" };
        return (
          <div key={key}>
            <p>
              {group.identity_name}
              {group.city ? ` / ${group.city}` : ""}
            </p>
            <div>
              {group.fairs.map((fair) => (
                <article key={fair.id}>
                  <h3>{fair.name}</h3>
                  <p>
                    {[fair.city, fair.start_date, fair.end_date, fair.organizer, fair.website]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  <p>
                    {[fair.source, fair.external_id].filter(Boolean).join(" · ")}
                    {fair.has_scraper_config ? ` · ${fairLabels.duplicateScraperConfig}` : ""}
                  </p>
                  <p>{counts(fair)}</p>
                  <RadioField
                    id={`keep-${fair.id}`}
                    name={`keep-${key}`}
                    label={fairLabels.duplicateKeep}
                    value={fair.id}
                    checked={chosen.keepId === fair.id}
                    onChange={() => choose(key, "keepId", fair.id)}
                  />
                  <RadioField
                    id={`merge-${fair.id}`}
                    name={`merge-${key}`}
                    label={fairLabels.duplicateMerge}
                    value={fair.id}
                    checked={chosen.mergeId === fair.id}
                    onChange={() => choose(key, "mergeId", fair.id)}
                  />
                </article>
              ))}
            </div>
            <button
              type="button"
              className="btn primary"
              disabled={!chosen.keepId || !chosen.mergeId || busy}
              onClick={() => void requestMerge(key)}
            >
              {fairLabels.duplicateMergeAction}
            </button>
            <button
              type="button"
              className="btn secondary"
              disabled={busy}
              onClick={() => void keepSeparate(group)}
            >
              {fairLabels.duplicateKeepSeparate}
            </button>
          </div>
        );
      })}
      {preview && preview.blocking_conflicts.length > 0 && (
        <Banner variant="error">
          {preview.blocking_conflicts.map((conflict) => conflict.message).join(" ")}
        </Banner>
      )}
      {preview && preview.blocking_conflicts.length === 0 && pending && (
        <p>
          {`Katılım ${preview.participations}, görev ${preview.todos}, teklif ${preview.quotes}, aktivite ${preview.activities}, import ${preview.imports}, scraper ${preview.scraper_runs}, e-posta ${preview.email_batches}, mail ${preview.mail_operations}, operasyon ${preview.operations}.`}
        </p>
      )}
      {pending && (
        <ConfirmDialog
          title={fairLabels.duplicateMergeAction}
          message={fairLabels.duplicateMergeConfirm}
          confirmLabel={fairLabels.duplicateMergeAction}
          variant="danger"
          loading={busy}
          onCancel={() => setPending(null)}
          onConfirm={() => void confirmMerge()}
        />
      )}
    </Card>
  );
}
