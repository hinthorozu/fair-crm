"""One-shot helper: migrate page wrappers to PageShell (P3)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "src"
IMPORT = 'import { PageShell } from "../components/ui/PageShell";\n'
OPEN_RE = re.compile(r'<div(\s+)className="page(?:\s+([^"]*))?"([^>]*)>')


def find_matching_close(text: str, start: int) -> int | None:
    i = start
    depth = 1
    while i < len(text):
        if text.startswith("</div>", i):
            depth -= 1
            if depth == 0:
                return i
            i += 6
            continue
        if text.startswith("<div", i):
            gt = text.find(">", i)
            if gt == -1:
                return None
            if text[gt - 1] != "/":
                depth += 1
            i = gt + 1
            continue
        i += 1
    return None


def replace_page_divs(text: str) -> str:
    parts: list[str] = []
    pos = 0
    while True:
        m = OPEN_RE.search(text, pos)
        if not m:
            parts.append(text[pos:])
            break
        parts.append(text[pos : m.start()])
        domain = (m.group(2) or "").strip()
        rest = (m.group(3) or "").strip()
        close_at = find_matching_close(text, m.end())
        if close_at is None:
            parts.append(m.group(0))
            pos = m.end()
            continue
        attr_bits: list[str] = []
        if domain:
            attr_bits.append(f'className="{domain}"')
        if rest:
            attr_bits.append(rest)
        open_tag = "<PageShell" + ((" " + " ".join(attr_bits)) if attr_bits else "") + ">"
        parts.append(open_tag)
        parts.append(text[m.end() : close_at])
        parts.append("</PageShell>")
        pos = close_at + len("</div>")
    return "".join(parts)


def wrap_bare_root(text: str, full_width: bool = False) -> str:
    if "<PageShell" in text:
        return text
    m = re.search(r"(return\s*\(\s*)(<div(\s+className=\"([^\"]*)\")?([^>]*)>)", text)
    if not m:
        return text
    window = text[m.start() : m.start() + 600]
    cls = m.group(4) or ""
    if not (
        "PageHeader" in window
        or cls.endswith("-page")
        or (cls == "" and "PageHeader" in text[m.end() : m.end() + 2500])
    ):
        return text
    close_at = find_matching_close(text, m.end())
    if close_at is None:
        return text
    domain = (m.group(4) or "").strip()
    rest = (m.group(5) or "").strip()
    attr_bits: list[str] = []
    if domain:
        attr_bits.append(f'className="{domain}"')
    if rest:
        attr_bits.append(rest)
    if full_width:
        attr_bits.append("fullWidth")
    open_tag = "<PageShell" + ((" " + " ".join(attr_bits)) if attr_bits else "") + ">"
    return (
        text[: m.start(2)]
        + open_tag
        + text[m.end() : close_at]
        + "</PageShell>"
        + text[close_at + len("</div>") :]
    )


def ensure_import(text: str) -> str:
    if 'from "../components/ui/PageShell"' in text or "from '../components/ui/PageShell'" in text:
        return text
    if "<PageShell" not in text:
        return text
    lines = text.splitlines(keepends=True)
    last_import = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("import ") or line.startswith("import type "):
            # skip to end of multiline import block
            if "{" in line and "}" not in line:
                i += 1
                while i < len(lines) and "from " not in lines[i]:
                    i += 1
                if i < len(lines):
                    last_import = i
            else:
                last_import = i
        i += 1
    lines.insert(last_import + 1, IMPORT)
    return "".join(lines)


def main() -> None:
    targets = list((ROOT / "pages").glob("*.tsx")) + list((ROOT / "dev").glob("*.tsx"))
    changed: list[str] = []
    for path in sorted(targets):
        if path.name == "LoginPage.tsx":
            continue
        original = path.read_text(encoding="utf-8")
        text = replace_page_divs(original)
        text = wrap_bare_root(text, full_width=path.name == "ImportWizardPage.tsx")
        text = ensure_import(text)
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())
    print(f"changed {len(changed)}")
    for c in changed:
        print(c)


if __name__ == "__main__":
    main()
