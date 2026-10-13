export const tobbLabels = {
  title: "TOBB incelemeleri", search: "Fuar adı", type: "Öneri türü", all: "Tümü",
  current: "Mevcut değer", incoming: "TOBB önerisi", name: "Fuar", actions: "İşlemler",
  apply: "Uygula", keep: "Mevcut Değeri Koru", defer: "Ertele", create: "Yeni Fuar Oluştur",
  map: "Seçilen Fuarla Eşleştir", same: "Aynı Fuar, Şehri Güncelle", different: "Farklı Fuar Oluştur",
  select: "Edisyonu Seç", target: "Mevcut sistem fuarı seç", bulkApply: "Seçili Tarihleri Uygula",
  bulkKeep: "Seçili Tarihleri Koru", selectRow: "Tarih önerisini seç", empty: "Bekleyen TOBB önerisi yok.",
  success: "Karar kaydedildi.", error: "TOBB işlemi tamamlanamadı.", preview: "TOBB önizlemesi",
  applySync: "Senkronizasyonu Uygula", cancel: "Durdur", retry: "Başarısız Yılları Yeniden Dene",
  history: "TOBB çalışma geçmişi", details: "Çalışma Detayı", notifications: "Bildirimler",
  notificationError: "Uygulama içi bildirim teslim edilemedi.",
  kinds: {dates: "Tarihler", organizer: "Organizatör", venue: "Fuar yeri", website: "Web sitesi", city: "Şehir", name: "İsim eşleştirmesi", edition: "Edisyon seçimi"} as Record<string, string>,
  statuses: {queued: "Sırada", running: "Çalışıyor", cancel_requested: "Durduruluyor", cancelling: "Durduruluyor", cancelled: "İptal edildi", completed: "Tamamlandı", failed: "Başarısız", preview_ready: "Önizleme hazır", preview_stale: "Önizleme değişti", review: "İnceleme", inserted: "Yeni", updated: "Güncelleme", skipped: "Atlandı"} as Record<string, string>,
};
