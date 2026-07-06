import type { WorklistFilter, WorklistPrimaryStatus } from "../types/todoWorklist";

export const todoWorklistLabels = {
  worklistTitle: "Çalışma Listesi",
  progressTitle: "İlerleme",
  progressTotal: "Toplam",
  progressNotStarted: "Yapılmadı",
  progressInFollowUp: "Takipte",
  progressClosed: "Konu kapandı",
  filterYapilmadi: "Yapılmadı",
  filterTakipte: "Takipte",
  filterKonuKapandi: "Konu kapandı",
  filterHepsi: "Hepsi",
  colCustomer: "Müşteri",
  colCityCountry: "Şehir / Ülke",
  colPhone: "Telefon",
  colEmail: "E-posta",
  colLastOutcome: "Son sonuç",
  colLastNote: "Son not",
  colFollowUp: "Takip tarihi",
  colStatus: "Durum",
  colActions: "İşlemler",
  activityPanelTitle: "Müşteri işlemi",
  outcomeLabel: "Sonuç",
  outcomePlaceholder: "Sonuç seçin",
  noteLabel: "Not",
  notePlaceholder: "Görüşme notunu yazın",
  followUpLabel: "Takip tarihi",
  actionRequiredLabel: "Aksiyon gerekiyor",
  dataProblemLabel: "Veri problemi",
  save: "Kaydet",
  saveAndNext: "Kaydet ve sıradakine geç",
  openActivity: "İşlem gir",
  emptyWorklist: "Bu filtrede müşteri bulunamadı.",
  loadError: "Çalışma listesi yüklenemedi.",
  saveError: "Kayıt başarısız.",
  saveSuccess: "Kayıt tamamlandı.",
  missingSourceFair: "Bu görev için kaynak fuar tanımlı değil; çalışma listesi kullanılamaz.",
  selectCustomerHint: "Listeden bir müşteri seçerek işlem girebilirsiniz.",
  recentActivities: "Son aktiviteler",
  backToList: "Görev listesine dön",
  addedAfterCompletionBadge: "Sonradan eklendi",
} as const;

export const worklistFilterOptions: { value: WorklistFilter; label: string }[] = [
  { value: "yapilmadi", label: todoWorklistLabels.filterYapilmadi },
  { value: "takipte", label: todoWorklistLabels.filterTakipte },
  { value: "konu_kapandi", label: todoWorklistLabels.filterKonuKapandi },
  { value: "hepsi", label: todoWorklistLabels.filterHepsi },
];

export const worklistStatusLabels: Record<WorklistPrimaryStatus, string> = {
  not_started: todoWorklistLabels.progressNotStarted,
  in_follow_up: todoWorklistLabels.progressInFollowUp,
  closed: todoWorklistLabels.progressClosed,
};

export function worklistStatusBadgeVariant(
  status: WorklistPrimaryStatus,
): "default" | "warning" | "success" {
  if (status === "in_follow_up") return "warning";
  if (status === "closed") return "success";
  return "default";
}
