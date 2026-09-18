/**
 * CI / standalone Fair CRM checkout fallback.
 * Local Kyrox workspace Vite aliases @fair-stand to the sibling Fair Stand src.
 */
export function mountFairStand(container, _options = {}) {
  if (!container) return () => {};
  container.replaceChildren();
  return () => {
    container.replaceChildren();
  };
}
