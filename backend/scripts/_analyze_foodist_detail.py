import re

import httpx

html = httpx.get("https://www.foodistexpo.com/brand/2a-akuzum-otomotiv-as", timeout=30).text
print("len", len(html))
for pat in ["mailto:", "tel:", "www.", "http", "E-posta", "Telefon", "Web"]:
    print(pat, pat.lower() in html.lower())
print("emails", re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)[:5])
