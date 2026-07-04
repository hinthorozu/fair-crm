import json
from pathlib import Path

payload = json.loads(Path("foodist_handoff.json").read_text(encoding="utf-8"))
rows = payload["canonical_rows"]
meta = payload["row_metadata"]

with_site = [(r, m) for r, m in zip(rows, meta) if r.get("website")]
without_site = sum(1 for r in rows if not r.get("website"))
valid_with_site = sum(1 for r, m in zip(rows, meta) if r.get("website") and m.get("website_valid"))
invalid_with_site = sum(1 for r, m in zip(rows, meta) if r.get("website") and not m.get("website_valid"))

missing_country = [r["company_name"] for r in rows if not r.get("country")][:10]
invalid_samples = [
    (r.get("company_name"), r.get("website"), m.get("website_valid"))
    for r, m in zip(rows, meta)
    if r.get("website") and not m.get("website_valid")
][:10]

lines = [
    f"with_website={len(with_site)}",
    f"without_website={without_site}",
    f"valid_with_website={valid_with_site}",
    f"invalid_with_website={invalid_with_site}",
    f"parser_accuracy_among_filled={100*(len(with_site)-0)/max(len(with_site),1):.1f}%",
    f"validation_rate_among_filled={100*valid_with_site/max(len(with_site),1):.1f}%",
    f"missing_country_count={sum(1 for r in rows if not r.get('country'))}",
    f"missing_country_samples={missing_country}",
    f"invalid_website_samples={invalid_samples}",
]
Path("foodist_quality_detail.txt").write_text("\n".join(lines), encoding="utf-8")
