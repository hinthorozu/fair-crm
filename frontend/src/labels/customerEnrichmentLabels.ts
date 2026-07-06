export const customerEnrichmentLabels = {
  tabTitle: "İletişim Zenginleştirme",
  intro:
    "Bu işlem müşterinin web sitesinden e-posta başta olmak üzere iletişim bilgilerini arar. Bulunan bilgiler doğrudan CRM'e yazılmaz; merge/preview akışına gönderilir.",
  runButton: "Bu Müşteriyi Zenginleştir",
  resetButton: "Zenginleştirme Durumunu Sıfırla",
  running: "Zenginleştirme çalışıyor…",
  resetting: "Sıfırlanıyor…",
  loadError: "Zenginleştirme durumu yüklenemedi.",
  runFailed: "Zenginleştirme başlatılamadı.",
  resetSuccess: "Zenginleştirme durumu sıfırlandı.",
  resetFailed: "Zenginleştirme durumu sıfırlanamadı.",
  resetConfirmTitle: "Zenginleştirme durumunu sıfırla",
  resetConfirmMessage:
    "Bu işlem müşterinin daha önce zenginleştirildi bilgilerini sıfırlar. CRM'deki email, telefon ve diğer müşteri bilgileri silinmez. Müşteri tekrar zenginleştirme adayına girebilir.",
  resetConfirmAction: "Sıfırla",
  statusTitle: "Mevcut durum",
  lastScan: "Son tarama",
  lastRunId: "Son run ID",
  lastEmail: "Son bulunan e-posta",
  sourceUrl: "Kaynak URL",
  lastError: "Son hata",
  retryAfter: "Tekrar deneme",
  importBatch: "Import batch",
  openImportBatch: "Import önizlemesine git",
  website: "Web sitesi",
  hasCrmEmail: "CRM e-postası",
  yes: "Var",
  no: "Yok",
  historyTitle: "Son çalışma logları",
  emptyHistory: "Henüz zenginleştirme logu yok.",
  runSummaryTitle: "Son çalışma özeti",
  summaryEmailFound: "E-posta bulundu",
  summaryPhoneFound: "Telefon bulundu",
  summaryImportBatch: "Import batch",
  summaryImportCreated: "Oluşturuldu",
  summaryImportNone: "Oluşturulmadı",
  statusNotScanned: "Taranmadı",
  statusEmailFound: "E-posta bulundu",
  statusEmailNotFound: "E-posta bulunamadı",
  statusFailed: "Başarısız",
  statusPendingMerge: "Merge bekliyor",
  statusSkippedEmailExists: "E-posta mevcut (atlandı)",
  statusSkippedNoWebsite: "Web sitesi yok (atlandı)",
} as const;

export type CustomerEnrichmentStatusKey =
  | "not_scanned"
  | "email_found"
  | "email_not_found"
  | "failed"
  | "pending_merge"
  | "skipped_email_exists"
  | "skipped_no_website";

export function customerEnrichmentStatusLabel(status: string): string {
  const map: Record<CustomerEnrichmentStatusKey, string> = {
    not_scanned: customerEnrichmentLabels.statusNotScanned,
    email_found: customerEnrichmentLabels.statusEmailFound,
    email_not_found: customerEnrichmentLabels.statusEmailNotFound,
    failed: customerEnrichmentLabels.statusFailed,
    pending_merge: customerEnrichmentLabels.statusPendingMerge,
    skipped_email_exists: customerEnrichmentLabels.statusSkippedEmailExists,
    skipped_no_website: customerEnrichmentLabels.statusSkippedNoWebsite,
  };
  return map[status as CustomerEnrichmentStatusKey] ?? status;
}
