import {
  canReadQuoteEditor,
} from "./quotePermissions";
import type { GrantedPermissionCollection } from "./corePermissions";

export function canOpenTodoQuoteAction(
  granted: GrantedPermissionCollection,
): boolean {
  return canReadQuoteEditor(granted);
}
