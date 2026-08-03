const RUN_PROGRESS_TEXT = /^(\d+)% \((\d+)\/(\d+)\)$/;

/** Convert legacy "percent (total/processed)" text to "percent (processed/total)". */
export function normalizeOperationRunProgressText(value: string): string {
  const match = RUN_PROGRESS_TEXT.exec(value.trim());
  if (!match) return value;
  return `${match[1]}% (${match[3]}/${match[2]})`;
}
