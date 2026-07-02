export const importLabels = {
  imports: "İçe Aktarma",
  wizardTitle: "Akıllı İçe Aktarma",
  wizardSubtitle: "Adım adım güvenli veri aktarımı",
  stepSource: "Kaynak",
  stepUpload: "Yükle",
  stepFair: "Fuar Seçimi",
  stepMapping: "Kolon Eşleştirme",
  stepSheet: "Sayfa",
  stepHeader: "Başlık",
  stepMappingGrid: "Excel Önizleme + Eşleştirme",
  stepAnalyze: "Analiz",
  stepPreview: "Önizleme",
  stepDecisions: "Kararlar",
  stepApply: "Uygula",
  stepSummary: "Özet",
  sourceTitle: "Kaynak türünü seçin",
  sourceExcel: "Excel",
  sourceSoon: "Yakında",
  uploadTitle: "Dosyayı yükleyin",
  uploadHint: "Bu aşamada CRM kaydı oluşturulmaz. Yalnızca ham veri okunur.",
  selectFile: "Dosya Seç",
  upload: "Yükle",
  fairTitle: "Hedef fuarı seçin",
  fairSubtitle: "Tüm satırlar bu fuara katılımcı olarak içe aktarılacaktır.",
  fairSelect: "Fuar seçin",
  fairParticipants: "Mevcut katılımcı",
  mappingTitle: "Kolon eşleştirme",
  mappingSubtitle: "Her CRM alanını kaynak kolonuna bağlayın. Yalnızca firma adı zorunludur.",
  hasHeader: "İlk satır başlık mı?",
  headerYes: "Evet",
  headerNo: "Hayır",
  noMapping: "Eşleştirme yok",
  analyzeTitle: "Analiz",
  analyzeRun: "Analiz Et",
  analyzeRunning: "Analiz ediliyor…",
  previewTitle: "Önizleme",
  decisionsTitle: "Kararlar",
  applyTitle: "Uygula",
  applyConfirmTitle: "İçe Aktarmayı Uygula",
  applyConfirmMessage: "Seçili import kararları uygulanacak. Devam edilsin mi?",
  summaryTitle: "Özet",
  back: "Geri",
  next: "İleri",
  bulkCreateNew: "Tüm yenileri oluştur",
  bulkLinkExisting: "Tüm mevcut müşterileri fuara bağla",
  bulkUpdateDuplicates: "Tüm duplicate kayıtları güncelle",
  bulkSkipInvalid: "Tüm hatalıları atla",
  applyAllList: "TÜM LİSTEYİ UYGULA",
  applySelected: "SEÇİLİ KAYITLARI UYGULA",
  applyRunning: "Uygulanıyor…",
  applyCompletedTitle: "İşlem tamamlandı.",
  applyProcessedCount: (count: number) => `${count} kayıt başarıyla uygulandı.`,
  applyNotProcessedCount: (count: number) =>
    `${count} kayıt karar verilmediği için işlenmedi.`,
  applyFailedCount: (count: number) => `${count} kayıt uygulanamadı.`,
  applyErrorsTitle: "Uygulama hataları",
  /** @deprecated Use applyCompletedTitle + applyProcessedCount */
  applyResult: (processed: number, _notProcessed: number, failed: number) =>
    `${processed} kayıt uygulandı${failed ? `, ${failed} hata` : ""}`,
  selectAllOnPage: "Bu sayfadaki tümünü seç",
  selectedCount: (count: number) => `${count} kayıt seçili`,
  bulkDecisionPanelTitle: "Toplu karar",
  bulkDecisionActionLabel: "İşlem seç",
  bulkAssignSelected: "SEÇİLİ KAYITLARA UYGULA",
  bulkAssignRunning: "Kararlar atanıyor…",
  bulkAssignResult: (updated: number, skipped: number) =>
    `${updated} kayda karar atandı${skipped ? `, ${skipped} atlandı` : ""}`,
  bulkAssignErrorsTitle: "Karar atama hataları",
  bulkConfirmTitle: "Toplu işlem onayı",
  bulkConfirmLabel: "Onayla",
  bulkJobRunning: "Toplu işlem devam ediyor…",
  bulkJobProgress: (processed: number, total: number) =>
    `İşleniyor: ${processed} / ${total}`,
  bulkConfirmMessage: (count: number, summary: string) =>
    `Bu işlem sonucunda ${count} kayıt işlenecektir.\n\n${summary}\n\nDevam etmek istiyor musunuz?`,
  bulkLinkConfirmMessage: (toProcess: number, skipped: number, unprocessable: number) =>
    `Bu işlem sonucunda:\n${toProcess} mevcut müşteri hedef fuara bağlanacak.\n${skipped} kayıt zaten bağlı olduğu için atlanacak.\n${unprocessable} kayıt işlenemeyecek.\n\nDevam etmek istiyor musunuz?`,
  bulkJobCompleted: (processed: number, skipped: number, errors: number) =>
    `${processed} kayıt işlendi${skipped ? `, ${skipped} kayıt atlandı` : ""}${errors ? `, ${errors} hata oluştu` : ""}`,
  bulkLinkJobCompleted: (linked: number, skipped: number, errors: number) =>
    `${linked} kayıt fuara bağlandı${skipped ? `, ${skipped} kayıt zaten bağlıydı` : ""}${errors ? `, ${errors} hata oluştu` : ""}`,
  importCompletedTitle: "Import başarıyla tamamlandı.",
  importCompletedMessage: (count: number) => `${count} kayıt işlendi.`,
  importCompletedNoPending: "Import üzerinde bekleyen karar kalmadı.",
  importCompletedBack: "Import İşlerine Dön",
  uploadResumeHint: "Dosya bu import işine bağlıdır. Yeni dosya için Yeni Import başlatın.",
  colRow: "Satır",
  colCompany: "Firma",
  colEmail: "E-posta",
  colPhone: "Telefon",
  colWeb: "Web",
  colHall: "Salon",
  colStand: "Stand",
  colStatus: "Durum",
  colMatch: "Eşleşen Müşteri",
  colMatchType: "Eşleşme Tipi",
  colParticipation: "Seçilen Fuarda Var mı?",
  colConfidence: "Güven",
  colDecision: "Karar",
  colErrors: "Hatalar",
  participationYes: "Mevcut katılım",
  participationNo: "Yeni katılım",
  resultCreated: "Oluşturulan müşteri",
  resultUpdated: "Güncellenen müşteri",
  resultParticipationCreated: "Oluşturulan katılım",
  resultParticipationUpdated: "Güncellenen katılım",
  resultContacts: "Oluşturulan contact",
  resultSkipped: "Atlanan",
  resultInvalid: "Hatalı",
  newImport: "Yeni içe aktarma",
  importFromFair: "Katılımcıları İçe Aktar",
  uploadError: "Dosya yüklenemedi.",
  loadError: "Veriler yüklenemedi.",
  applyError: "Uygulama başarısız.",
  decisionError: "Karar kaydedilemedi.",
  previewFilterWithCount: (label: string, count: number) => `${label} (${count})`,
  previewFilterPending: "Bekleyen",
  previewFilterAll: "Tüm kayıtlar",
  previewFilterApplied: "Uygulandı",
  previewFilterNew: "Yeni",
  previewFilterUpdate: "Güncellenecek",
  previewFilterDuplicate: "Duplicate",
  previewFilterInvalid: "Hatalı",
  previewFilterSkip: "Atlanacak",
  previewSearch: "Firma ara…",
  previewSortConfidence: "Güven skoru",
  previewSortCompany: "Firma",
  previewSortStatus: "Durum",
  mergeDiffTitle: "Birleştirme Detayı",
  mappingCrmField: "CRM Alanı",
  mappingSourceColumn: "Kaynak Kolonu",
  mappingSourcePreview: "Kaynak Önizleme",
  mappingShowMoreSamples: "Diğer örnekleri göster",
  mappingShowLessSamples: "Daha az göster",
  mappingStatsTotal: "Toplam örnek",
  mappingStatsEmpty: "Boş",
  mappingStatsFilled: "Dolu",
  mappingStatsFirst: "İlk değer",
  mappingNoColumnSelected: "Kolon seçin",
} as const;

export const importBatchStatusLabels: Record<string, string> = {
  uploaded: "Yüklendi",
  sheet_selected: "Sayfa Seçildi",
  header_configured: "Başlık Ayarlandı",
  mapping_completed: "Analiz Bekliyor",
  analysis_queued: "Analiz Kuyrukta",
  analyzing: "Analiz Ediliyor",
  analyzed: "Analiz Edildi",
  analysis_failed: "Analiz Başarısız",
  decision_required: "Karar Bekliyor",
  applying: "Uygulanıyor",
  completed: "Tamamlandı",
  failed: "Başarısız",
  cancelled: "İptal Edildi",
  // Legacy
  mapped: "Analiz Bekliyor",
  previewed: "Önizlendi",
  applied: "Tamamlandı",
};

export const GRID_MAPPING_FIELD_OPTIONS = [
  { value: "", label: "Kullanma" },
  { value: "company_name", label: "Firma Adı" },
  { value: "phone", label: "Telefon" },
  { value: "email", label: "E-posta" },
  { value: "website", label: "Website" },
  { value: "contact_first_name", label: "Yetkili Adı" },
  { value: "country", label: "Ülke" },
  { value: "city", label: "Şehir" },
  { value: "address", label: "Adres" },
  { value: "stand", label: "Stand No" },
  { value: "hall", label: "Salon / Hall" },
  { value: "notes", label: "Not" },
] as const;

export const importRowStatusLabels: Record<string, string> = {
  pending: "Bekliyor",
  valid: "Geçerli",
  invalid: "Hatalı",
  possible_duplicate: "Olası Tekrar",
  ready_to_create: "Yeni",
  ready_to_update: "Güncellenecek",
  applied: "Uygulandı",
  skipped: "Atlandı",
};

export const importMatchStatusLabels: Record<string, string> = {
  new_customer: "Yeni müşteri",
  existing_customer_candidate: "Mevcut müşteri olabilir",
  no_company_name: "Eksik firma adı",
  invalid_company_name: "Geçersiz firma adı",
  batch_duplicate: "Dosyada tekrar",
};

export const importMatchTypeLabels: Record<string, string> = {
  exact_normalized_match: "Tam eşleşme",
  fuzzy_name_candidate: "Benzer isim",
  weak_name_candidate: "Düşük güven",
  no_match: "Eşleşme yok",
};

export const importMatchExplanationLabels: Record<string, string> = {
  normalized_exact: "Normalize isim aynı",
  token_overlap_high: "Token örtüşmesi yüksek",
  legal_suffix_ignored: "Tüzel ek farkı ihmal edildi",
  abbreviation_normalized: "Kısaltmalar normalize edildi",
  string_similarity_high: "Yüksek string benzerliği",
};

export const importDecisionLabels: Record<string, string> = {
  create_new: "Yeni müşteri oluştur",
  update_existing: "Mevcut müşteriyi güncelle/bağla",
  skip: "Atla",
};

export const WIZARD_SETUP_STEPS = [
  { id: "fair", label: importLabels.stepFair },
  { id: "upload", label: importLabels.stepUpload },
  { id: "sheet", label: importLabels.stepSheet },
  { id: "header", label: importLabels.stepHeader },
  { id: "mapping", label: importLabels.stepMappingGrid },
] as const;

export const WIZARD_CONTINUE_STEPS = [
  { id: "decisions", label: importLabels.stepDecisions },
] as const;

/** @deprecated Use WIZARD_SETUP_STEPS / WIZARD_CONTINUE_STEPS */
export const WIZARD_STEPS = [
  { id: "source", label: importLabels.stepSource },
  ...WIZARD_SETUP_STEPS,
  { id: "analyze", label: importLabels.stepAnalyze },
  { id: "preview", label: importLabels.stepPreview },
  ...WIZARD_CONTINUE_STEPS,
] as const;

export type WizardStepId = (typeof WIZARD_STEPS)[number]["id"];

export const mergeEntityLabels: Record<string, string> = {
  customer: "Müşteri",
  participation: "Fuar Katılımı",
  contact: "İletişim Kişisi",
};

export const mergeOutcomeLabels: Record<string, string> = {
  same: "Aynı",
  new: "Yeni",
  will_add: "Eklenecek",
  will_update: "Güncellenecek",
  will_keep: "Korunacak",
  conflict: "Çakışıyor",
  empty: "Boş",
  skipped: "Atlanacak",
};
