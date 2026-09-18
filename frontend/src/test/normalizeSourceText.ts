/** Canonicalize source text for contract tests across Windows CRLF and Unix LF. */
export function normalizeSourceText(source: string): string {
  return source.replace(/\r\n/g, "\n");
}
