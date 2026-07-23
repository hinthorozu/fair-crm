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
  detailSubtitle: "Tanım, canlı log ve çalıştırma geçmişi",
  runsTitle: "Çalıştırma Geçmişi",
  runsEmpty: "Henüz çalıştırma kaydı yok.",
  progressTitle: "İlerleme",
  liveLogTitle: "Canlı Log",
  linkedScraperRunMissing: "Bu otomasyona bağlı scraper çalıştırması bulunmuyor.",
  startSuccess: "Otomasyon başlatıldı.",
  cancelSuccess: "Otomasyon iptal edildi.",
  createSuccess: "Otomasyon oluşturuldu.",
  wizardTitle: "Yeni Otomasyon",
  wizardSubtitle: "Ortak sihirbaz ile otomasyon tanımı oluşturun",
  typeSelectTitle: "Otomasyon Türü",
  typeSelectSubtitle: "Oluşturmak istediğiniz otomasyon tipini seçin",
  typeSelectPlaceholder: "Otomasyon türü seçin",
  typeInfoPurpose: "Ne işe yarar",
  typeInfoHow: "Ne yapılır",
  continue: "Devam Et",
  dismiss: "Vazgeç",
  chooseType: "Seç",
  scraperWizardTitle: "Web Scraper Otomasyonu",
  scraperWizardSubtitle: "Fuar seçerek Web Scraper otomasyonu oluşturun",
  stepType: "İş tipi",
  stepSource: "Kaynak",
  stepTypeConfig: "İş ayarları",
  stepScope: "Hedef / kapsam",
  stepRunSettings: "Çalışma ayarları",
  stepSummary: "Özet",
  stepConfirm: "Onay",
  stepAdapter: "Adapter",
  stepFair: "Fuar",
  stepScraperInfo: "Web Scraper Bilgileri",
  stepOutputFields: "Çıktı Alanları",
  stepRequestedFields: "İstenen alanlar",
  stepSettings: "Ayarlar",
  next: "İleri",
  back: "Geri",
  create: "Oluştur",
  createAndStart: "Oluştur ve Başlat",
  startAutomation: "Otomasyonu Başlat",
  typeRequired: "İş tipi seçin.",
  titleRequired: "Başlık zorunludur.",
  adapterRequired: "Adapter seçin.",
  fairRequired: "Bir fuar seçin.",
  requestedFieldsRequired: "En az bir alan seçin.",
  fairSourceUrlRequired: "Kaynak URL zorunludur.",
  fairNotScraperReady:
    "Seçilen fuarın scraper adapter’ı yok veya scraper çalıştırmaya uygun değil.",
  fairEnrichmentAdapterNotAllowed:
    "Bu fuar enrichment adapter’ına bağlı. Web Scraper otomasyonu için uygun değil.",
  scraperConfigInvalidJson: "Scraper Config geçerli bir JSON nesnesi olmalıdır.",
  operationOverrideHint:
    "Bu alanlar yalnızca bu otomasyon çalıştırması için kullanılır; fuar kaydı güncellenmez.",
  adaptersEmpty: "Aktif scraper adapter bulunamadı.",
  linkedFairsEmpty: "Bu adapter’a bağlı fuar yok.",
  fairSourceUrlLabel: "Kaynak URL",
  fairScraperConfigLabel: "Scraper Config",
  overrideMaxPages: "max_pages",
  overrideUseHttp: "use_http",
  overrideScrapeDetail: "scrape_detail",
  readOnlyConfigHint: "URL ve scraper_config salt okunur; yalnızca aşağıdaki override alanları düzenlenebilir.",
  scopePreviewHint: "Kapsam önizlemesi iş tipine göre sonraki aşamada eklenecek.",
  linkedTodoTitle: "Bağlı Görev",
  linkedTodoOpen: "Görevi Aç",
  linkedTodoMissing: "Bağlı görev yüklenemedi.",
  linkedTodoEmpty: "Henüz bağlı görev yok. Başlatınca Todo oluşturulur.",
  scraperConfigTitle: "Web Scraper ayarları",
  linkedScraperRunTitle: "Bağlı Web Scraper Çalıştırması",
  linkedScraperRunId: "Web Scraper run ID",
  linkedImportBatchId: "Import batch ID",
  linkedImportBatchOpen: "Import batch’i aç",
  linkedTotalRows: "Toplam satır",
  linkedInputUrl: "Girdi URL",
  adapterKeyLabel: "Adapter",
  requestedFieldsLabel: "İstenen alanlar",
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

/** Short summary + purpose/how copy for the new-automation type picker. */
export type OperationTypeInfo = {
  summary: string;
  purpose: string;
  how: string;
};

/**
 * Canonical, conservative copy from existing labels/schemas/ADR-036.
 * Placeholder types stay brief until their wizards ship.
 */
export const operationTypeInfo: Record<OperationType, OperationTypeInfo> = {
  scraper: {
    summary: "Web sitelerinden veri toplama otomasyonu.",
    purpose: "Fuar/katılımcı/firma verilerini web sitesinden toplar.",
    how: "Fuar seçilir, Web Scraper bilgileri ve çıktı alanları belirlenir, otomasyon başlatılır.",
  },
  email: {
    summary: "Tekil e-posta gönderimi.",
    purpose: "Müşteriye tekil e-posta gönderir.",
    how: "SMTP hesabı, şablon ve konu alanlarıyla yapılandırılır.",
  },
  bulk_email: {
    summary: "Toplu e-posta kampanyası.",
    purpose: "Fuar, segment veya seçili kayıtlar üzerinden toplu e-posta gönderir.",
    how: "Kaynak, SMTP hesabı, şablon ve konu ile yapılandırılır.",
  },
  enrichment: {
    summary: "Müşteri verisi araştırma ve öneri üretimi.",
    purpose: "Müşteri kayıtları için web sitesi, e-posta ve telefon araştırması yapar.",
    how: "Kaynak seçilir; araştırma alanları yapılandırılır.",
  },
  duplicate_check: {
    summary: "Yinelenen kayıt eşleştirme.",
    purpose: "Yinelenen müşteri kayıtlarını eşleştirir.",
    how: "Eşleştirme alanları ve normalize kuralları ile yapılandırılır.",
  },
  data_cleanup: {
    summary: "Veri temizleme kuralları.",
    purpose: "Kayıtlar üzerinde veri temizleme kurallarını uygular.",
    how: "Temizleme kuralları ile yapılandırılır.",
  },
  whatsapp: {
    summary: "WhatsApp mesaj gönderimi.",
    purpose: "Müşterilere WhatsApp mesajı gönderir.",
    how: "Sağlayıcı, şablon ve mesaj alanlarıyla yapılandırılır.",
  },
  manual_task: {
    summary: "Worker gerektirmeyen manuel görev.",
    purpose: "İnsan tarafından yürütülen manuel görevi Operation kaydı olarak izler.",
    how: "Görev başlığı, atama ve zamanlama alanlarıyla yapılandırılır.",
  },
  reminder: {
    summary: "Zamanlanmış hatırlatma.",
    purpose: "Zamanlanmış hatırlatma oluşturur.",
    how: "Mesaj ve hatırlatma zamanı ile yapılandırılır.",
  },
};

export const operationTypeDescriptions: Record<OperationType, string> = {
  scraper: operationTypeInfo.scraper.summary,
  email: operationTypeInfo.email.summary,
  bulk_email: operationTypeInfo.bulk_email.summary,
  enrichment: operationTypeInfo.enrichment.summary,
  duplicate_check: operationTypeInfo.duplicate_check.summary,
  data_cleanup: operationTypeInfo.data_cleanup.summary,
  whatsapp: operationTypeInfo.whatsapp.summary,
  manual_task: operationTypeInfo.manual_task.summary,
  reminder: operationTypeInfo.reminder.summary,
};

export const operationStatusLabels: Record<OperationStatus, string> = {
  draft: "Taslak",
  ready: "Hazır",
  active: "Aktif",
  completed: "Tamamlandı",
  cancelled: "İptal",
  archived: "Arşiv",
};

/**
 * @deprecated Prefer utils/operationRunStatus user-facing mapping for UI.
 * Kept for any technical/debug references; values align with the shared model.
 */
export const runStatusLabels: Record<RunStatus, string> = {
  queued: "Çalışıyor",
  running: "Çalışıyor",
  paused: "Durduruldu",
  completed: "Bitti",
  failed: "Hata",
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
  adapter: operationLabels.stepAdapter,
  fair: operationLabels.stepFair,
  scraper_info: operationLabels.stepScraperInfo,
  output_fields: operationLabels.stepOutputFields,
  requested_fields: operationLabels.stepRequestedFields,
  settings: operationLabels.stepSettings,
};
