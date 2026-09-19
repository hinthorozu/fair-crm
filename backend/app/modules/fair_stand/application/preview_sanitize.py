from __future__ import annotations

import re

ALLOWED_MARKUP_TAGS = frozenset({"div", "i", "span"})
FORBIDDEN_CSS = (
    r"@import",
    r"expression\s*\(",
    r"javascript\s*:",
    r"behavior\s*:",
    r"-moz-binding",
    r"@namespace",
)
FORBIDDEN_SELECTOR_ROOTS = ("html", "body", ":root", "*", "html ", "body ")


class PreviewDefinitionError(ValueError):
    pass


def sanitize_markup(markup: str) -> str:
    raw = markup.strip()
    if not raw:
        raise PreviewDefinitionError("markup is required")
    lowered = raw.lower()
    if re.search(r"\son[a-z]+\s*=", lowered):
        raise PreviewDefinitionError("markup cannot include scripts or event handlers")
    if "<style" in lowered or "javascript:" in lowered:
        raise PreviewDefinitionError("markup cannot include scripts or embedded stylesheets")
    tags = {tag.lower() for tag in re.findall(r"</?([a-z0-9]+)", raw, flags=re.I)}
    unknown = tags - ALLOWED_MARKUP_TAGS
    if unknown:
        raise PreviewDefinitionError(f"markup allows only div, i, and span tags; found {sorted(unknown)}")
    if re.search(r"\sstyle\s*=", raw, flags=re.I):
        raise PreviewDefinitionError("markup cannot include inline style attributes")
    return raw


def sanitize_css(css_code: str) -> str:
    css = css_code.strip()
    if not css:
        raise PreviewDefinitionError("css_code is required")
    compact = re.sub(r"\s+", " ", css.lower())
    for pattern in FORBIDDEN_CSS:
        if re.search(pattern, compact, flags=re.I):
            raise PreviewDefinitionError("css_code contains a forbidden construct")
    for selector, _body in _split_rules(css):
        for raw_selector in selector.split(","):
            candidate = raw_selector.strip().lower()
            if candidate in {"html", "body", ":root", "*"} or candidate.startswith(("html ", "body ", ":root ")):
                raise PreviewDefinitionError("css_code cannot target global document selectors")
    return css


def scope_css(css_code: str, scope_selector: str) -> str:
    sanitized = sanitize_css(css_code)
    chunks: list[str] = []
    for rule in _split_rules(sanitized):
        selector, body = rule
        if not selector or not body:
            continue
        parts = []
        for raw_selector in selector.split(","):
            candidate = raw_selector.strip()
            if not candidate:
                continue
            lowered = candidate.lower()
            if lowered.startswith(FORBIDDEN_SELECTOR_ROOTS) or lowered in {"html", "body", ":root"}:
                raise PreviewDefinitionError("css_code cannot target global document selectors")
            if candidate.startswith(scope_selector):
                parts.append(candidate)
            elif candidate == ".module-drag-preview":
                parts.append(scope_selector)
            elif candidate.startswith(".module-drag-preview "):
                parts.append(f"{scope_selector}{candidate[len('.module-drag-preview'):]}")
            else:
                parts.append(f"{scope_selector} {candidate}")
        chunks.append(", ".join(parts) + " {" + body + "}")
    return "\n".join(chunks)


def _split_rules(css_code: str) -> list[tuple[str, str]]:
    rules: list[tuple[str, str]] = []
    depth = 0
    start = 0
    for index, char in enumerate(css_code):
        if char == "{":
            if depth == 0:
                selector = css_code[start:index]
                start = index + 1
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                rules.append((selector.strip(), css_code[start:index].strip()))
                start = index + 1
            if depth < 0:
                raise PreviewDefinitionError("css_code has unbalanced braces")
    if depth != 0:
        raise PreviewDefinitionError("css_code has unbalanced braces")
    return rules
