export const fairLabels = {
  fairs: "Fuarlar",
  newFair: "Yeni Fuar",
  editFair: "Fuar Düzenle",
  archiveConfirm: "Bu fuarı arşivlemek istediğinize emin misiniz?",
  restoreConfirm: "Bu fuarı arşivden çıkarmak istiyor musunuz?",
  restoreSuccess: "Fuar arşivden çıkarıldı.",
  searchPlaceholder: "Fuar ara…",
  noResults: "Fuar bulunamadı.",
  loadError: "Fuarlar yüklenemedi.",
  archiveError: "Arşivleme başarısız.",
  restoreError: "Arşivden çıkarma başarısız.",
  nameRequired: "Fuar adı zorunludur.",
  name: "Fuar Adı",
  organizer: "Organizatör",
  venue: "Mekan",
  start_date: "Başlangıç Tarihi",
  end_date: "Bitiş Tarihi",
} as const;

export const fairStatusLabels: Record<string, string> = {
  planned: "Planlandı",
  active: "Aktif",
  completed: "Tamamlandı",
  cancelled: "İptal Edildi",
  archived: "Arşivlenmiş",
};
