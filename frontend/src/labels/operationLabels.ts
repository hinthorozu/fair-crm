import type {
  OperationPriority,
  OperationStatus,
  OperationType,
  RunStatus,
  SourceKind,
} from "../types/operation";

export const operationLabels = {
  pageTitle: "Otomasyonlar",
  pageSubtitle: "Ortak Operation Engine üzerinden otomasyon tanımlarını yönetin",
  newOperation: "Yeni Otomasyon",
  loadError: "Otomasyonlar yüklenemedi.",
  emptyTitle: "Henüz otomasyon yok.",
  emptyDescription: "Sihirbaz ile yeni bir otomasyon oluşturarak başlayın.",
  emptyFilteredTitle: "Sonuç bulunamadı.",
  emptyFilteredDescription: "Arama veya filtre kriterlerinizi değiştirip tekrar deneyin.",
  searchPlaceholder: "Otomasyon ara…",
  filterType: "İş tipi",
  filterStatus: "Durum",
  filterAll: "Tümü",
  colTitle: "Başlık",
  colType: "İş tipi",
  colStatus: "Durum",
  colPriority: "Öncelik",
  colProgress: "İlerleme",
  colUpdatedAt: "Güncelleme",
  colActions: "Aksiyonlar",
  actionOpen: "Aç",
  actionStart: "Başlat",
  actionCancel: "İptal",
  detailTitle: "Otomasyon Detayı",
  detailSubtitle: "Tanım, yetenekler ve çalıştırma geçmişi",
  runsTitle: "Çalıştırma Geçmişi",
  runsEmpty: "Henüz çalıştırma kaydı yok.",
  progressTitle: "İlerleme",
  capabilitiesTitle: "Yetenekler",
  startSuccess: "Otomasyon başlatıldı.",
  cancelSuccess: "Otomasyon iptal edildi.",
  createSuccess: "Otomasyon oluşturuldu.",
  wizardTitle: "Yeni Otomasyon",
  wizardSubtitle: "Ortak sihirbaz ile otomasyon tanımı oluşturun",
  stepType: "İş tipi",
  stepSource: "Kaynak",
  stepTypeConfig: "İş ayarları",
  stepScope: "Hedef / kapsam",
  stepRunSettings: "Çalışma ayarları",
  stepSummary: "Özet",
  stepConfirm: "Onay",
  next: "İleri",
  back: "Geri",
  create: "Oluştur",
  createAndStart: "Oluştur ve Başlat",
  typeRequired: "İş tipi seçin.",
  titleRequired: "Başlık zorunludur.",
  notExecutionReady:
    "Bu iş tipi henüz Execution Engine’e bağlanmadı. Kayıt oluşturulabilir; başlatma sonraki adımda gelecek.",
  scopePreviewHint: "Kapsam önizlemesi iş tipine göre sonraki aşamada eklenecek.",
  sourceNoneHint: "Bu iş tipi kaynak gerektirmez.",
  fairSourceLabel: "Fuar seçimi",
  fairSourcePlaceholder: "Fuar seçin…",
  fairSourceAdd: "Ekle",
  fairSourceEmpty: "Henüz fuar eklenmedi.",
  fairSourceRemove: "Kaldır",
  fairSourceRequired: "En az bir fuar seçin.",
  fairSourceAlreadyAdded: "Bu fuar zaten listede.",
  linkedTodoTitle: "Bağlı Görev",
  linkedTodoOpen: "Görevi Aç",
  linkedTodoMissing: "Bağlı görev yüklenemedi.",
  linkedTodoEmpty: "Henüz bağlı görev yok. Başlatınca Todo oluşturulur.",
} as const;

export const operationTypeLabels: Record<OperationType, string> = {
  scraper: "Web Scraper",
  email: "E-posta",
  bulk_email: "Toplu E-posta",
  enrichment: "Zenginleştirme",
  duplicate_check: "Duplicate Kontrolü",
  data_cleanup: "Veri Temizleme",
  whatsapp: "WhatsApp",
  manual_task: "Manuel Görev",
  reminder: "Hatırlatma",
};

export const operationTypeDescriptions: Record<OperationType, string> = {
  scraper: "Web sitelerinden veri toplama otomasyonu.",
  email: "Tekil e-posta gönderimi.",
  bulk_email: "Toplu e-posta kampanyası.",
  enrichment: "Müşteri verisi araştırma ve öneri üretimi.",
  duplicate_check: "Yinelenen kayıt eşleştirme.",
  data_cleanup: "Veri temizleme kuralları.",
  whatsapp: "WhatsApp mesaj gönderimi.",
  manual_task: "Worker gerektirmeyen manuel görev.",
  reminder: "Zamanlanmış hatırlatma.",
};

export const operationStatusLabels: Record<OperationStatus, string> = {
  draft: "Taslak",
  ready: "Hazır",
  active: "Aktif",
  completed: "Tamamlandı",
  cancelled: "İptal",
  archived: "Arşiv",
};

export const runStatusLabels: Record<RunStatus, string> = {
  queued: "Kuyrukta",
  running: "Çalışıyor",
  paused: "Duraklatıldı",
  completed: "Tamamlandı",
  failed: "Başarısız",
  cancelled: "İptal",
};

export const sourceKindLabels: Record<SourceKind, string> = {
  fair: "Fuar",
  import: "İçe aktarım",
  segment: "Segment",
  manual_selection: "Manuel seçim",
  customer: "Müşteri",
  none: "Yok",
};

export const operationPriorityLabels: Record<OperationPriority, string> = {
  low: "Düşük",
  normal: "Normal",
  high: "Yüksek",
  urgent: "Acil",
};

export const wizardStepLabels: Record<string, string> = {
  type: operationLabels.stepType,
  source: operationLabels.stepSource,
  type_config: operationLabels.stepTypeConfig,
  scope: operationLabels.stepScope,
  run_settings: operationLabels.stepRunSettings,
  summary: operationLabels.stepSummary,
  confirm: operationLabels.stepConfirm,
};
