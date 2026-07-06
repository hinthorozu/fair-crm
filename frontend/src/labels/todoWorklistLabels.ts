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
  sectionCustomer: "Müşteri özeti",
  sectionNewActivity: "Yeni işlem",
  sectionFlags: "İşaretleme",
  outcomeLabel: "Sonuç",
  outcomePlaceholder: "Sonuç seçin",
  noteLabel: "Not",
  notePlaceholder: "Görüşme notunu yazın",
  followUpLabel: "Takip tarihi",
  actionRequiredLabel: "Aksiyon gerekiyor",
  actionRequiredHint: "Bu müşteri için ek takip veya işlem gerekir.",
  dataProblemLabel: "Veri problemi",
  dataProblemHint: "Müşteri kaydındaki eksik veya hatalı bilgiyi işaretler.",
  save: "Kaydet ve kapat",
  saveAndNext: "Kaydet ve sıradakine geç",
  saving: "Kaydediliyor…",
  openCustomerCard: "Müşteri Kartı",
  emptyWorklist: "Bu filtrede müşteri bulunamadı.",
  loadError: "Çalışma listesi yüklenemedi.",
  saveError: "Kayıt başarısız.",
  saveSuccess: "Kayıt tamamlandı.",
  missingSourceFair: "Bu görev için kaynak fuar tanımlı değil. Çalışma listesini kullanmak için görevi düzenleyip bir fuar seçin.",
  missingSourceFairAction: "Görevler listesinden Düzenle ile kaynak fuar atayabilirsiniz.",
  recentActivities: "Son aktiviteler",
  recentActivitiesOverflow: "+{count} aktivite daha",
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
