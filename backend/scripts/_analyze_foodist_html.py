import re
from urllib.parse import urljoin

import httpx

url = "https://www.foodistexpo.com/katilimci-listesi"
html = httpx.get(url, timeout=30).text
pattern = re.compile(
    r'<a[^>]+href=["\']([^"\']*brand/[^"\']+)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
matches = pattern.findall(html)
print("matches", len(matches))
for href, inner in matches[:3]:
    print("---")
    print("href", href)
    print("inner", re.sub(r"\s+", " ", inner)[:120])
    # get surrounding block
    idx = html.find(href)
    block = html[max(0, idx - 200) : idx + 400]
    text = re.sub(r"<[^>]+>", " ", block)
    text = re.sub(r"\s+", " ", text).strip()
    print("block", text[:250])

# pagination
pages = sorted(set(re.findall(r"katilimci-listesi\?page=(\d+)", html)))
print("pages", pages)
