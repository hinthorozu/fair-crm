import re
from pathlib import Path

import httpx

html = httpx.get(
    "https://www.foodistexpo.com/brand/44-beydag-peynircilik-gida-sanayi-tic-as",
    timeout=30,
).text
Path("detail_full.html").write_text(html, encoding="utf-8")

for pat in [
    r'class="[^"]*brand[^"]*"',
    r'class="[^"]*company[^"]*"',
    r'class="[^"]*contact[^"]*"',
    r'class="[^"]*detail[^"]*"',
    r"<table",
    r"44beydag",
]:
    matches = re.findall(pat, html, re.I)
    print(pat, len(matches))
    for m in matches[:8]:
        print(" ", m[:120])
