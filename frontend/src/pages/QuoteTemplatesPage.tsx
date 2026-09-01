import React from "react";
import {
  createQuoteTemplate,
  fetchManagedQuoteTemplateLogo,
  isManagedQuoteTemplateLogoUrl,
  listQuoteTemplates,
  updateQuoteTemplate,
  uploadQuoteTemplateLogo,
} from "../api/quoteTemplates";
import { Banner } from "../components/ui/Banner";
import { EmptyState } from "../components/ui/EmptyState";
import { FormField, FormModal, TextareaInput, TextInput } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import type { QuoteTemplate, QuoteTemplatePayload } from "../types/quoteTemplates";
import {
  getGrantedQuoteTemplatePermissions,
  QUOTE_TEMPLATE_PERMISSION_CREATE,
  QUOTE_TEMPLATE_PERMISSION_READ,
  QUOTE_TEMPLATE_PERMISSION_UPDATE,
} from "../permissions/quoteTemplatePermissions";

const empty: QuoteTemplatePayload = { name: "", logo_url: null, source_code: "" };

function QuoteTemplateLogo({
  src,
  alt,
  style,
}: {
  src: string;
  alt: string;
  style: React.CSSProperties;
}) {
  const [resolvedSrc, setResolvedSrc] = React.useState<string | null>(
    isManagedQuoteTemplateLogoUrl(src) ? null : src,
  );

  React.useEffect(() => {
    if (!isManagedQuoteTemplateLogoUrl(src)) {
      setResolvedSrc(src);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;
    setResolvedSrc(null);
    void fetchManagedQuoteTemplateLogo(src)
      .then((blob) => {
        const nextUrl = URL.createObjectURL(blob);
        if (cancelled) {
          URL.revokeObjectURL(nextUrl);
          return;
        }
        objectUrl = nextUrl;
        setResolvedSrc(nextUrl);
      })
      .catch(() => {
        if (!cancelled) setResolvedSrc(null);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src]);

  return resolvedSrc ? <img src={resolvedSrc} alt={alt} style={style} /> : null;
}

export function QuoteTemplatesPage() {
  const permissions = React.useMemo(() => getGrantedQuoteTemplatePermissions(), []);
  const canRead = permissions.has(QUOTE_TEMPLATE_PERMISSION_READ);
  const canCreate = permissions.has(QUOTE_TEMPLATE_PERMISSION_CREATE);
  const canUpdate = permissions.has(QUOTE_TEMPLATE_PERMISSION_UPDATE);
  const [items, setItems] = React.useState<QuoteTemplate[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [editing, setEditing] = React.useState<QuoteTemplate | null | undefined>(undefined);
  const [values, setValues] = React.useState<QuoteTemplatePayload>(empty);
  const [saving, setSaving] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const canSaveTemplate = editing ? canUpdate : canCreate;
  const canUploadLogo = canCreate || canUpdate;

  const load = React.useCallback(async () => {
    if (!canRead) { setItems([]); setLoading(false); setError("Teklif şablonlarını görüntüleme yetkiniz yok."); return; }
    setLoading(true); setError(null);
    try { setItems((await listQuoteTemplates()).items); }
    catch { setError("Teklif şablonları yüklenemedi."); }
    finally { setLoading(false); }
  }, [canRead]);
  React.useEffect(() => { void load(); }, [load]);

  const openCreate = () => { setValues(empty); setEditing(null); };
  const openEdit = (item: QuoteTemplate) => { setValues({ name: item.name, logo_url: item.logo_url, source_code: item.source_code }); setEditing(item); };
  const close = () => setEditing(undefined);
  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSaveTemplate) return;
    if (!values.name.trim() || !values.source_code.trim()) { setError("Şablon adı ve HTML/CSS source code zorunludur."); return; }
    setSaving(true); setError(null);
    try { editing ? await updateQuoteTemplate(editing.id, values) : await createQuoteTemplate(values); close(); await load(); }
    catch { setError("Teklif şablonu kaydedilemedi."); }
    finally { setSaving(false); }
  };
  const upload = async (file?: File) => {
    if (!canUploadLogo || !file) return;
    setUploading(true);
    try {
      const result = await uploadQuoteTemplateLogo(file);
      setValues((current) => ({ ...current, logo_url: result.url }));
    }
    catch { setError("Logo yüklenemedi."); }
    finally { setUploading(false); }
  };
  const columns: UniversalDataTableColumn<QuoteTemplate>[] = [
    { key: "name", title: "Şablon Adı", sortable: true, render: (item) => item.name },
    { key: "version", title: "Versiyon", sortable: true, render: (item) => `v${item.version_number}` },
    { key: "logo", title: "Logo", render: (item) => item.logo_url ? <QuoteTemplateLogo src={item.logo_url} alt="" style={{ maxHeight: 36, maxWidth: 120 }} /> : "—" },
    { key: "updated", title: "Güncellendi", sortable: true, render: (item) => new Date(item.updated_at).toLocaleString("tr-TR") },
    { key: "actions", title: "İşlemler", render: (item) => canUpdate ? <button type="button" className="btn secondary" onClick={() => openEdit(item)}>Düzenle</button> : "—" },
  ];

  return <PageShell className="quote-templates-page">
    <PageHeader title="Teklif Şablonları" subtitle="Tekliflerde kullanılacak versiyonlu HTML/CSS şablonlarını yönetin" actions={canCreate ? <button type="button" className="btn primary" onClick={openCreate}>+ Şablon Ekle</button> : null} />
    {error ? <Banner variant="error">{error}</Banner> : null}
    <UniversalDataTable items={items} columns={columns} rowKey={(item) => item.id} loading={loading} onRetry={() => void load()} emptyState={<EmptyState title="Henüz teklif şablonu yok" description="İlk teklif şablonunuzu oluşturun." actionLabel={canCreate ? "+ Şablon Ekle" : undefined} onAction={canCreate ? openCreate : undefined} />} />
    {editing !== undefined ? <FormModal title={editing ? "Teklif Şablonunu Düzenle" : "Yeni Teklif Şablonu"} onClose={close} size="lg">
      <form className="crm-form" onSubmit={save}>
        <FormField label="Şablon adı" htmlFor="quote-template-name"><TextInput id="quote-template-name" value={values.name} onChange={(e) => setValues({ ...values, name: e.target.value })} /></FormField>
        <FormField label="Logo" htmlFor="quote-template-logo" hint={values.logo_url ? "Yüklü logo seçildi. Yeni dosya seçerek değiştirebilirsiniz." : "PNG, JPG, SVG veya WebP; en fazla 5 MB."}>
          <input id="quote-template-logo" className="form-control" type="file" accept="image/png,image/jpeg,image/svg+xml,image/webp" disabled={uploading || !canUploadLogo} onChange={(e) => void upload(e.target.files?.[0])} />
        </FormField>
        {values.logo_url ? <QuoteTemplateLogo src={values.logo_url} alt="Şablon logosu" style={{ maxHeight: 72, maxWidth: 240, objectFit: "contain" }} /> : null}
        <FormField label="HTML/CSS Source Code" htmlFor="quote-template-source"><TextareaInput id="quote-template-source" rows={18} spellCheck={false} className="code-editor" value={values.source_code} onChange={(e) => setValues({ ...values, source_code: e.target.value })} /></FormField>
        {editing ? <Banner variant="info">Kaydettiğinizde mevcut sürüm korunur ve v{editing.version_number + 1} oluşturulur.</Banner> : null}
        <div className="form-actions"><button type="button" className="btn secondary" onClick={close}>İptal</button>{canSaveTemplate ? <button type="submit" className="btn primary" disabled={saving || uploading}>{saving ? "Kaydediliyor…" : "Kaydet"}</button> : null}</div>
      </form>
    </FormModal> : null}
  </PageShell>;
}
