"""Fix PageShell imports wrongly inserted inside multiline import blocks."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "src"
BAD = re.compile(
    r'import \{\s*\nimport \{ PageShell \} from "\.\./components/ui/PageShell";\n'
)


def fix_text(text: str) -> str:
    if "import { PageShell }" not in text:
        return text
    # Remove every standalone PageShell import line first
    without = re.sub(
        r'^import \{ PageShell \} from "\.\./components/ui/PageShell";\r?\n',
        "",
        text,
        flags=re.M,
    )
    # Re-insert once after the last clean import line
    if "<PageShell" not in without and "PageShell" not in without:
        return without
    lines = without.splitlines(keepends=True)
    last_import = -1
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("import "):
            last_import = i
            # skip multiline import
            if line.rstrip().endswith("{") or ("{" in line and "}" not in line):
                i += 1
                while i < len(lines) and "from " not in lines[i]:
                    i += 1
                if i < len(lines):
                    last_import = i
            elif " from " not in line and not line.rstrip().endswith(";"):
                # rare
                pass
        i += 1
    insert_at = last_import + 1 if last_import >= 0 else 0
    lines.insert(insert_at, 'import { PageShell } from "../components/ui/PageShell";\n')
    return "".join(lines)


def main() -> None:
    changed = []
    for path in sorted((ROOT / "pages").glob("*.tsx")) + sorted((ROOT / "dev").glob("*.tsx")):
        original = path.read_text(encoding="utf-8")
        if "PageShell" not in original:
            continue
        fixed = fix_text(original)
        if fixed != original:
            path.write_text(fixed, encoding="utf-8")
            changed.append(path.name)
    print("fixed", len(changed), changed)


if __name__ == "__main__":
    main()
