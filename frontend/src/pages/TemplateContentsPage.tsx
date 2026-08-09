import React from "react";
import {
  createTemplateContent, createTemplateContentTag, deleteTemplateContent,
  deleteTemplateContentTag, listTemplateContents, listTemplateContentTags,
  updateTemplateContent, updateTemplateContentTag,
} from "../api/templateContents";
import { Banner } from "../components/ui/Banner";
import { EmptyState } from "../components/ui/EmptyState";
import { FormField, FormModal, SelectInput, TextInput } from "../components/ui/form";
import { PageHeader } from "../components/ui/PageHeader";
import { PageShell } from "../components/ui/PageShell";
import { UniversalDataTable, type UniversalDataTableColumn } from "../components/ui/UniversalDataTable";
import {
  getGrantedTemplateContentPermissions, TEMPLATE_CONTENT_PERMISSION_CREATE,
  TEMPLATE_CONTENT_PERMISSION_DELETE, TEMPLATE_CONTENT_PERMISSION_READ,
  TEMPLATE_CONTENT_PERMISSION_UPDATE,
} from "../permissions/templateContentPermissions";
import type { TemplateContent, TemplateContentTag } from "../types/templateContents";

export function TemplateContentsPage() {
  const permissions = React.useMemo(() => getGrantedTemplateContentPermissions(), []);
  const canRead = permissions.has(TEMPLATE_CONTENT_PERMISSION_READ);
  const canCreate = permissions.has(TEMPLATE_CONTENT_PERMISSION_CREATE);
  const canUpdate = permissions.has(TEMPLATE_CONTENT_PERMISSION_UPDATE);
  const canDelete = permissions.has(TEMPLATE_CONTENT_PERMISSION_DELETE);
  const [section, setSection] = React.useState<"tags" | "contents">("tags");
  const [tags, setTags] = React.useState<TemplateContentTag[]>([]);
  const [contents, setContents] = React.useState<TemplateContent[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<"tag" | "content" | null>(null);
  const [editingTag, setEditingTag] = React.useState<TemplateContentTag | null>(null);
  const [editingContent, setEditingContent] = React.useState<TemplateContent | null>(null);
  const [tagName, setTagName] = React.useState("");
  const [contentValues, setContentValues] = React.useState({ tag_id: "", title: "" });
  const [saving, setSaving] = React.useState(false);
  const [tagSorting, setTagSorting] = React.useState<{ field: string; direction: "asc" | "desc" }>({ field: "created_at", direction: "desc" });
  const [contentSorting, setContentSorting] = React.useState<{ field: string; direction: "asc" | "desc" }>({ field: "created_at", direction: "desc" });

  const load = React.useCallback(async () => {
    if (!canRead) { setError("Şablon içeriklerini görüntüleme yetkiniz yok."); setLoading(false); return; }
    setLoading(true); setError(null);
    try {
      const [tagResult, contentResult] = await Promise.all([listTemplateContentTags(), listTemplateContents()]);
      setTags(tagResult.items); setContents(contentResult.items);
    } catch { setError("Şablon içerikleri yüklenemedi."); }
    finally { setLoading(false); }
  }, [canRead]);
  React.useEffect(() => { void load(); }, [load]);

  const openTag = () => { setEditingTag(null); setTagName(""); setModal("tag"); };
  const editTag = (tag: TemplateContentTag) => { setEditingTag(tag); setTagName(tag.name); setModal("tag"); };
  const openContent = () => { setEditingContent(null); setContentValues({ tag_id: tags[0]?.id ?? "", title: "" }); setModal("content"); };
  const editContent = (item: TemplateContent) => { setEditingContent(item); setContentValues({ tag_id: item.tag_id, title: item.title }); setModal("content"); };

  const saveTag = async (event: React.FormEvent) => {
    event.preventDefault(); if (!tagName.trim()) return; setSaving(true); setError(null);
    try { editingTag ? await updateTemplateContentTag(editingTag.id, tagName.trim()) : await createTemplateContentTag(tagName.trim()); setModal(null); await load(); }
    catch { setError("İçerik etiketi kaydedilemedi."); }
    finally { setSaving(false); }
  };
  const saveContent = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!contentValues.tag_id || !contentValues.title.trim()) { setError("Etiket ve başlık zorunludur."); return; }
    setSaving(true); setError(null);
    try { editingContent ? await updateTemplateContent(editingContent.id, contentValues) : await createTemplateContent(contentValues); setModal(null); await load(); }
    catch { setError("İçerik kaydedilemedi."); }
    finally { setSaving(false); }
  };
  const removeTag = async (tag: TemplateContentTag) => {
    if (!window.confirm(`“${tag.name}” etiketi silinsin mi?`)) return;
    try { await deleteTemplateContentTag(tag.id); await load(); }
    catch { setError("Bağlı içeriği bulunan etiket silinemez."); }
  };
  const removeContent = async (item: TemplateContent) => {
    if (!window.confirm(`“${item.title}” içeriği silinsin mi?`)) return;
    try { await deleteTemplateContent(item.id); await load(); }
    catch { setError("İçerik silinemedi."); }
  };

  const changeTagSort = (field: string) => setTagSorting((current) => ({
    field,
    direction: current.field === field && current.direction === "asc" ? "desc" : "asc",
  }));
  const changeContentSort = (field: string) => setContentSorting((current) => ({
    field,
    direction: current.field === field && current.direction === "asc" ? "desc" : "asc",
  }));
  const sortedTags = React.useMemo(() => [...tags].sort((left, right) => {
    const result = tagSorting.field === "created_at"
      ? new Date(left.created_at).getTime() - new Date(right.created_at).getTime()
      : left.name.localeCompare(right.name, "tr", { sensitivity: "base" });
    return tagSorting.direction === "asc" ? result : -result;
  }), [tags, tagSorting]);
  const sortedContents = React.useMemo(() => [...contents].sort((left, right) => {
    const result = contentSorting.field === "created_at"
      ? new Date(left.created_at).getTime() - new Date(right.created_at).getTime()
      : contentSorting.field === "tag_name"
        ? left.tag_name.localeCompare(right.tag_name, "tr", { sensitivity: "base" })
        : left.title.localeCompare(right.title, "tr", { sensitivity: "base" });
    return contentSorting.direction === "asc" ? result : -result;
  }), [contents, contentSorting]);

  const tagColumns: UniversalDataTableColumn<TemplateContentTag>[] = [
    { key: "name", title: "Etiket Adı", sortable: true, render: (item) => item.name },
    { key: "created_at", title: "Oluşturuldu", sortable: true, render: (item) => new Date(item.created_at).toLocaleString("tr-TR") },
    { key: "actions", title: "İşlemler", sortable: false, render: (item) => <div className="form-actions">{canUpdate ? <button type="button" className="btn secondary" onClick={() => editTag(item)}>Düzenle</button> : null}{canDelete ? <button type="button" className="btn danger" onClick={() => void removeTag(item)}>Sil</button> : null}</div> },
  ];
  const contentColumns: UniversalDataTableColumn<TemplateContent>[] = [
    { key: "title", title: "Başlık", sortable: true, render: (item) => item.title },
    { key: "tag_name", title: "Etiket", sortable: true, render: (item) => item.tag_name },
    { key: "created_at", title: "Oluşturuldu", sortable: true, render: (item) => new Date(item.created_at).toLocaleString("tr-TR") },
    { key: "actions", title: "İşlemler", sortable: false, render: (item) => <div className="form-actions">{canUpdate ? <button type="button" className="btn secondary" onClick={() => editContent(item)}>Düzenle</button> : null}{canDelete ? <button type="button" className="btn danger" onClick={() => void removeContent(item)}>Sil</button> : null}</div> },
  ];

  const action = canCreate ? <button type="button" className="btn primary" onClick={section === "tags" ? openTag : openContent} disabled={section === "contents" && tags.length === 0}>{section === "tags" ? "+ Etiket Ekle" : "+ İçerik Ekle"}</button> : null;
  return <PageShell className="template-contents-page">
    <PageHeader title="Şablon İçerikleri" subtitle="Tekliflerde tekrar kullanılacak etiketli içerikleri yönetin" actions={action} />
    <div className="form-actions" role="tablist" aria-label="Şablon içeriği bölümleri"><button type="button" className={`btn ${section === "tags" ? "primary" : "secondary"}`} onClick={() => setSection("tags")}>İçerik Etiketleri</button><button type="button" className={`btn ${section === "contents" ? "primary" : "secondary"}`} onClick={() => setSection("contents")}>İçerikler</button></div>
    {error ? <Banner variant="error">{error}</Banner> : null}
    {section === "tags" ? <UniversalDataTable items={sortedTags} columns={tagColumns} rowKey={(item) => item.id} loading={loading} sorting={tagSorting} onSortChange={changeTagSort} emptyState={<EmptyState title="Henüz içerik etiketi yok" description="İçerikleri gruplamak için ilk etiketi oluşturun." actionLabel={canCreate ? "+ Etiket Ekle" : undefined} onAction={canCreate ? openTag : undefined} />} /> : <UniversalDataTable items={sortedContents} columns={contentColumns} rowKey={(item) => item.id} loading={loading} sorting={contentSorting} onSortChange={changeContentSort} emptyState={<EmptyState title="Henüz içerik yok" description={tags.length ? "İlk etiketli içeriğinizi oluşturun." : "Önce bir içerik etiketi oluşturun."} actionLabel={canCreate && tags.length ? "+ İçerik Ekle" : undefined} onAction={canCreate && tags.length ? openContent : undefined} />}/>} 
    {modal === "tag" ? <FormModal title={editingTag ? "İçerik Etiketini Düzenle" : "Yeni İçerik Etiketi"} onClose={() => setModal(null)}><form className="crm-form" onSubmit={saveTag}><FormField label="Etiket adı" htmlFor="content-tag-name"><TextInput id="content-tag-name" value={tagName} onChange={(e) => setTagName(e.target.value)} /></FormField><div className="form-actions"><button type="button" className="btn secondary" onClick={() => setModal(null)}>İptal</button><button type="submit" className="btn primary" disabled={saving}>Kaydet</button></div></form></FormModal> : null}
    {modal === "content" ? <FormModal title={editingContent ? "İçeriği Düzenle" : "Yeni İçerik"} onClose={() => setModal(null)}><form className="crm-form" onSubmit={saveContent}><FormField label="İçerik etiketi" htmlFor="content-tag"><SelectInput id="content-tag" value={contentValues.tag_id} onChange={(e) => setContentValues({ ...contentValues, tag_id: e.target.value })}><option value="">Etiket seçin</option>{tags.map((tag) => <option key={tag.id} value={tag.id}>{tag.name}</option>)}</SelectInput></FormField><FormField label="Başlık" htmlFor="content-title"><TextInput id="content-title" value={contentValues.title} onChange={(e) => setContentValues({ ...contentValues, title: e.target.value })} /></FormField><div className="form-actions"><button type="button" className="btn secondary" onClick={() => setModal(null)}>İptal</button><button type="submit" className="btn primary" disabled={saving}>Kaydet</button></div></form></FormModal> : null}
  </PageShell>;
}
