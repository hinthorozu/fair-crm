import { canSendMail } from "./emailAccountPermissions";
import { canPerformTodoAction } from "./todoPermissions";

export interface TodoWorklistActionPermissions {
  canRecordActivity: boolean;
  canSendManualMail: boolean;
}

export function resolveTodoWorklistActionPermissions(
  grantedPermissions: Set<string>,
): TodoWorklistActionPermissions {
  return {
    canRecordActivity: canPerformTodoAction(grantedPermissions, "update"),
    canSendManualMail: canSendMail(grantedPermissions),
  };
}
