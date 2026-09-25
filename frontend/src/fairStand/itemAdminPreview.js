/**
 * CI / standalone Fair CRM checkout fallback for Item 3D admin preview.
 * Local Kyrox workspace Vite aliases @fair-stand to the sibling Fair Stand src.
 */

export function envelopeFromForm() {
  return null;
}

export function partFromChildRecord(child, instanceIndex = 0, pose = {}) {
  return {
    childItemKey: String(child?.itemKey || child?.item_key || ""),
    instanceIndex: Number(instanceIndex) || 0,
    widthCm: 10,
    depthCm: 10,
    heightCm: 10,
    colorCss: "#9ca3af",
    xCm: Number(pose.xCm) || 0,
    yCm: Number(pose.yCm) || 0,
    zCm: Number(pose.zCm) || 0,
    rotationXDeg: Number(pose.rotationXDeg) || 0,
    rotationYDeg: Number(pose.rotationYDeg) || 0,
    rotationZDeg: Number(pose.rotationZDeg) || 0,
  };
}

export function mountItemAdminPreview(host) {
  if (!host) throw new TypeError("mountItemAdminPreview requires a host element.");
  host.replaceChildren();
  const message = document.createElement("p");
  message.textContent = "Fair Stand kaynagi yok — 3D onizleme sadece lokal/sibling checkout'ta.";
  message.style.cssText = "margin:0;padding:16px;text-align:center;color:#64748b;";
  host.appendChild(message);
  return {
    setState() {},
    getParts() {
      return [];
    },
    setSelectedEuler() {
      return false;
    },
    setSnapMode() {
      return false;
    },
    getSnapMode() {
      return false;
    },
    lockPendingPair() {
      return false;
    },
    unlockAssembly() {
      return true;
    },
    removeSelectedFromLock() {
      return false;
    },
    getLockUiState() {
      return { lock: null, canLock: false };
    },
    dispose() {
      host.replaceChildren();
    },
  };
}
