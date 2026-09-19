/**
 * CI / standalone Fair CRM checkout fallback for admin live preview.
 * Local workspace Vite aliases @fair-stand to the sibling Fair Stand src.
 */

const ALLOWED_TAGS = new Set(["DIV", "I", "SPAN"]);

export function previewWidthPx(widthCm) {
  const width = Number(widthCm);
  if (!Number.isFinite(width) || width <= 0) return 24;
  return Math.max(12, Math.round((width / 350) * 68));
}

export function scopePreviewCss(cssCode, scopeSelector) {
  if (typeof cssCode !== "string" || cssCode.trim() === "") {
    throw new TypeError("Catalog preview cssCode is required.");
  }
  const lowered = cssCode.toLowerCase();
  if (/@import|expression\s*\(|javascript\s*:|behavior\s*:|-moz-binding|@namespace/.test(lowered)) {
    throw new TypeError("Catalog preview cssCode contains a forbidden construct.");
  }
  return splitCssRules(cssCode)
    .map(([selector, body]) => {
      const parts = selector
        .split(",")
        .map((raw) => {
          const candidate = raw.trim();
          if (!candidate) return "";
          const token = candidate.toLowerCase();
          if (token === "html" || token === "body" || token === ":root" || token === "*") {
            throw new TypeError("Catalog preview cssCode cannot target global document selectors.");
          }
          if (candidate.startsWith(scopeSelector)) return candidate;
          if (candidate === ".module-drag-preview") return scopeSelector;
          if (candidate.startsWith(".module-drag-preview ")) {
            return `${scopeSelector}${candidate.slice(".module-drag-preview".length)}`;
          }
          return `${scopeSelector} ${candidate}`;
        })
        .filter(Boolean);
      return `${parts.join(", ")} {${body}}`;
    })
    .join("\n");
}

function splitCssRules(cssCode) {
  const rules = [];
  let depth = 0;
  let start = 0;
  let selector = "";
  for (let index = 0; index < cssCode.length; index += 1) {
    const char = cssCode[index];
    if (char === "{") {
      if (depth === 0) {
        selector = cssCode.slice(start, index);
        start = index + 1;
      }
      depth += 1;
    } else if (char === "}") {
      depth -= 1;
      if (depth === 0) {
        rules.push([selector.trim(), cssCode.slice(start, index).trim()]);
        start = index + 1;
      }
      if (depth < 0) throw new TypeError("Catalog preview cssCode has unbalanced braces.");
    }
  }
  if (depth !== 0) throw new TypeError("Catalog preview cssCode has unbalanced braces.");
  return rules;
}

function parseAttributes(raw) {
  const attrs = {};
  const pattern = /([a-zA-Z0-9:-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'))?/g;
  let match = pattern.exec(raw);
  while (match) {
    attrs[match[1]] = match[2] ?? match[3] ?? "";
    match = pattern.exec(raw);
  }
  return attrs;
}

export function parsePreviewMarkup(markup, document) {
  if (typeof markup !== "string" || markup.trim() === "") {
    throw new TypeError("Catalog preview markup is required.");
  }
  if (/<script|<\/script|\son[a-z]+\s*=|<style/i.test(markup)) {
    throw new TypeError("Catalog preview markup cannot include scripts or event handlers.");
  }
  const tokens = markup.match(/<\/?[a-z0-9]+[^>]*\/?>|[^<]+/gi) || [];
  const root = document.createElement("div");
  const stack = [root];
  for (const token of tokens) {
    const trimmed = token.trim();
    if (!trimmed) continue;
    if (!trimmed.startsWith("<")) continue;
    const close = trimmed.match(/^<\/([a-z0-9]+)/i);
    if (close) {
      if (stack.length > 1) stack.pop();
      continue;
    }
    const open = trimmed.match(/^<([a-z0-9]+)([^>]*)\/?>$/i);
    if (!open) {
      throw new TypeError("Catalog preview markup is invalid.");
    }
    const tag = open[1].toUpperCase();
    if (!ALLOWED_TAGS.has(tag)) {
      throw new TypeError(`Catalog preview markup allows only div, i, and span tags; found ${tag.toLowerCase()}.`);
    }
    const element = document.createElement(tag.toLowerCase());
    const attrs = parseAttributes(open[2] || "");
    if (Object.prototype.hasOwnProperty.call(attrs, "style")) {
      throw new TypeError("Catalog preview markup cannot include inline style attributes.");
    }
    Object.entries(attrs).forEach(([name, value]) => {
      if (name.toLowerCase() === "class") {
        element.className = value;
        return;
      }
      if (name.toLowerCase().startsWith("data-")) {
        const datasetKey = name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
        element.dataset[datasetKey] = value;
        return;
      }
      throw new TypeError(`Catalog preview markup cannot include attribute ${name}.`);
    });
    stack[stack.length - 1].appendChild(element);
    if (!trimmed.endsWith("/>") && !/^<(?:i|span)\b[^>]*\/>$/i.test(trimmed)) {
      stack.push(element);
    }
  }
  return [...root.childNodes];
}

function applyPreviewContext(root, context) {
  const widthPx = previewWidthPx(context.widthCm);
  const walk = (node) => {
    if (!node) return;
    const dataset = node.dataset || {};
    if (Object.prototype.hasOwnProperty.call(dataset, "previewWidth") || node.getAttribute?.("data-preview-width") != null) {
      const minWidth = Number(dataset.previewMinWidth || 0);
      node.style.width = `${Math.max(minWidth, widthPx)}px`;
    }
    if (dataset.autoSpans) {
      const count = Number(dataset.autoSpans);
      for (let index = 0; index < count; index += 1) {
        node.appendChild(node.ownerDocument?.createElement?.("span") ?? globalThis.document.createElement("span"));
      }
    }
    if (Object.prototype.hasOwnProperty.call(dataset, "eyes")) {
      node.dataset.eyes = Number(context.eyeCount) === 3 ? "3" : "2";
    }
    if (Object.prototype.hasOwnProperty.call(dataset, "videoWall")) {
      node.classList.add("is-video-wall");
      if (Number(context.videoWallRows) === 3 && Number(context.videoWallCols) === 3) {
        node.classList.add("is-video-wall-3x3");
      }
    }
    if (Object.prototype.hasOwnProperty.call(dataset, "flatPanel")) {
      for (let index = 0; index < 7; index += 1) {
        node.appendChild((node.ownerDocument || globalThis.document).createElement("span"));
      }
    }
    (node.childNodes || []).forEach(walk);
  };
  walk(root);
}

function ensurePreviewCss(document, previewId, cssCode, scopeSelector) {
  if (!document?.head?.appendChild) return;
  const styleId = `fair-stand-preview-css-${previewId}`;
  let style = document.getElementById?.(styleId) || document.querySelector?.(`#${styleId}`);
  const scoped = scopePreviewCss(cssCode, scopeSelector);
  if (!style) {
    style = document.createElement("style");
    style.id = styleId;
    document.head.appendChild(style);
  }
  style.textContent = scoped;
}

export function renderCatalogPreview(definition, context = {}, hostDocument = globalThis.document) {
  const previewId = Number(definition?.id);
  if (!Number.isInteger(previewId) || previewId <= 0) {
    throw new TypeError("Catalog preview definition is required.");
  }
  const preview = hostDocument.createElement("div");
  preview.className = "module-drag-preview";
  const scope = `preview-${previewId}`;
  preview.dataset.previewScope = scope;
  preview.dataset.previewId = String(previewId);
  const scopeSelector = `.module-drag-preview[data-preview-scope="${scope}"]`;
  if (definition.cssCode) {
    ensurePreviewCss(hostDocument, previewId, definition.cssCode, scopeSelector);
  }
  const nodes = parsePreviewMarkup(definition.markup, hostDocument);
  nodes.forEach((node) => {
    applyPreviewContext(node, context);
    preview.appendChild(node);
  });
  return preview;
}
