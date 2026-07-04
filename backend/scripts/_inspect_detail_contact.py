import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

urls = [
    "https://www.foodistexpo.com/brand/44-beydag-peynircilik-gida-sanayi-tic-as",
    "https://www.foodistexpo.com/brand/ada-food-gida-sanayi-ve-ticaret-as",
]
for url in urls:
    html = httpx.get(url, timeout=30).text
    text = re.sub(r"<[^>]+>", " ", html)
    text = " ".join(text.split())
    for label in ["Web Site", "Website", "E-posta", "Telefon"]:
        idx = text.find(label)
        if idx >= 0:
            print(url)
            print(label, ":", text[idx : idx + 120])
    # find external links in contact section
    contact_links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
    print("links", [l for l in contact_links if "foodist" not in l and "google" not in l and "tuyap" not in l and "cdn" not in l][:8])
    print("---")
