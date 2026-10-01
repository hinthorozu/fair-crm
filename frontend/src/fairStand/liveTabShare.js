/**
 * CI / standalone Fair CRM checkout fallback.
 * Server and local Kyrox builds alias @fair-stand to the sibling Fair Stand src
 * when that checkout is present. This file only lets the CRM build resolve
 * the watch page import when Fair Stand is not beside the repo.
 */

export function viewerStatusCopy(status) {
  switch (status) {
    case "waiting":
      return "Canlı bağlantı bekleniyor";
    case "disconnected":
      return "Bağlantı kesildi";
    case "ended":
      return "Yayın sona erdi";
    case "invalid":
      return "Bu canlı paylaşım linki geçersiz.";
    case "expired":
      return "Bu canlı paylaşımın süresi doldu.";
    case "occupied":
      return "Bu canlı paylaşım oturumunda zaten bir izleyici bağlı.";
    default:
      return "";
  }
}

export function startViewerSession() {
  return () => {};
}
