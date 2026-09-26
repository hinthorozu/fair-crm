import React from "react";
import { buildApiHeaders } from "../config";
import {
  getGrantedCorePermissions,
  hasGrantedCorePermission,
} from "../permissions/corePermissions";
import {
  PERMISSION_STAND_PROJECTS_CREATE,
  PERMISSION_STAND_PROJECTS_DELETE,
  PERMISSION_STAND_PROJECTS_EXECUTE,
  PERMISSION_STAND_PROJECTS_UPDATE,
} from "../permissions/navigationPermissions";
import { standProjectsLabels } from "../labels/standProjectsLabels";

export type FairStandPageProps = {
  mode: "new" | "edit";
  projectId?: string;
  onBackToList: () => void;
};

export function FairStandPage({ mode, projectId, onBackToList }: FairStandPageProps) {
  const hostRef = React.useRef<HTMLDivElement>(null);
  const granted = React.useMemo(() => getGrantedCorePermissions(), []);
  const capabilities = React.useMemo(
    () => ({
      canCreate: hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_CREATE),
      canUpdate: hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_UPDATE),
      canDelete: hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_DELETE),
      canExecute: hasGrantedCorePermission(granted, PERMISSION_STAND_PROJECTS_EXECUTE),
    }),
    [granted],
  );

  React.useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;

    let cancelled = false;
    let unmount: (() => void) | undefined;

    void import("@fair-stand/mountFairStand.js").then(({ mountFairStand }) => {
      if (cancelled || !hostRef.current) return;
      unmount = mountFairStand(hostRef.current, {
        catalogHeaders: buildApiHeaders(),
        initialProjectId: mode === "edit" ? projectId : undefined,
        capabilities,
      });
    });

    return () => {
      cancelled = true;
      unmount?.();
    };
  }, [capabilities, mode, projectId]);

  return (
    <div className="fair-stand-standalone" data-testid="fair-stand-standalone">
      <div className="fair-stand-chrome">
        <button type="button" className="btn secondary fair-stand-chrome-back" onClick={onBackToList}>
          ← {standProjectsLabels.backToList}
        </button>
        <span className="fair-stand-chrome-title">
          {mode === "new" ? standProjectsLabels.editorNewTitle : standProjectsLabels.editorEditTitle}
        </span>
      </div>
      <div
        ref={hostRef}
        className="fair-stand-host"
        data-testid="fair-stand-host"
      />
    </div>
  );
}
