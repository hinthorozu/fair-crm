import re
from urllib.parse import urljoin

import httpx

base = "https://www.foodistexpo.com/katilimci-listesi"
all_pages: set[str] = {base}
queue = [base]
seen = set()
total_brands = 0

while queue:
    url = queue.pop(0)
    if url in seen:
        continue
    seen.add(url)
    html = httpx.get(url, timeout=30).text
    brands = re.findall(r'href=["\'](brand/[^"\']+)["\']', html)
    total_brands += len(brands)
    page_links = re.findall(r'href=["\']([^"\']*katilimci-listesi[^"\']*)["\']', html)
    for href in page_links:
        full = urljoin(base, href)
        if full not in seen and "katilimci-listesi" in full:
            queue.append(full)

print("pages", len(seen))
print("total_brand_links", total_brands)
print("unique estimate", total_brands)  # may have dupes across revisit
