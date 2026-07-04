import json
from collections import Counter
from pathlib import Path

payload = json.loads(Path("foodist_handoff.json").read_text(encoding="utf-8"))
rows = payload["canonical_rows"]
names = [r.get("company_name", "") for r in rows]
emails = [str(r.get("email") or "").strip() for r in rows]
websites = [str(r.get("website") or "").strip() for r in rows]
phones = [str(r.get("phone") or "").strip() for r in rows]
real_websites = [w for w in websites if w and "googleapis" not in w and "foodistexpo" not in w and "tuyap" not in w]
lines = [
    f"total={len(rows)}",
    f"email_filled={sum(1 for e in emails if e)}",
    f"phone_filled={sum(1 for p in phones if p)}",
    f"website_any={sum(1 for w in websites if w)}",
    f"website_real={len(real_websites)}",
    f"empty_name={sum(1 for n in names if not str(n).strip())}",
    f"dup_names={sum(1 for k,v in Counter(names).items() if v>1 and k)}",
    "website_top=" + str(Counter(websites).most_common(5)),
    "sample_real_websites=" + str(real_websites[:10]),
]
Path("foodist_stats.txt").write_text("\n".join(lines), encoding="utf-8")
