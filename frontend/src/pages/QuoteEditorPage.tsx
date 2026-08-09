import React from "react";
import { getTodo } from "../api/todos";
import { getCustomer } from "../api/customers";
import { getFair } from "../api/fairs";
import { listQuoteTemplates } from "../api/quoteTemplates";
import { listTemplateContents, listTemplateContentTags } from "../api/templateContents";
import { createQuoteByTodo, getQuoteByTodo, renderQuoteByTodo, updateQuoteByTodo } from "../api/quotes";
import { Banner } from "../components/ui/Banner";
import { LoadingState } from "../components/ui/LoadingState";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { Card } from "../components/ui/Card";
import { FormField, FormGrid, SelectInput, TextInput } from "../components/ui/form";
import { getQuotePermissions, QUOTE_CREATE, QUOTE_READ, QUOTE_UPDATE } from "../permissions/quotePermissions";
import type { QuoteSelectedItem } from "../types/quote";

interface Props { todoId: string; onBack: () => void }

export function QuoteEditorPage({ todoId, onBack }: Props) {
  const permissions = React.useMemo(getQuotePermissions, []);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [todo, setTodo] = React.useState<any>(null);
  const [customer, setCustomer] = React.useState<any>(null);
  const [fair, setFair] = React.useState<any>(null);
  const [templates, setTemplates] = React.useState<any[]>([]);
  const [tags, setTags] = React.useState<any[]>([]);
  const [contents, setContents] = React.useState<any[]>([]);
  const [existing, setExisting] = React.useState(false);
  const [templateId, setTemplateId] = React.useState("");
  const [quoteDate, setQuoteDate] = React.useState(() => new Date().toISOString().slice(0, 10));
  const [status, setStatus] = React.useState<"draft" | "given">("draft");
  const [selected, setSelected] = React.useState<Record<string, string>>({});
  const [preview, setPreview] = React.useState("");
  const previewRef = React.useRef<HTMLIFrameElement>(null);

  React.useEffect(() => { void (async () => {
    if (!permissions.has(QUOTE_READ)) { setError("Teklifleri görüntüleme yetkiniz yok."); setLoading(false); return; }
    try {
      const task = await getTodo(todoId);
      if (task.category !== "teklif" || !task.customer_id || !task.source_fair_id) throw new Error("Bu görev geçerli bir teklif görevi değil.");
      const [cust, fairResult, templateResult, tagResult, contentResult, quote] = await Promise.all([
        getCustomer(task.customer_id), getFair(task.source_fair_id), listQuoteTemplates(), listTemplateContentTags(), listTemplateContents(), getQuoteByTodo(todoId),
      ]);
      setTodo(task); setCustomer(cust); setFair(fairResult); setTemplates(templateResult.items); setTags(tagResult.items); setContents(contentResult.items);
      setTemplateId(quote?.template_id ?? templateResult.items[0]?.id ?? "");
      if (quote) { setExisting(true); setQuoteDate(quote.quote_date); setStatus(quote.status); setSelected(Object.fromEntries(quote.selected_items.map((item) => [item.content_id, item.value]))); setPreview((await renderQuoteByTodo(todoId)).html); }
    } catch (err) { setError(err instanceof Error ? err.message : "Teklif bilgileri yüklenemedi."); }
    finally { setLoading(false); }
  })(); }, [todoId, permissions]);

  const toggle = (id: string, checked: boolean) => setSelected((current) => { const next = { ...current }; if (checked) next[id] = next[id] || "VAR"; else delete next[id]; return next; });
  const save = async () => {
    const allowed = existing ? permissions.has(QUOTE_UPDATE) : permissions.has(QUOTE_CREATE);
    if (!allowed) { setError("Teklifi kaydetme yetkiniz yok."); return; }
    if (!templateId) { setError("Teklif şablonu seçin."); return; }
    const selected_items: QuoteSelectedItem[] = Object.entries(selected).map(([content_id, value]) => ({ content_id, value: value.trim() })).filter((item) => item.value);
    setSaving(true); setError(null);
    try { const payload = { template_id: templateId, quote_date: quoteDate, status, selected_items }; if (existing) await updateQuoteByTodo(todoId, payload); else await createQuoteByTodo(todoId, payload); setExisting(true); setPreview((await renderQuoteByTodo(todoId)).html); }
    catch (err) { setError(err instanceof Error ? err.message : "Teklif kaydedilemedi."); }
    finally { setSaving(false); }
  };

  if (loading) return <LoadingState />;
  return <PageShell>
    <PageHeader title="Teklif Hazırlama" subtitle={todo ? `${customer?.display_name} · ${fair?.name}` : ""} actions={<><button className="btn secondary" onClick={onBack}>Göreve Dön</button><button className="btn primary" onClick={() => void save()} disabled={saving}>{saving ? "Kaydediliyor..." : "Kaydet ve Önizle"}</button></>} />
    {error ? <Banner variant="error">{error}</Banner> : null}
    <Card><FormGrid>
      <FormField label="Teklif şablonu" htmlFor="quote-template" required><SelectInput id="quote-template" value={templateId} onChange={(e) => setTemplateId(e.target.value)}>{templates.map((item) => <option key={item.id} value={item.id}>{item.name} (v{item.version_number})</option>)}</SelectInput></FormField>
      <FormField label="Teklif tarihi" htmlFor="quote-date" required><TextInput id="quote-date" type="date" value={quoteDate} onChange={(e) => setQuoteDate(e.target.value)} /></FormField>
      <FormField label="Durum" htmlFor="quote-status"><SelectInput id="quote-status" value={status} onChange={(e) => setStatus(e.target.value as "draft" | "given")}><option value="draft">Taslak</option><option value="given">Teklif Verildi</option></SelectInput></FormField>
    </FormGrid></Card>
    {tags.map((tag) => <Card key={tag.id}><h3>{tag.name}</h3>{contents.filter((item) => item.tag_id === tag.id).map((item) => <div key={item.id} className="form-grid" style={{gridTemplateColumns:"40px 1fr 1fr",alignItems:"center",marginBottom:8}}><input type="checkbox" checked={Object.prototype.hasOwnProperty.call(selected, item.id)} onChange={(e) => toggle(item.id, e.target.checked)} aria-label={`${item.title} seç`} /><span>{item.title}</span><TextInput id={`quote-content-${item.id}`} value={selected[item.id] ?? ""} disabled={!Object.prototype.hasOwnProperty.call(selected, item.id)} placeholder="VAR / 1 ADET" onChange={(e) => setSelected((current) => ({ ...current, [item.id]: e.target.value }))} /></div>)}</Card>)}
    {preview ? <Card><div className="form-actions"><h3 style={{marginRight:"auto"}}>Önizleme</h3><button className="btn secondary" onClick={() => previewRef.current?.contentWindow?.print()}>Yazdır / PDF</button></div><iframe ref={previewRef} title="Teklif önizleme" srcDoc={preview} style={{width:"100%",height:"900px",border:"1px solid #d8deea",background:"white"}} /></Card> : null}
  </PageShell>;
}
