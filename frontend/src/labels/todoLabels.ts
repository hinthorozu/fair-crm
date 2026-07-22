import type {
  CreatableTodoCategory,
  TodoCategory,
  TodoFormStatus,
  TodoPriority,
  TodoStatus,
} from "../types/todo";

export const todoLabels = {
  pageTitle: "Görevler",
  pageSubtitle: "Organizasyon görevlerini yönetin",
  permissionDenied: "Görevleri görüntüleme yetkiniz yok.",
  loadError: "Görevler yüklenemedi.",
  emptyTitle: "Henüz görev yok.",
  emptyDescription: "Yeni görev ekleyerek başlayın.",
  emptyFilteredTitle: "Sonuç bulunamadı.",
  emptyFilteredDescription: "Arama veya filtre kriterlerinizi değiştirip tekrar deneyin.",
  newTodo: "Yeni Görev",
  editTodo: "Görevi Düzenle",
  save: "Kaydet",
  cancel: "İptal",
  saving: "Kaydediliyor…",
  searchPlaceholder: "Görev ara…",
  viewTabsAriaLabel: "Görev görünümleri",
  viewAll: "Tüm Görevler",
  viewToday: "Bugün",
  viewOverdue: "Gecikenler",
  viewFollowUps: "Takip Bekleyenler",
  viewActionRequired: "Aksiyon Gerekenler",
  viewDataProblem: "Veri Problemleri",
  filterAll: "Tümü",
  filterStatus: "Durum",
  filterPriority: "Öncelik",
  filterCategory: "Kategori",
  filterOverdue: "Gecikmiş",
  filterOverdueYes: "Gecikmiş",
  filterOverdueNo: "Gecikmiş değil",
  filterIncludeArchived: "Arşivlenenleri göster",
  filterCreatedBy: "Oluşturan (UUID)",
  filterAssignee: "Sorumlu (UUID)",
  colTitle: "Başlık",
  colStatus: "Durum",
  colPriority: "Öncelik",
  colCategory: "Kategori",
  colDeadline: "Son Tarih",
  colOverdue: "Gecikmiş",
  colCreatedBy: "Oluşturan",
  colAssignee: "Sorumlu",
  colUpdatedAt: "Güncelleme",
  colActions: "İşlemler",
  overdueBadge: "Gecikmiş",
  actionEdit: "Düzenle",
  actionComplete: "Tamamlandı Yap",
  completeAndRecord: "Tamamla",
  completeModalTitle: "Tamamla ve sonucu kaydet",
  completeNote: "Sonuç notu",
  completeNoteHint: "İsteğe bağlı. Tamamlanan görevin sonucu aktivite olarak kaydedilir.",
  completeNotePlaceholder: "Örn. Müşteri bilgilendirildi, süreç kapandı.",
  actionArchive: "Arşivle",
  actionDelete: "Kalıcı Sil",
  completeSuccess: "Görev tamamlandı.",
  archiveSuccess: "Görev arşivlendi.",
  deleteSuccess: "Görev kalıcı olarak silindi.",
  createSuccess: "Görev oluşturuldu.",
  updateSuccess: "Görev güncellendi.",
  archiveConfirmTitle: "Görevi Arşivle",
  archiveConfirmMessage: "Bu görev arşivlenecek. Devam etmek istiyor musunuz?",
  deleteConfirmTitle: "Görevi Kalıcı Olarak Sil",
  deleteConfirmMessage:
    "Bu görev veritabanından kalıcı olarak silinecek. Bu işlem geri alınamaz.",
  fieldTitle: "Başlık",
  fieldDescription: "Açıklama",
  fieldStatus: "Durum",
  fieldPriority: "Öncelik",
  fieldCategory: "Kategori",
  fieldDeadline: "Son Tarih",
  fieldAssignee: "Sorumlu (UUID, opsiyonel)",
  fieldCustomer: "Müşteri",
  fieldCustomerHint: "İsteğe bağlı. Görevi belirli bir müşteriye bağlar.",
  fieldCustomerPlaceholder: "Müşteri seçin",
  fieldCustomerClear: "Müşteri seçimini kaldır",
  fieldCustomerNoResults: "Müşteri bulunamadı.",
  fieldSourceFair: "Kaynak fuar",
  fieldSourceFairHint: "İsteğe bağlı. Fuar bağlı çalışma listesi için seçin.",
  fieldSourceFairPlaceholder: "Fuar seçin",
  fieldSourceFairClear: "Fuar seçimini kaldır",
  fieldCustomerNone: "—",
  fieldSourceFairNone: "—",
  fieldCreatedAt: "Oluşturulma",
  fieldUpdatedAt: "Güncelleme",
  fieldCompletedAt: "Tamamlanma",
  titleRequired: "Başlık zorunludur.",
} as const;

export const todoStatusLabels: Record<TodoStatus, string> = {
  todo: "Yapılacak",
  in_progress: "Devam Ediyor",
  done: "Tamamlandı",
  cancelled: "İptal Edildi",
  archived: "Arşivlendi",
};

export const todoFormStatusOptions: TodoFormStatus[] = ["todo", "in_progress", "cancelled"];

export const todoFormStatusLabels: Record<TodoFormStatus, string> = {
  todo: todoStatusLabels.todo,
  in_progress: todoStatusLabels.in_progress,
  cancelled: todoStatusLabels.cancelled,
};

export const todoStatusFilterOptions: TodoStatus[] = [
  "todo",
  "in_progress",
  "done",
  "cancelled",
  "archived",
];

export const todoPriorityLabels: Record<TodoPriority, string> = {
  low: "Düşük",
  normal: "Normal",
  high: "Yüksek",
  urgent: "Acil",
};

export const todoPriorityOptions: TodoPriority[] = ["low", "normal", "high", "urgent"];

export const todoCategoryLabels: Record<TodoCategory, string> = {
  arama: "Arama",
  toplu_mail: "Toplu Mail",
  sms: "SMS",
  whatsapp: "WhatsApp",
  ziyaret: "Ziyaret",
  teklif: "Teklif",
  veri_temizleme: "Veri Temizleme",
  import_kontrol: "Import Kontrol",
  musteri_guncelleme: "Müşteri Güncelleme",
  genel_gorev: "Genel Görev",
  stand_tasarim: "Stand Tasarım",
  diger: "Diğer",
};

/** Create/edit select — human categories only. */
export const todoCategoryOptions: CreatableTodoCategory[] = [
  "arama",
  "ziyaret",
  "teklif",
  "import_kontrol",
  "musteri_guncelleme",
  "genel_gorev",
  "stand_tasarim",
  "diger",
];

/** Filter dropdown includes legacy categories so old records remain findable. */
export const todoCategoryFilterOptions: TodoCategory[] = [
  "arama",
  "toplu_mail",
  "sms",
  "whatsapp",
  "ziyaret",
  "teklif",
  "veri_temizleme",
  "import_kontrol",
  "musteri_guncelleme",
  "genel_gorev",
  "stand_tasarim",
  "diger",
];

const CREATABLE_CATEGORY_SET = new Set<string>(todoCategoryOptions);

export function isCreatableTodoCategory(value: string): value is CreatableTodoCategory {
  return CREATABLE_CATEGORY_SET.has(value);
}
