/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_CORE_BASE_URL: string;
  readonly VITE_APP_ENV: string;
  readonly VITE_DEV_BYPASS_ENABLED: string;
  readonly VITE_DEV_BYPASS_TOKEN: string;
  readonly VITE_ORGANIZATION_ID: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module "@fair-stand/mountFairStand.js" {
  export type FairStandMountCapabilities = {
    canCreate?: boolean;
    canUpdate?: boolean;
    canDelete?: boolean;
    canExecute?: boolean;
  };

  export type FairStandMountOptions = {
    catalogHeaders?: HeadersInit | Record<string, string>;
    initialProjectId?: string;
    capabilities?: FairStandMountCapabilities;
  };

  export function mountFairStand(
    container: HTMLElement,
    options?: FairStandMountOptions,
  ): () => void;
}

declare module "@fair-stand/catalogPreviewRenderer.js" {
  export function renderCatalogPreview(
    definition: {
      id: number;
      markup: string;
      cssCode?: string;
    },
    context?: Record<string, unknown>,
    hostDocument?: Document,
  ): HTMLElement;
}

declare module "@fair-stand/itemAdminPreview.js" {
  export function mountItemAdminPreview(
    host: HTMLElement,
    options?: Record<string, unknown>,
  ): {
    setState: (next: Record<string, unknown>) => void;
    getParts: () => Array<Record<string, unknown>>;
    setSelectedEuler: (next: {
      rotationXDeg?: number;
      rotationYDeg?: number;
      rotationZDeg?: number;
    }) => boolean;
    setSnapMode: (enabled: boolean) => boolean;
    getSnapMode: () => boolean;
    lockPendingPair: () => boolean;
    unlockAssembly: () => boolean;
    removeSelectedFromLock: () => boolean;
    applyPersistedLockFromParts: (parts?: Array<Record<string, unknown>>) => boolean;
    getLockUiState: () => {
      lock: {
        members?: Array<{ childItemKey: string; instanceIndex: number }>;
        host: { childItemKey: string; instanceIndex: number } | null;
        follower: { childItemKey: string; instanceIndex: number } | null;
      } | null;
      canLock: boolean;
    };
    dispose: () => void;
  };
  export function envelopeFromForm(input: Record<string, unknown>): Record<string, unknown> | null;
  export function partFromChildRecord(
    child: Record<string, unknown>,
    instanceIndex: number,
    pose?: Record<string, unknown>,
  ): Record<string, unknown>;
}

declare module "@fair-stand/itemAssembly.js" {
  export function buildLiveAssemblyParts(
    parentItem: Record<string, unknown>,
    savedParts: Array<Record<string, unknown>>,
    getItemFn: (key: string) => Record<string, unknown> | null,
  ): Array<Record<string, unknown>>;
  export function isAssemblyRenderableChild(child: unknown): boolean;
  export function mergeAssemblyPoses(
    bomParts: Array<Record<string, unknown>>,
    savedParts: Array<Record<string, unknown>>,
  ): Array<Record<string, unknown>>;
  export function normalizeAssemblyPartsPayload(
    parts: unknown,
  ): Array<{
    childItemKey: string;
    instanceIndex: number;
    xCm: number;
    yCm: number;
    zCm: number;
    rotationXDeg: number;
    rotationYDeg: number;
    rotationZDeg: number;
    lockGroupId: number | null;
  }>;
}

