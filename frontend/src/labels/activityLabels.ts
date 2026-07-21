import type { ActivitySource, ActivityStatus, ActivityType } from "../types/activity";

export const activityLabels = {
  tabActivities: "Aktiviteler",
  pageTitle: "Aktiviteler",
  pageSubtitle: "Tüm müşteri aktiviteleri",
  newActivity: "Yeni Aktivite Ekle",
  editActivity: "Aktivite Düzenle",
  detailTitle: "Aktivite Detayı",
  view: "Görüntüle",
  type: "Aktivite Türü",
  status: "Durum",
  source: "Kaynak",
  subject: "Konu",
  description: "Açıklama",
  activityDate: "Aktivite Tarihi",
  followUpDate: "Takip Tarihi",
  createdAt: "Oluşturulma Tarihi",
  contact: "İlgili Kişi",
  customer: "Müşteri",
  relatedTodo: "İlgili Görev",
  relatedOutcome: "Sonuç",
  actionRequired: "Aksiyon Gerekli",
  dataProblem: "Veri Problemi",
  yes: "Evet",
  no: "Hayır",
  save: "Kaydet",
  cancel: "İptal",
  edit: "Düzenle",
  delete: "Sil",
  deleteSelected: "Seçilenleri Sil",
  actions: "İşlemler",
  noActivities: "Henüz aktivite bulunmuyor.",
  deleteConfirm: "Bu aktiviteyi kalıcı olarak silmek istediğinize emin misiniz? Bu işlem geri alınamaz.",
  bulkDeleteConfirm: (count: number) =>
    `${count} aktivite kalıcı olarak silinecek. Bu işlem geri alınamaz. Devam etmek istiyor musunuz?`,
  bulkDeleteTitle: "Seçilen Aktiviteleri Sil",
  deleteSuccess: "Aktivite silindi.",
  bulkDeleteSuccess: (deleted: number, notFound: number) =>
    notFound > 0
      ? `${deleted} aktivite silindi, ${notFound} kayıt bulunamadı.`
      : `${deleted} aktivite silindi.`,
  loadError: "Aktiviteler yüklenemedi.",
  deleteError: "Aktivite silinemedi.",
  bulkDeleteError: "Seçilen aktiviteler silinemedi.",
  searchPlaceholder: "Aktivite ara...",
  filterAll: "Tümü",
  filterCustomer: "Müşteri",
  filterType: "Aktivite Türü",
  filterStatus: "Durum",
  filterDateFrom: "Başlangıç tarihi",
  filterDateTo: "Bitiş tarihi",
  selectAllOnPage: "Sayfadaki tümünü seç",
  selectRow: (subject: string) => `${subject} seç`,
  selectionColumn: "Seç",
  openCustomer: "Müşteri kartını aç",
  subjectRequired: "Konu zorunludur.",
  typeRequired: "Aktivite türü zorunludur.",
  statusRequired: "Durum zorunludur.",
  activityDateRequired: "Aktivite tarihi zorunludur.",
  activitySectionInfo: "Aktivite Bilgileri",
  activitySectionSchedule: "Zamanlama",
  activitySectionRelations: "İlişkiler",
  activitySectionDetails: "Detaylar",
  noContact: "— (Kişi seçilmedi)",
  backToCustomers: "Müşterilere dön",
  tabOverview: "Genel Bilgiler",
  tabContacts: "İletişim Kişileri",
  emptyTitle: "Aktivite bulunamadı.",
  emptyDescription: "Arama veya filtre kriterlerinizi değiştirip tekrar deneyin.",
} as const;

export const activityTypeLabels: Record<ActivityType, string> = {
  call: "Telefon",
  meeting: "Toplantı",
  email: "E-posta",
  whatsapp: "WhatsApp",
  note: "Not",
  fair_visit: "Fuar Görüşmesi",
  follow_up: "Takip",
  other: "Diğer",
};

export const activityStatusLabels: Record<ActivityStatus, string> = {
  open: "Açık",
  completed: "Tamamlandı",
  cancelled: "İptal Edildi",
};

export const activitySourceLabels: Record<ActivitySource, string> = {
  manual: "Manuel",
  system: "Sistem",
  email_automation: "E-posta Otomasyonu",
  whatsapp_integration: "WhatsApp Entegrasyonu",
  import: "İçe Aktarma",
  other: "Diğer",
};

export const activityTypeOptions: ActivityType[] = [
  "call",
  "meeting",
  "email",
  "whatsapp",
  "note",
  "fair_visit",
  "follow_up",
  "other",
];

export const activityStatusOptions: ActivityStatus[] = ["open", "completed", "cancelled"];

export const activitySourceOptions: ActivitySource[] = [
  "manual",
  "system",
  "email_automation",
  "whatsapp_integration",
  "import",
  "other",
];

export function formatActivityDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("tr-TR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatActivityDateShort(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("tr-TR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
