import React from "react";
import { getTodo } from "../api/todos";
import { getCustomer } from "../api/customers";
import { getFair } from "../api/fairs";
import { listQuoteTemplates } from "../api/quoteTemplates";
import { listTemplateContents, listTemplateContentTags } from "../api/templateContents";
import { createQuoteByTodo, getQuoteByTodo, renderQuoteByTodo, updateQuoteByTodo } from "../api/quotes";
import { Banner } from "../components/ui/Banner";
import { LoadingState } from "../components/ui/LoadingState";
import { Modal } from "../components/ui/Modal";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { Card } from "../components/ui/Card";
import { FormField, FormGrid, SelectInput, TextInput } from "../components/ui/form";
import { getQuotePermissions, QUOTE_CREATE, QUOTE_READ, QUOTE_UPDATE } from "../permissions/quotePermissions";
import type { QuoteSelectedItem } from "../types/quote";

interface Props { todoId: string; onBack: () => void }

const NEW_QUOTE_DEFAULTS: Record<string, string> = {
  "KİRALIK STANT TİPİ": "Maksima",
  "STANT ALANI": "",
  "STANT YÜKSEKLİĞİ": "3.5 Metre",
  "ZEMİN": "PARKE",
  "ASKILIK": "VAR",
  "DEPO": "VAR",
  "DEPO İÇİ RAF": "VAR",
  "KETTLE": "VAR",
  "MİNİ BUZDOLABI": "VAR",
  "ÇÖP KOVASI": "VAR",
};

function buildNewQuoteDefaults(items: any[]): Record<string, string> {
  const defaults: Record<string, string> = {};
  for (const item of items) {
    const title = String(item.title ?? "").trim().toLocaleUpperCase("tr-TR");
    if (Object.prototype.hasOwnProperty.call(NEW_QUOTE_DEFAULTS, title)) {
      defaults[item.id] = NEW_QUOTE_DEFAULTS[title];
    }
  }
  return defaults;
}

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
  const [price, setPrice] = React.useState("");
  const [selected, setSelected] = React.useState<Record<string, string>>({});
  const [preview, setPreview] = React.useState("");
  const [previewOpen, setPreviewOpen] = React.useState(false);
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
      if (quote) {
        setExisting(true);
        setQuoteDate(quote.quote_date);
        setStatus(quote.status);
        setPrice(quote.price ?? "");
        setSelected(Object.fromEntries(quote.selected_items.map((item) => [item.content_id, item.value])));
        try {
          setPreview((await renderQuoteByTodo(todoId)).html);
        } catch {
          setPreview("");
        }
      } else {
        setSelected(buildNewQuoteDefaults(contentResult.items));
      }
    } catch (err) { setError(err instanceof Error ? err.message : "Teklif bilgileri yüklenemedi."); }
    finally { setLoading(false); }
  })(); }, [todoId, permissions]);

  const toggle = (id: string, checked: boolean) => setSelected((current) => { const next = { ...current }; if (checked) next[id] = next[id] || "VAR"; else delete next[id]; return next; });
  const save = async () => {
    const allowed = existing ? permissions.has(QUOTE_UPDATE) : permissions.has(QUOTE_CREATE);
    if (!allowed) { setError("Teklifi kaydetme yetkiniz yok."); return; }
    if (!templateId) { setError("Teklif şablonu seçin."); return; }

    const standArea = contents.find((item) => String(item.title ?? "").trim().toLocaleUpperCase("tr-TR") === "STANT ALANI");
    if (standArea && Object.prototype.hasOwnProperty.call(selected, standArea.id) && !selected[standArea.id].trim()) {
      setError("Stand Alanı değerini girin.");
      return;
    }

    const selected_items: QuoteSelectedItem[] = Object.entries(selected).map(([content_id, value]) => ({ content_id, value: value.trim() })).filter((item) => item.value);
    setSaving(true); setError(null);
    try {
      const payload = { template_id: templateId, quote_date: quoteDate, status, price: price.trim(), selected_items };
      if (existing) await updateQuoteByTodo(todoId, payload); else await createQuoteByTodo(todoId, payload);
      setExisting(true);

      try {
        const rendered = await renderQuoteByTodo(todoId);
        setPreview(rendered.html);
        setPreviewOpen(true);
      } catch (err) {
        setError(err instanceof Error ? `Teklif kaydedildi ancak önizleme oluşturulamadı: ${err.message}` : "Teklif kaydedildi ancak önizleme oluşturulamadı.");
      }
    }
    catch (err) { setError(err instanceof Error ? err.message : "Teklif kaydedilemedi."); }
    finally { setSaving(false); }
  };

  if (loading) return <LoadingState />;
  return <PageShell>
    <PageHeader title="Teklif Hazırlama" subtitle={todo ? `${customer?.display_name} · ${fair?.name}` : ""} actions={<><button type="button" className="btn secondary" onClick={onBack}>Göreve Dön</button><button type="button" className="btn primary" onClick={() => void save()} disabled={saving}>{saving ? "Kaydediliyor..." : "Kaydet ve Önizle"}</button></>} />
    {error ? <Banner variant="error">{error}</Banner> : null}
    <Card><FormGrid>
      <FormField label="Teklif şablonu" htmlFor="quote-template" required><SelectInput id="quote-template" value={templateId} onChange={(e) => setTemplateId(e.target.value)}>{templates.map((item) => <option key={item.id} value={item.id}>{item.name} (v{item.version_number})</option>)}</SelectInput></FormField>
      <FormField label="Teklif tarihi" htmlFor="quote-date" required><TextInput id="quote-date" type="date" value={quoteDate} onChange={(e) => setQuoteDate(e.target.value)} /></FormField>
      <FormField label="Durum" htmlFor="quote-status"><SelectInput id="quote-status" value={status} onChange={(e) => setStatus(e.target.value as "draft" | "given")}><option value="draft">Taslak</option><option value="given">Teklif Verildi</option></SelectInput></FormField>
      <FormField label="Stand Bedeli" htmlFor="quote-price"><TextInput id="quote-price" value={price} maxLength={255} placeholder="125.000 TL + %20 KDV" onChange={(e) => setPrice(e.target.value)} /></FormField>
    </FormGrid></Card>
    {tags.map((tag) => <Card key={tag.id}><h3>{tag.name}</h3>{contents.filter((item) => item.tag_id === tag.id).map((item) => <div key={item.id} className="form-grid" style={{gridTemplateColumns:"40px 1fr 1fr",alignItems:"center",marginBottom:8}}><input type="checkbox" checked={Object.prototype.hasOwnProperty.call(selected, item.id)} onChange={(e) => toggle(item.id, e.target.checked)} aria-label={`${item.title} seç`} /><span>{item.title}</span><TextInput id={`quote-content-${item.id}`} value={selected[item.id] ?? ""} disabled={!Object.prototype.hasOwnProperty.call(selected, item.id)} placeholder="VAR / 1 ADET" onChange={(e) => setSelected((current) => ({ ...current, [item.id]: e.target.value }))} /></div>)}</Card>)}
    {preview ? <Card><div className="form-actions"><h3 style={{marginRight:"auto"}}>Önizleme</h3><button type="button" className="btn secondary" onClick={() => setPreviewOpen(true)}>Önizlemeyi Aç</button></div></Card> : null}
    {previewOpen && preview ? <Modal title="Teklif Önizleme" onClose={() => setPreviewOpen(false)} size="lg" footer={<><button type="button" className="btn secondary" onClick={() => setPreviewOpen(false)}>Kapat</button><button type="button" className="btn primary" onClick={() => previewRef.current?.contentWindow?.print()}>Yazdır / PDF</button></>}>
      <iframe ref={previewRef} title="Teklif önizleme" srcDoc={preview} style={{width:"100%",height:"75vh",border:"1px solid #d8deea",background:"white"}} />
    </Modal> : null}
  </PageShell>;
}
