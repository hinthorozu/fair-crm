import React from "react";
import {
  envelopeFromForm,
  mountItemAdminPreview,
  partFromChildRecord,
} from "@fair-stand/itemAdminPreview.js";
import { mergeAssemblyPoses, normalizeAssemblyPartsPayload } from "@fair-stand/itemAssembly.js";
import { getFairStandAdminItemRecord, updateFairStandAdminItemAssembly } from "../../api/fairStandAdmin";
import { Banner } from "../ui/Banner";
import { Button } from "../ui/Button";
import { adminLabels } from "../../labels/adminLabels";

export type AssemblyPartPose = {
  childItemKey: string;
  instanceIndex: number;
  xCm: number;
  yCm: number;
  zCm: number;
  rotationXDeg: number;
  rotationYDeg: number;
  rotationZDeg: number;
};

type EulerDraft = {
  rotationXDeg: string;
  rotationYDeg: string;
  rotationZDeg: string;
};

const EMPTY_EULER_DRAFT: EulerDraft = {
  rotationXDeg: "",
  rotationYDeg: "",
  rotationZDeg: "",
};

function formatDeg(value: number) {
  return String(Number((Number(value) || 0).toFixed(1)));
}

type PreviewFormSlice = {
  is_render: boolean;
  composition_mode: string;
  default_color: string;
  width_cm: string;
  depth_cm: string;
  height_cm: string;
  scene_width_cm: string;
  scene_depth_cm: string;
  scene_height_cm: string;
  components: Array<{ child_item_key: string; quantity: string }>;
};

function buildBomPartsFromChildren(
  components: PreviewFormSlice["components"],
  childByKey: Map<string, Awaited<ReturnType<typeof getFairStandAdminItemRecord>>>,
  saved: AssemblyPartPose[],
) {
  const bom: ReturnType<typeof partFromChildRecord>[] = [];
  for (const row of components) {
    const key = row.child_item_key.trim();
    if (!key) continue;
    const child = childByKey.get(key);
    if (!child || child.isRender !== true) continue;
    const quantity = Math.round(Number(row.quantity));
    if (!Number.isFinite(quantity) || quantity <= 0) continue;
    for (let instanceIndex = 0; instanceIndex < quantity; instanceIndex += 1) {
      bom.push(partFromChildRecord(child, instanceIndex));
    }
  }
  return mergeAssemblyPoses(bom, saved);
}

export function FairStandItem3dPreview({
  itemKey,
  form,
  initialAssemblyParts = [],
  canSaveAssembly,
}: {
  itemKey: string;
  form: PreviewFormSlice;
  initialAssemblyParts?: AssemblyPartPose[];
  canSaveAssembly: boolean;
}) {
  const hostRef = React.useRef<HTMLDivElement>(null);
  const apiRef = React.useRef<ReturnType<typeof mountItemAdminPreview> | null>(null);
  const partsRef = React.useRef<AssemblyPartPose[]>(
    normalizeAssemblyPartsPayload(initialAssemblyParts),
  );
  const [mode, setMode] = React.useState<"envelope" | "assembly">("envelope");
  const [expanded, setExpanded] = React.useState(false);
  const [selectedPart, setSelectedPart] = React.useState<{
    childItemKey: string;
    instanceIndex: number;
    rotationXDeg: number;
    rotationYDeg: number;
    rotationZDeg: number;
  } | null>(null);
  const [eulerDraft, setEulerDraft] = React.useState<EulerDraft>(EMPTY_EULER_DRAFT);
  const angleFocusRef = React.useRef<"rotationXDeg" | "rotationYDeg" | "rotationZDeg" | null>(null);
  const [snapMode, setSnapMode] = React.useState(false);
  const [snapSession, setSnapSession] = React.useState<{
    childItemKey: string;
    instanceIndex: number;
    cornerKey: string;
    cornerLabel: string;
  } | null>(null);
  const [canLockPair, setCanLockPair] = React.useState(false);
  const [assemblyLock, setAssemblyLock] = React.useState<{
    host: { childItemKey: string; instanceIndex: number };
    follower: { childItemKey: string; instanceIndex: number };
  } | null>(null);
  const [status, setStatus] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [childCache, setChildCache] = React.useState<
    Map<string, Awaited<ReturnType<typeof getFairStandAdminItemRecord>>>
  >(() => new Map());

  const isRecipe = form.composition_mode.trim() === "recipe" && form.components.length > 0;

  React.useEffect(() => {
    partsRef.current = normalizeAssemblyPartsPayload(initialAssemblyParts);
  }, [initialAssemblyParts]);

  React.useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const api = mountItemAdminPreview(host, {
      isRender: form.is_render,
      mode: "envelope",
      envelope: envelopeFromForm({
        widthCm: form.width_cm,
        depthCm: form.depth_cm,
        heightCm: form.height_cm,
        sceneWidthCm: form.scene_width_cm,
        sceneDepthCm: form.scene_depth_cm,
        sceneHeightCm: form.scene_height_cm,
        defaultColor: form.default_color,
      }),
      onPartsChange: (parts) => {
        partsRef.current = normalizeAssemblyPartsPayload(parts);
      },
      onSelectionChange: (selection) => {
        if (!selection?.childItemKey) {
          setSelectedPart(null);
          setEulerDraft(EMPTY_EULER_DRAFT);
          return;
        }
        const next = {
          childItemKey: String(selection.childItemKey),
          instanceIndex: Number(selection.instanceIndex) || 0,
          rotationXDeg: Number(selection.rotationXDeg) || 0,
          rotationYDeg: Number(selection.rotationYDeg) || 0,
          rotationZDeg: Number(selection.rotationZDeg) || 0,
        };
        setSelectedPart(next);
        setEulerDraft((prev) => ({
          rotationXDeg:
            angleFocusRef.current === "rotationXDeg" ? prev.rotationXDeg : formatDeg(next.rotationXDeg),
          rotationYDeg:
            angleFocusRef.current === "rotationYDeg" ? prev.rotationYDeg : formatDeg(next.rotationYDeg),
          rotationZDeg:
            angleFocusRef.current === "rotationZDeg" ? prev.rotationZDeg : formatDeg(next.rotationZDeg),
        }));
      },
      onSnapModeChange: (enabled) => {
        setSnapMode(Boolean(enabled));
        if (!enabled) setSnapSession(null);
      },
      onSnapSessionChange: (session) => {
        if (!session?.cornerKey) {
          setSnapSession(null);
          return;
        }
        setSnapSession({
          childItemKey: String(session.childItemKey || ""),
          instanceIndex: Number(session.instanceIndex) || 0,
          cornerKey: String(session.cornerKey),
          cornerLabel: String(session.cornerLabel || session.cornerKey),
        });
      },
      onLockChange: (next) => {
        setCanLockPair(Boolean(next?.canLock));
        if (!next?.lock?.host?.childItemKey || !next?.lock?.follower?.childItemKey) {
          setAssemblyLock(null);
          return;
        }
        setAssemblyLock({
          host: {
            childItemKey: String(next.lock.host.childItemKey),
            instanceIndex: Number(next.lock.host.instanceIndex) || 0,
          },
          follower: {
            childItemKey: String(next.lock.follower.childItemKey),
            instanceIndex: Number(next.lock.follower.instanceIndex) || 0,
          },
        });
      },
    });
    apiRef.current = api;
    return () => {
      api.dispose();
      apiRef.current = null;
    };
    // Mount once per itemKey; updates go through setState.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemKey]);

  React.useEffect(() => {
    let cancelled = false;
    const keys = [
      ...new Set(
        form.components
          .map((row) => row.child_item_key.trim())
          .filter(Boolean),
      ),
    ];
    if (!keys.length) {
      setChildCache(new Map());
      return;
    }
    void Promise.all(
      keys.map(async (key) => {
        try {
          return [key, await getFairStandAdminItemRecord(key)] as const;
        } catch {
          return [key, null] as const;
        }
      }),
    ).then((rows) => {
      if (cancelled) return;
      const next = new Map<string, Awaited<ReturnType<typeof getFairStandAdminItemRecord>>>();
      for (const [key, record] of rows) {
        if (record) next.set(key, record);
      }
      setChildCache(next);
    });
    return () => {
      cancelled = true;
    };
  }, [form.components]);

  React.useEffect(() => {
    const api = apiRef.current;
    if (!api) return;
    const envelope = envelopeFromForm({
      widthCm: form.width_cm,
      depthCm: form.depth_cm,
      heightCm: form.height_cm,
      sceneWidthCm: form.scene_width_cm,
      sceneDepthCm: form.scene_depth_cm,
      sceneHeightCm: form.scene_height_cm,
      defaultColor: form.default_color,
    });
    if (mode === "assembly" && isRecipe) {
      const parts = buildBomPartsFromChildren(form.components, childCache, partsRef.current);
      api.setState({
        isRender: form.is_render,
        mode: "assembly",
        envelope,
        parts,
        message: parts.length
          ? null
          : adminLabels.fairStandItems3dNoRenderableChildren,
      });
      return;
    }
    setSelectedPart(null);
    setSnapMode(false);
    setSnapSession(null);
    setCanLockPair(false);
    setAssemblyLock(null);
    api.setSnapMode(false);
    api.unlockAssembly();
    api.setState({
      isRender: form.is_render,
      mode: "envelope",
      envelope,
      parts: [],
      message: null,
    });
  }, [form, mode, isRecipe, childCache]);

  React.useEffect(() => {
    if (!expanded) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [expanded]);

  const saveAssembly = async () => {
    if (!canSaveAssembly) return;
    setSaving(true);
    setError(null);
    setStatus(null);
    try {
      const live = apiRef.current?.getParts() ?? partsRef.current;
      const payload = normalizeAssemblyPartsPayload(live).map((part) => ({
        child_item_key: part.childItemKey,
        instance_index: part.instanceIndex,
        x_cm: part.xCm,
        y_cm: part.yCm,
        z_cm: part.zCm,
        rotation_x_deg: part.rotationXDeg,
        rotation_y_deg: part.rotationYDeg,
        rotation_z_deg: part.rotationZDeg,
      }));
      const saved = await updateFairStandAdminItemAssembly(itemKey, { parts: payload });
      partsRef.current = normalizeAssemblyPartsPayload(saved.assemblyParts ?? []);
      setStatus(adminLabels.fairStandItems3dAssemblySaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : adminLabels.fairStandItems3dAssemblySaveFailed);
    } finally {
      setSaving(false);
    }
  };

  const commitEulerAxis = (axis: keyof EulerDraft) => {
    if (!selectedPart) return;
    const raw = eulerDraft[axis];
    const deg = Number(raw);
    if (!Number.isFinite(deg)) {
      setEulerDraft((prev) => ({ ...prev, [axis]: formatDeg(selectedPart[axis]) }));
      return;
    }
    const ok = apiRef.current?.setSelectedEuler({ [axis]: deg });
    if (ok) {
      setSelectedPart((prev) => (prev ? { ...prev, [axis]: deg } : prev));
      setEulerDraft((prev) => ({ ...prev, [axis]: formatDeg(deg) }));
    }
  };

  const selectedLabel = React.useMemo(() => {
    if (!selectedPart?.childItemKey) return null;
    const record = childCache.get(selectedPart.childItemKey);
    const name = record?.name?.trim() || "";
    const key = selectedPart.childItemKey;
    const index = selectedPart.instanceIndex;
    return name ? `${key} · ${name} · #${index}` : `${key} · #${index}`;
  }, [selectedPart, childCache]);

  const angleFields: Array<{
    axis: keyof EulerDraft;
    label: string;
    className: string;
  }> = [
    { axis: "rotationXDeg", label: adminLabels.fairStandItems3dRotationW, className: "is-w" },
    { axis: "rotationYDeg", label: adminLabels.fairStandItems3dRotationD, className: "is-d" },
    { axis: "rotationZDeg", label: adminLabels.fairStandItems3dRotationH, className: "is-h" },
  ];

  const toolbar = (
    <div className="fair-stand-item-3d-preview__toolbar">
      <Button
        type="button"
        size="sm"
        variant={mode === "envelope" ? "primary" : "secondary"}
        onClick={() => setMode("envelope")}
      >
        {adminLabels.fairStandItems3dModeEnvelope}
      </Button>
      <Button
        type="button"
        size="sm"
        variant={mode === "assembly" ? "primary" : "secondary"}
        disabled={!isRecipe}
        onClick={() => setMode("assembly")}
      >
        {adminLabels.fairStandItems3dModeAssembly}
      </Button>
      <Button
        type="button"
        size="sm"
        variant="secondary"
        disabled={!canSaveAssembly || !isRecipe || mode !== "assembly" || saving}
        onClick={() => void saveAssembly()}
      >
        {saving ? adminLabels.fairStandItemsSaving : adminLabels.fairStandItems3dSaveAssembly}
      </Button>
      <Button
        type="button"
        size="sm"
        variant={snapMode ? "primary" : "secondary"}
        disabled={!isRecipe || mode !== "assembly"}
        aria-pressed={snapMode}
        onClick={() => {
          const next = !snapMode;
          apiRef.current?.setSnapMode(next);
        }}
      >
        {adminLabels.fairStandItems3dCornerSnap}
      </Button>
      <Button
        type="button"
        size="sm"
        variant={assemblyLock ? "primary" : "secondary"}
        disabled={!isRecipe || mode !== "assembly" || (!canLockPair && !assemblyLock)}
        onClick={() => {
          if (assemblyLock) {
            apiRef.current?.unlockAssembly();
            return;
          }
          apiRef.current?.lockPendingPair();
        }}
      >
        {assemblyLock ? adminLabels.fairStandItems3dUnlock : adminLabels.fairStandItems3dLock}
      </Button>
      <Button
        type="button"
        size="sm"
        variant="secondary"
        className="fair-stand-item-3d-preview__expand"
        aria-pressed={expanded}
        onClick={() => setExpanded((value) => !value)}
      >
        {expanded ? adminLabels.fairStandItems3dCollapse : adminLabels.fairStandItems3dExpand}
      </Button>
    </div>
  );

  return (
    <div
      className={[
        "fair-stand-item-3d-preview",
        expanded ? "fair-stand-item-3d-preview--expanded" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {expanded ? (
        <div
          className="fair-stand-item-3d-preview__backdrop"
          aria-hidden="true"
          onClick={() => setExpanded(false)}
        />
      ) : null}
      <div
        className="fair-stand-item-3d-preview__panel"
        role={expanded ? "dialog" : undefined}
        aria-modal={expanded || undefined}
        aria-label={adminLabels.fairStandItemsTabPreview3d}
      >
        {error ? <Banner variant="error">{error}</Banner> : null}
        {status ? <Banner variant="success">{status}</Banner> : null}
        {toolbar}
        {mode === "assembly" ? (
          <div className="fair-stand-item-3d-preview__selection-row">
            <p className="fair-stand-item-3d-preview__selection" aria-live="polite">
              {selectedLabel
                ? `${adminLabels.fairStandItems3dSelectedPrefix}: ${selectedLabel}`
                : adminLabels.fairStandItems3dSelectedNone}
            </p>
            <div className="fair-stand-item-3d-preview__angles" aria-label="Euler açıları">
              {angleFields.map((field) => (
                <label key={field.axis} className={`fair-stand-item-3d-preview__angle ${field.className}`}>
                  <span>{field.label}</span>
                  <input
                    type="number"
                    step="1"
                    inputMode="decimal"
                    disabled={!selectedPart}
                    value={eulerDraft[field.axis]}
                    onFocus={() => {
                      angleFocusRef.current = field.axis;
                    }}
                    onBlur={() => {
                      angleFocusRef.current = null;
                      commitEulerAxis(field.axis);
                    }}
                    onChange={(event) => {
                      const value = event.target.value;
                      setEulerDraft((prev) => ({ ...prev, [field.axis]: value }));
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        commitEulerAxis(field.axis);
                        (event.target as HTMLInputElement).blur();
                      }
                    }}
                    aria-label={field.label}
                  />
                </label>
              ))}
            </div>
          </div>
        ) : null}
        <p className="text-muted fair-stand-item-3d-preview__hint">
          {mode === "assembly"
            ? assemblyLock
              ? `${adminLabels.fairStandItems3dLockActive}: ${assemblyLock.follower.childItemKey}#${assemblyLock.follower.instanceIndex} ← ${assemblyLock.host.childItemKey}#${assemblyLock.host.instanceIndex}`
              : snapMode
                ? snapSession
                  ? `${adminLabels.fairStandItems3dCornerSnapSource}: ${snapSession.childItemKey}#${snapSession.instanceIndex} · ${snapSession.cornerLabel} — ${adminLabels.fairStandItems3dCornerSnapPickTarget}`
                  : adminLabels.fairStandItems3dCornerSnapHint
                : canLockPair
                  ? adminLabels.fairStandItems3dLockHint
                  : adminLabels.fairStandItems3dAssemblyHint
            : adminLabels.fairStandItems3dEnvelopeHint}
          {expanded ? " · Esc: küçült" : null}
        </p>
        <div
          ref={hostRef}
          className="fair-stand-item-3d-preview__canvas"
          aria-label={adminLabels.fairStandItemsTabPreview3d}
        />
      </div>
    </div>
  );
}
