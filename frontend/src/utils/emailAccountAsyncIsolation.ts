/**
 * Entity/ID-scoped async UI guard — same idea as preview/requestId patterns elsewhere.
 * A response may update UI only when it still belongs to the active entity + request generation.
 */
export function shouldApplyAccountScopedResult(options: {
  requestId: number;
  activeRequestId: number;
  operationAccountId: string;
  activeOperationAccountId: string | null;
  modalAccountId: string | null;
}): boolean {
  const {
    requestId,
    activeRequestId,
    operationAccountId,
    activeOperationAccountId,
    modalAccountId,
  } = options;
  return (
    requestId === activeRequestId &&
    activeOperationAccountId === operationAccountId &&
    modalAccountId === operationAccountId
  );
}

export function clearIdIfMatches(
  currentId: string | null,
  finishedId: string,
): string | null {
  return currentId === finishedId ? null : currentId;
}
