import React from "react";
import { useAuth } from "../auth/AuthContext";
import { config } from "../config";
import {
  hasAnyGrantedCorePermission,
  hasGrantedCorePermission,
  type GrantedPermissionCollection,
} from "../permissions/corePermissions";

const EMPTY_PERMISSIONS: readonly string[] = [];

export function isEffectivePermissionGranted(
  granted: GrantedPermissionCollection,
  permissionCode: string,
  bypass = false,
): boolean {
  return bypass || hasGrantedCorePermission(granted, permissionCode);
}

export function isAnyEffectivePermissionGranted(
  granted: GrantedPermissionCollection,
  permissionCodes: readonly string[],
  bypass = false,
): boolean {
  return bypass || hasAnyGrantedCorePermission(granted, permissionCodes);
}

export function usePermissions() {
  const { session } = useAuth();
  const grantedPermissions = session?.permissions ?? EMPTY_PERMISSIONS;
  const bypass = config.devBypassEnabled;

  const can = React.useCallback(
    (permissionCode: string) =>
      isEffectivePermissionGranted(grantedPermissions, permissionCode, bypass),
    [bypass, grantedPermissions],
  );

  const canAny = React.useCallback(
    (permissionCodes: readonly string[]) =>
      isAnyEffectivePermissionGranted(grantedPermissions, permissionCodes, bypass),
    [bypass, grantedPermissions],
  );

  return { grantedPermissions, bypass, can, canAny };
}
