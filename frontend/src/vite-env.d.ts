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
  export function mountFairStand(container: HTMLElement): () => void;
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
    getLockUiState: () => {
      lock: {
        host: { childItemKey: string; instanceIndex: number };
        follower: { childItemKey: string; instanceIndex: number };
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
  }>;
}

