/**
 * CI / standalone Fair CRM checkout fallback for assembly pose helpers.
 * Local Kyrox workspace Vite aliases @fair-stand to the sibling Fair Stand src.
 */

export function mergeAssemblyPoses(bomParts, savedParts) {
  const byKey = new Map();
  if (Array.isArray(savedParts)) {
    for (const saved of savedParts) {
      if (!saved?.childItemKey) continue;
      const index = Number(saved.instanceIndex);
      if (!Number.isInteger(index) || index < 0) continue;
      byKey.set(`${saved.childItemKey}#${index}`, saved);
    }
  }
  return (Array.isArray(bomParts) ? bomParts : []).map((part) => {
    const saved = byKey.get(`${part.childItemKey}#${part.instanceIndex}`);
    if (!saved) return { ...part };
    const lockRaw = saved.lockGroupId ?? saved.lock_group_id;
    const lockGroupId =
      Number.isInteger(Number(lockRaw)) && Number(lockRaw) >= 1 ? Number(lockRaw) : null;
    return {
      ...part,
      xCm: Number.isFinite(Number(saved.xCm)) ? Number(saved.xCm) : part.xCm,
      yCm: Number.isFinite(Number(saved.yCm)) ? Number(saved.yCm) : part.yCm,
      zCm: Number.isFinite(Number(saved.zCm)) ? Number(saved.zCm) : part.zCm,
      rotationXDeg: Number.isFinite(Number(saved.rotationXDeg))
        ? Number(saved.rotationXDeg)
        : part.rotationXDeg,
      rotationYDeg: Number.isFinite(Number(saved.rotationYDeg))
        ? Number(saved.rotationYDeg)
        : part.rotationYDeg,
      rotationZDeg: Number.isFinite(Number(saved.rotationZDeg))
        ? Number(saved.rotationZDeg)
        : part.rotationZDeg,
      lockGroupId,
    };
  });
}

/** Standalone stub: no live catalog expand; return saved poses only. */
export function buildLiveAssemblyParts(_parentItem, savedParts, _getItemFn) {
  return normalizeAssemblyPartsPayload(savedParts);
}

export function normalizeAssemblyPartsPayload(parts) {
  if (!Array.isArray(parts)) return [];
  return parts
    .map((row) => {
      if (!row || typeof row !== "object") return null;
      const childItemKey = String(row.childItemKey ?? row.child_item_key ?? "").trim();
      if (!childItemKey) return null;
      const instanceIndex = Number(row.instanceIndex ?? row.instance_index);
      if (!Number.isInteger(instanceIndex) || instanceIndex < 0) return null;
      const lockRaw = row.lockGroupId ?? row.lock_group_id;
      const lockGroupId =
        Number.isInteger(Number(lockRaw)) && Number(lockRaw) >= 1 ? Number(lockRaw) : null;
      return {
        childItemKey,
        instanceIndex,
        xCm: Number(row.xCm ?? row.x_cm) || 0,
        yCm: Number(row.yCm ?? row.y_cm) || 0,
        zCm: Number(row.zCm ?? row.z_cm) || 0,
        rotationXDeg: Number(row.rotationXDeg ?? row.rotation_x_deg) || 0,
        rotationYDeg: Number(row.rotationYDeg ?? row.rotation_y_deg) || 0,
        rotationZDeg: Number(row.rotationZDeg ?? row.rotation_z_deg) || 0,
        lockGroupId,
      };
    })
    .filter(Boolean);
}
