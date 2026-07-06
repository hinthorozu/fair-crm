import type { FollowUpFilter } from "../types/followUps";

export const followUpLabels = {
  pageTitle: "Takipler",
  searchPlaceholder: "Müşteri ara...",
  filterBugun: "Bugün takip edilecekler",
  filterGecmis: "Takip tarihi geçmiş olanlar",
  filterActionRequired: "Aksiyon gerekenler",
  filterDataProblem: "Veri problemi olanlar",
  filterHepsi: "Hepsi",
  colCustomer: "Müşteri",
  colCityCountry: "Şehir / Ülke",
  colPhone: "Telefon",
  colEmail: "E-posta",
  colLastOutcome: "Son sonuç",
  colLastNote: "Son not",
  colFollowUp: "Takip tarihi",
  colSourceTask: "Kaynak görev",
  colStatus: "Durum",
  colActionRequired: "Aksiyon gerekli",
  colDataProblem: "Veri problemi",
  colActions: "İşlemler",
  flagYes: "Evet",
  flagNo: "—",
  emptyList: "Bu filtrede takip kaydı bulunamadı.",
  loadError: "Takipler listesi yüklenemedi.",
  saveError: "Kayıt başarısız.",
  saveSuccess: "Kayıt tamamlandı.",
} as const;

export const followUpFilterOptions: { value: FollowUpFilter; label: string }[] = [
  { value: "bugun", label: followUpLabels.filterBugun },
  { value: "gecmis", label: followUpLabels.filterGecmis },
  { value: "action_required", label: followUpLabels.filterActionRequired },
  { value: "data_problem", label: followUpLabels.filterDataProblem },
  { value: "hepsi", label: followUpLabels.filterHepsi },
];
