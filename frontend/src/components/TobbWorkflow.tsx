import React from "react";
import { ApiError } from "../api/client";
import { applyTobbPreview, bulkTobbDates, cancelTobbRun, decideTobbReview, getTobbRun, listSystemInAppNotifications, listTobbReviews, listTobbRuns, retryTobbRun, type TobbChange, type TobbReview, type TobbRun } from "../api/tobb";
import { tobbLabels as t } from "../labels/tobbLabels";
import { changeTobbMapping, listTobbMappings, retryTobbNotification, type TobbMapping } from "../api/tobb";
import { FairEntitySelect } from "./FairEntitySelect";
import { Banner } from "./ui/Banner";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { EmptyState } from "./ui/EmptyState";
import { FilterPanel } from "./ui/FilterPanel";
import { LoadingState } from "./ui/LoadingState";
import { TableRowActions } from "./ui/TableRowActions";
import { UniversalDataTable } from "./ui/UniversalDataTable";
import { CheckboxField, FormField, SelectInput, TextInput, FormDirtyHost, useReportFormDirty } from "./ui/form";

type Props = {runId: string | null; onRunSelected: (id: string) => void; onChanged: () => void};
const active = new Set(["queued", "running", "cancel_requested", "cancelling"]);

function valueText(values: Record<string, unknown> | undefined): string {
  if (!values) return "—";
  if ("start_date" in values) return [values.start_date, values.end_date].map(value => typeof value === "string" ? value.split("-").reverse().join(".") : "—").join(" – ");
  const displayValue = (value: unknown): string => {
    if (value == null) return "—";
    if (Array.isArray(value)) return value.map(displayValue).join("; ");
    if (typeof value === "object") {
      const row = value as Record<string, unknown>;
      return [row.name, row.city, row.start_date, row.end_date].filter(Boolean).join(" · ") || "—";
    }
    return String(value);
  };
  return Object.entries(values).filter(([key]) => key !== "fair_ids").map(([, value]) => displayValue(value)).join(" · ") || "—";
}

export function TobbWorkflow(props: Props) {
  return <FormDirtyHost onClose={() => {}}><TobbWorkflowInner {...props} /></FormDirtyHost>;
}

function TobbWorkflowInner({runId, onRunSelected, onChanged}: Props) {
  const [reviews, setReviews] = React.useState<TobbReview[]>([]);
  const [history, setHistory] = React.useState<TobbRun[]>([]);
  const [moreHistory, setMoreHistory] = React.useState(false);
  const [mappings, setMappings] = React.useState<TobbMapping[]>([]);
  const [run, setRun] = React.useState<TobbRun | null>(null);
  const [search, setSearch] = React.useState("");
  const [kind, setKind] = React.useState("");
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [targets, setTargets] = React.useState<Record<string, string>>({});
  const [editions, setEditions] = React.useState<Record<string, string>>({});
  const [busy, setBusy] = React.useState(false);
  const [loaded, setLoaded] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [notifications, setNotifications] = React.useState<Awaited<ReturnType<typeof listSystemInAppNotifications>>>([]);
  useReportFormDirty({targets, editions}, {targets: {}, editions: {}});

  const reload = React.useCallback(async () => {
    const [reviewData, runData, mappingData] = await Promise.all([listTobbReviews(), listTobbRuns(), listTobbMappings()]);
    setReviews(reviewData.items);
    setHistory(runData.items);
    setMoreHistory(runData.items.length === 50);
    setMappings(mappingData.items);
    setLoaded(true);
    setSelected(current => new Set([...current].filter(id => reviewData.items.some(item => item.id === id))));
  }, []);

  React.useEffect(() => { void reload().catch(err => {setError(err instanceof Error ? err.message : t.error); setLoaded(true);}); }, [reload]);
  React.useEffect(() => {
    let stopped = false;
    async function poll() {
      try {
        const notices = await listSystemInAppNotifications();
        if (!stopped) setNotifications(notices);
      } catch (err) {
        if (!stopped) setError(err instanceof Error ? err.message : t.error);
      }
    }
    void poll();
    const timer = window.setInterval(() => void poll(), 15000);
    return () => {stopped = true; window.clearInterval(timer);};
  }, []);
  React.useEffect(() => {
    if (!runId) return;
    let stopped = false;
    let timer: number | undefined;
    async function poll() {
      try {
        const current = await getTobbRun(runId!);
        if (stopped) return;
        setRun(current);
        if (active.has(current.status) || current.summary.notification === "pending") timer = window.setTimeout(() => void poll(), 1500);
        else {await reload(); if (current.summary.phase !== "preview_ready") onChanged();}
      } catch (err) {if (!stopped) setError(err instanceof Error ? err.message : t.error);}
    }
    void poll();
    return () => {stopped = true; window.clearTimeout(timer);};
  }, [runId, reload, run?.status, run?.summary.notification]);

  const perform = async (action: () => Promise<unknown>) => {
    if (busy) return;
    setBusy(true); setError(null); setSuccess(null);
    try {await action(); await reload(); onChanged(); setSuccess(t.success);}
    catch (err) {setError(err instanceof ApiError || err instanceof Error ? err.message : t.error); await reload();}
    finally {setBusy(false);}
  };
  const decide = (item: TobbReview, decision: string) => void perform(async () => {
    await decideTobbReview({id: item.id, version: item.version, decision, target_fair_id: targets[item.id] || undefined,
                          source_external_id: editions[item.id] || undefined});
    setTargets(current => {const next = {...current}; delete next[item.id]; return next;});
    setEditions(current => {const next = {...current}; delete next[item.id]; return next;});
  });
  const bulk = (decision: "apply" | "keep") => void perform(async () => {
    const result = await bulkTobbDates(reviews.filter(item => item.kind === "dates" && selected.has(item.id)).map(item => ({id: item.id, version: item.version, decision})));
    const failures = result.items.filter(item => !item.success);
    setSelected(new Set(failures.map(item => item.id)));
    if (failures.length) throw new Error(failures.map(item => `${reviews.find(row => row.id === item.id)?.name}: ${item.error}`).join("; "));
  });
  const visible = reviews.filter(item => (!kind || item.kind === kind) && item.name.toLocaleLowerCase("tr").includes(search.toLocaleLowerCase("tr")));
  const actionButtons = (item: TobbReview) => <TableRowActions>
    {Array.isArray(item.source_row.choices) && <FormField htmlFor={`tobb-edition-${item.id}`} label={t.select}><SelectInput id={`tobb-edition-${item.id}`} value={editions[item.id] ?? ""} onChange={event => setEditions(current => ({...current, [item.id]: event.target.value}))}>
      <option value="">{t.select}</option>{(item.source_row.choices as Record<string, unknown>[]).map(choice => <option key={String(choice.external_id)} value={String(choice.external_id)}>{String(choice.name)} · {String(choice.start_date ?? "—")} – {String(choice.end_date ?? "—")}</option>)}
    </SelectInput></FormField>}
    {["dates", "organizer", "venue", "website"].includes(item.kind) ? <Button variant="link" disabled={busy} onClick={() => decide(item, "apply")}>{t.apply}</Button> : <>
      {item.kind === "edition" ? <Button variant="link" disabled={busy} onClick={() => decide(item, "select")}>{t.select}</Button> : <>
        {item.kind === "city" && <Button variant="link" disabled={busy} onClick={() => decide(item, "same")}>{t.same}</Button>}
        <FormField htmlFor={`tobb-target-${item.id}`} label={t.target}><FairEntitySelect id={`tobb-target-${item.id}`} systemOnly value={targets[item.id] ?? ""} onChange={value => setTargets(current => ({...current, [item.id]: value}))} disabled={busy} /></FormField>
        <Button variant="link" disabled={busy || !targets[item.id]} onClick={() => decide(item, "map")}>{t.map}</Button>
        <Button variant="link" disabled={busy} onClick={() => decide(item, item.kind === "city" ? "different" : "create")}>{item.kind === "city" ? t.different : t.create}</Button>
      </>}
      <Button variant="link" disabled={busy} onClick={() => decide(item, "defer")}>{t.defer}</Button>
    </>}
    <Button variant="link" disabled={busy} onClick={() => decide(item, "keep")}>{t.keep}</Button>
  </TableRowActions>;

  return <Card as="section" aria-label={t.title}>
    <h2>{t.title} ({reviews.length})</h2>
    {error && <Banner variant="error">{error}</Banner>}
    {success && <Banner variant="success">{success}</Banner>}
    <UniversalDataTable items={visible} loading={!loaded} rowKey={item => item.id} emptyState={<EmptyState title={t.empty} />}
      toolbar={<FilterPanel actions={<><Button disabled={busy || !selected.size} onClick={() => bulk("apply")}>{t.bulkApply}</Button><Button disabled={busy || !selected.size} onClick={() => bulk("keep")}>{t.bulkKeep}</Button></>}>
        <FormField htmlFor="tobb-review-search" label={t.search}><TextInput id="tobb-review-search" value={search} onChange={event => setSearch(event.target.value)} /></FormField>
        <FormField htmlFor="tobb-review-kind" label={t.type}><SelectInput id="tobb-review-kind" value={kind} onChange={event => setKind(event.target.value)}><option value="">{t.all} ({reviews.length})</option>{Object.entries(t.kinds).map(([key, label]) => <option key={key} value={key}>{label} ({reviews.filter(item => item.kind === key).length})</option>)}</SelectInput></FormField>
      </FilterPanel>}
      columns={[
        {key: "name", title: t.name, sortable: false, render: item => item.name},
        {key: "selection", title: t.selectRow, sortable: false, render: item => item.kind === "dates" ? <CheckboxField id={`tobb-review-${item.id}`} label={`${t.selectRow}: ${item.name}`} ariaLabel={`${t.selectRow}: ${item.name}`} hideLabel checked={selected.has(item.id)} onChange={checked => setSelected(current => {const next = new Set(current); checked ? next.add(item.id) : next.delete(item.id); return next;})} /> : "—"},
        {key: "kind", title: t.type, sortable: false, render: item => t.kinds[item.kind] ?? item.kind},
        {key: "current", title: t.current, sortable: false, allowWrap: true, render: item => valueText(item.stored_values)},
        {key: "incoming", title: t.incoming, sortable: false, allowWrap: true, render: item => valueText(item.proposed_values)},
        {key: "actions", title: t.actions, sortable: false, render: actionButtons},
      ]} />
    {runId && !run && <LoadingState />}
    {run && <>
      <h3>{run.summary.phase === "preview_ready" ? t.preview : t.details}</h3>
      <p>{t.statuses[run.status] ?? run.status} · {new Date(run.started_at).toLocaleString("tr-TR")} · {run.duration_ms == null ? "—" : `${(run.duration_ms / 1000).toFixed(1)} sn`}</p>
      <p>Bitiş: {run.finished_at ? new Date(run.finished_at).toLocaleString("tr-TR") : "—"}</p>
      <p>{run.progress_current} / {run.progress_total} yıl işlendi</p>
      <TableRowActions>
        {run.summary.phase === "preview_ready" && <Button variant="primary" loading={busy} onClick={() => void perform(async () => {const result = await applyTobbPreview(run.id); setRun(await getTobbRun(result.run.id)); onRunSelected(result.run.id);})}>{t.applySync}</Button>}
        {["queued", "running"].includes(run.status) && <Button disabled={busy} onClick={() => void perform(async () => setRun(await cancelTobbRun(run.id)))}>{t.cancel}</Button>}
        {run.status === "failed" && <Button disabled={busy} onClick={() => void perform(async () => {const result = await retryTobbRun(run.id); setRun(await getTobbRun(result.run.id)); onRunSelected(result.run.id);})}>{t.retry}</Button>}
      </TableRowActions>
      {run.error_message && <Banner variant="error">{run.error_message}</Banner>}
      {run.summary.notification === "pending" && <LoadingState message="Bildirim gönderiliyor…" variant="inline" />}
      {run.summary.notification === "failed" && <Banner variant="warning">{t.notificationError} <Button disabled={busy} onClick={() => void perform(async () => setRun(await retryTobbNotification(run.id)))}>Bildirimi Tekrar Gönder</Button></Banner>}
      {Object.entries(run.summary.year_results).map(([year, result]) => <React.Fragment key={year}>
        <h4>{year} · {t.statuses[result.status] ?? result.status}</h4>
        <p>{result.inserted ?? 0} yeni · {result.updated ?? 0} güncelleme · {result.reviews ?? 0} inceleme · {result.skipped ?? 0} atlandı · {result.attempts} deneme</p>
        {result.error && <Banner variant="error">{result.error}</Banner>}
        <UniversalDataTable<TobbChange> items={result.changes ?? result.details ?? []} rowKey={item => `${item.name}:${item.action}:${item.kind ?? ""}`} columns={[
          {key: "name", title: t.name, sortable: false, render: item => item.name},
          {key: "action", title: t.type, sortable: false, render: item => t.kinds[item.kind ?? ""] ?? t.statuses[item.action] ?? item.action},
          {key: "current", title: t.current, sortable: false, allowWrap: true, render: item => valueText(item.stored_values)},
          {key: "incoming", title: t.incoming, sortable: false, allowWrap: true, render: item => valueText(item.proposed_values ?? item.source)},
        ]} />
      </React.Fragment>)}
    </>}
    <h3>{t.history}</h3>
    <UniversalDataTable items={history} rowKey={item => item.id} columns={[
      {key: "started_at", title: "Başlangıç", sortable: false, render: item => new Date(item.started_at).toLocaleString("tr-TR")},
      {key: "source", title: "Başlatan", sortable: false, render: item => item.summary.requested_by_label ?? (item.run_source === "tobb_weekly" ? "Sistem" : "Super Admin")},
      {key: "years", title: "Yıllar", sortable: false, render: item => item.summary.years.join(", ")},
      {key: "status", title: "Durum", sortable: false, render: item => item.summary.phase === "preview_ready" ? t.preview : t.statuses[item.status]},
      {key: "actions", title: t.actions, sortable: false, render: item => <TableRowActions><Button variant="link" onClick={() => onRunSelected(item.id)}>{t.details}</Button></TableRowActions>},
    ]} />
    {moreHistory && <Button disabled={busy} onClick={() => {
      setBusy(true);
      void listTobbRuns(history.length).then(data => {
        setHistory(current => [...new Map([...current, ...data.items].map(item => [item.id, item])).values()]);
        setMoreHistory(data.items.length === 50);
      }).catch(err => setError(err instanceof Error ? err.message : t.error)).finally(() => setBusy(false));
    }}>Önceki Çalışmaları Göster</Button>}
    {mappings.length > 0 && <><h3>Onaylanmış TOBB eşleştirmeleri</h3><UniversalDataTable items={mappings} rowKey={item => item.id} columns={[
      {key: "name", title: t.name, sortable: false, render: item => item.name},
      {key: "identity_name", title: t.incoming, sortable: false, render: item => `${item.identity_name} · ${item.city}`},
      {key: "actions", title: t.actions, sortable: false, render: item => <TableRowActions>
        <FormField htmlFor={`tobb-mapping-${item.id}`} label={t.target}><FairEntitySelect id={`tobb-mapping-${item.id}`} systemOnly value={targets[`mapping-${item.id}`] ?? ""} onChange={value => setTargets(current => ({...current, [`mapping-${item.id}`]: value}))} /></FormField>
        <Button variant="link" disabled={busy || !targets[`mapping-${item.id}`]} onClick={() => void perform(async () => {
          await changeTobbMapping(item.id, targets[`mapping-${item.id}`]);
          setTargets(current => {const next = {...current}; delete next[`mapping-${item.id}`]; return next;});
        })}>{t.map}</Button>
      </TableRowActions>},
    ]} /></>}
    {notifications.length > 0 && <><h3>{t.notifications}</h3>{notifications.map(item => <Banner key={item.id} variant="info">{item.subject} {item.body} {item.variables?.run_id && <Button variant="link" onClick={() => onRunSelected(item.variables!.run_id!)}>{t.details}</Button>}</Banner>)}</>}
  </Card>;
}
