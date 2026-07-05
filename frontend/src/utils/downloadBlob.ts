/** Download a same- or cross-origin URL without navigating the current page. */
export function triggerIframeDownload(url: string): void {
  const iframe = document.createElement("iframe");
  iframe.setAttribute("aria-hidden", "true");
  iframe.style.cssText = "display:none;width:0;height:0;border:0";
  iframe.src = url;
  document.body.appendChild(iframe);
  window.setTimeout(() => {
    iframe.remove();
  }, 120_000);
}

/** Trigger a file download from a Blob without navigating away from the current page. */
export function triggerBlobDownload(blob: Blob, fileName: string): void {
  const nav = window.navigator as Navigator & {
    msSaveOrOpenBlob?: (blob: Blob, defaultName?: string) => boolean;
  };
  if (typeof nav.msSaveOrOpenBlob === "function") {
    nav.msSaveOrOpenBlob(blob, fileName);
    return;
  }

  const objectUrl = URL.createObjectURL(blob);
  const iframe = document.createElement("iframe");
  iframe.setAttribute("aria-hidden", "true");
  iframe.style.cssText = "display:none;width:0;height:0;border:0";
  document.body.appendChild(iframe);

  const startDownload = () => {
    const doc = iframe.contentDocument ?? iframe.contentWindow?.document;
    if (!doc) return;
    const anchor = doc.createElement("a");
    anchor.href = objectUrl;
    anchor.download = fileName;
    anchor.rel = "noopener";
    doc.body.appendChild(anchor);
    anchor.click();
  };

  iframe.onload = () => {
    startDownload();
    window.setTimeout(() => {
      iframe.remove();
      URL.revokeObjectURL(objectUrl);
    }, 60_000);
  };
  iframe.onerror = () => {
    iframe.remove();
    URL.revokeObjectURL(objectUrl);
  };
  iframe.src = "about:blank";
}

export function parseContentDispositionFileName(
  disposition: string | null,
  fallback: string,
): string {
  if (!disposition) return fallback;
  const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(disposition);
  const raw = match?.[1] ?? match?.[2];
  if (!raw) return fallback;
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

export function buildDownloadRequestHeaders(extra: HeadersInit = {}): HeadersInit {
  const headers = new Headers(extra);
  headers.delete("Content-Type");
  return headers;
}
