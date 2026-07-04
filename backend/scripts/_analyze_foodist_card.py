import re
from html import unescape
from pathlib import Path

import httpx

html = httpx.get("https://www.foodistexpo.com/katilimci-listesi", timeout=30).text
blocks = re.findall(r'<a[^>]+href=["\']([^"\']*brand/[^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
lines = [f"count={len(blocks)}"]
for href, inner in blocks:
    text = re.sub(r"<[^>]+>", " ", inner)
    text = " ".join(unescape(text).split())
    lines.append(f"href={href}")
    lines.append(text)
    lines.append("---")
Path("foodist_card_sample.txt").write_text("\n".join(lines), encoding="utf-8")
