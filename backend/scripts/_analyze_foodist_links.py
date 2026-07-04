import re

import httpx

html = httpx.get("https://www.foodistexpo.com/katilimci-listesi", timeout=30).text
hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
detail = [
    h
    for h in hrefs
    if any(token in h.lower() for token in ("detay", "katilim", "brand", "firma", "exhibitor"))
]
print("total_hrefs", len(hrefs))
print("detail_hrefs_sample")
for item in detail[:25]:
    print(item)
