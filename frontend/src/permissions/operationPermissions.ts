import { getGrantedCorePermissions } from "./corePermissions";

export const OPERATION_UPDATE = "fair_crm.operations.update";
export const OPERATION_EXECUTE = "fair_crm.operations.execute";

export function canUpdateOperationCapabilities(): boolean {
  return getGrantedCorePermissions().has(OPERATION_UPDATE);
}
