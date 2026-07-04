import re
from pathlib import Path

import httpx

html = httpx.get("https://www.foodistexpo.com/brand/44-beydag-peynircilik-gida-sanayi-tic-as", timeout=30).text
Path("detail_sample.html").write_text(html[:50000], encoding="utf-8")

# find website-like patterns
for pat in [r'Web\s*Site', r'Website', r'www\.', r'href=["\']https?://[^"\']+["\']']:
    matches = re.findall(pat, html, re.I)
    print(pat, len(matches))

# labeled website
for m in re.finditer(r'(?:Web\s*Site|Website|Site)\s*:?\s*([^<]+)', html, re.I):
    print("label", m.group(0)[:200])
