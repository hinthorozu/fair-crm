const STAND_WATCH_PATH = /^\/stand\/watch\/([^/]+)\/?$/;

export function parseStandWatchToken(pathname: string): string | null {
  const match = STAND_WATCH_PATH.exec(pathname);
  if (!match) return null;
  try {
    const token = decodeURIComponent(match[1]);
    if (!token || token === "." || token === "..") return null;
    return token;
  } catch {
    return null;
  }
}
