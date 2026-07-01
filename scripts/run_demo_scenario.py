#!/usr/bin/env python3
"""Run Fair CRM demo customer scenario via dev bypass."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8001/api/v1"
ORG_ID = "00000000-0000-4000-8000-000000000010"
HEADERS = {
    "Authorization": "Bearer dev-bypass",
    "X-Organization-Id": ORG_ID,
}

CUSTOMERS = [
    {
        "display_name": "Sinan Elektronik A.Ş.",
        "legal_name": "Sinan Elektronik Anonim Şirketi",
        "trade_name": "Sinan Elektronik",
        "customer_type": "exhibitor",
        "status": "active",
        "country": "Türkiye",
        "city": "İstanbul",
        "district": "Ümraniye",
        "address": "Fatih Sultan Mehmet Mah. Sanayi Cad. No:42",
        "website": "https://www.sinanelektronik.com.tr",
        "phone": "+90 216 555 0101",
        "email": "info@sinanelektronik.com.tr",
        "source": "manual",
        "description": "Elektronik fuar stand ekipmanları tedarikçisi. Not: 2025 İstanbul fuarında stand kurulumu yapıldı.",
    },
    {
        "display_name": "Umaay Fuar Stand Tasarım",
        "legal_name": "Umaay Fuar Stand Tasarım Ltd. Şti.",
        "trade_name": "Umaay Stand",
        "customer_type": "supplier",
        "status": "active",
        "country": "Türkiye",
        "city": "Ankara",
        "district": "Sincan",
        "address": "Ostim OSB 1208. Sokak No:5",
        "website": "https://www.umaay.com",
        "phone": "+90 312 555 0202",
        "email": "iletisim@umaay.com",
        "source": "manual",
        "description": "Modüler fuar stand tasarım ve üretim firması. Not: Referans müşteri.",
    },
    {
        "display_name": "Kyrox Metal & Wood",
        "legal_name": "Kyrox Metal ve Ahşap Sanayi Tic. Ltd. Şti.",
        "trade_name": "Kyrox Metal",
        "customer_type": "exhibitor",
        "status": "active",
        "country": "Türkiye",
        "city": "Bursa",
        "district": "Nilüfer",
        "address": "Hasanağa OSB 3. Cadde No:18",
        "website": "https://www.kyroxmetal.com",
        "phone": "+90 224 555 0303",
        "email": "sales@kyroxmetal.com",
        "source": "manual",
        "description": "Metal ve ahşap fuar standı üreticisi. Not: Yıllık bakım anlaşması mevcut.",
    },
    {
        "display_name": "Anadolu Mobilya Sanayi",
        "legal_name": "Anadolu Mobilya Sanayi ve Ticaret A.Ş.",
        "trade_name": "Anadolu Mobilya",
        "customer_type": "exhibitor",
        "status": "active",
        "country": "Türkiye",
        "city": "Kayseri",
        "district": "Melikgazi",
        "address": "Organize Sanayi Bölgesi 4. Cadde No:12",
        "website": "https://www.anadolumobilya.com.tr",
        "phone": "+90 352 555 0404",
        "email": "export@anadolumobilya.com.tr",
        "source": "manual",
        "description": "Ofis ve fuar mobilyası üreticisi. Not: Eski lead — arşivlenecek.",
    },
    {
        "display_name": "İstanbul Reklam ve Tabela",
        "legal_name": "İstanbul Reklam ve Tabela Hizmetleri Ltd. Şti.",
        "trade_name": "İstanbul Reklam",
        "customer_type": "partner",
        "status": "active",
        "country": "Türkiye",
        "city": "İstanbul",
        "district": "Başakşehir",
        "address": "İkitelli OSB Mutfakçılar Sitesi B Blok No:7",
        "website": "https://www.istanbulreklam.com",
        "phone": "+90 212 555 0505",
        "email": "info@istanbulreklam.com",
        "source": "manual",
        "description": "Fuar tabelası, dijital baskı ve brand uygulamaları. Not: Kadıköy fuar projesi tamamlandı.",
    },
]

EXPECTED_NORMALIZED = {
    "Sinan Elektronik A.Ş.": "SINAN ELEKTRONIK",
    "Umaay Fuar Stand Tasarım": "UMAAY FUAR STAND TASARIM",
    "Kyrox Metal & Wood": "KYROX METAL AHSAP",
    "Anadolu Mobilya Sanayi": "ANADOLU MOBILYA",
    "İstanbul Reklam ve Tabela": "ISTANBUL REKLAM TABELA HIZMETLERI",
}


def main() -> int:
    report: dict = {"errors": [], "created": {}, "verifications": {}, "swagger_usable": True}
    client = httpx.Client(base_url=BASE, headers=HEADERS, timeout=15.0)

    # Health + bypass probe
    health = httpx.get("http://127.0.0.1:8001/health", timeout=5.0)
    if health.status_code != 200:
        report["errors"].append(f"Health check failed: {health.status_code}")
        _write(report)
        return 1

    probe = client.post("/customers", json={"display_name": "__bypass_probe__"})
    if probe.status_code == 401:
        report["errors"].append("Dev bypass not active — enable FAIR_CRM_DEV_BYPASS_CORE=true and restart")
        _write(report)
        return 1
    if probe.status_code == 201:
        client.delete(f"/customers/{probe.json()['id']}")

    # 1. Create 5 customers
    ids: dict[str, str] = {}
    for payload in CUSTOMERS:
        resp = client.post("/customers", json=payload)
        if resp.status_code != 201:
            report["errors"].append(f"Create failed for {payload['display_name']}: {resp.status_code} {resp.text}")
            continue
        body = resp.json()
        ids[payload["display_name"]] = body["id"]
        report["created"][payload["display_name"]] = {
            "id": body["id"],
            "normalized_name": body["normalized_name"],
        }

    # 3. List all 5
    list_resp = client.get("/customers", params={"limit": 100})
    list_ok = list_resp.status_code == 200 and len(list_resp.json().get("items", [])) >= 5
    demo_ids = set(ids.values())
    found_in_list = {i["id"] for i in list_resp.json().get("items", []) if i["id"] in demo_ids}
    report["verifications"]["list_all_5"] = {
        "ok": list_ok and len(found_in_list) == len(ids),
        "total_items": len(list_resp.json().get("items", [])),
        "demo_found": len(found_in_list),
    }

    # Search Sinan
    sinan_resp = client.get("/customers", params={"search": "Sinan"})
    sinan_items = sinan_resp.json().get("items", []) if sinan_resp.status_code == 200 else []
    report["verifications"]["search_sinan"] = {
        "ok": any("Sinan" in i["display_name"] for i in sinan_items),
        "count": len(sinan_items),
        "matches": [i["display_name"] for i in sinan_items],
    }

    # Search İstanbul
    istanbul_resp = client.get("/customers", params={"search": "İstanbul"})
    istanbul_items = istanbul_resp.json().get("items", []) if istanbul_resp.status_code == 200 else []
    report["verifications"]["search_istanbul"] = {
        "ok": len(istanbul_items) >= 1,
        "count": len(istanbul_items),
        "matches": [i["display_name"] for i in istanbul_items],
    }

    # normalized_name check
    norm_checks = {}
    for name, expected in EXPECTED_NORMALIZED.items():
        if name not in report["created"]:
            norm_checks[name] = {"ok": False, "reason": "not created"}
            continue
        actual = report["created"][name]["normalized_name"]
        norm_checks[name] = {"ok": actual == expected, "expected": expected, "actual": actual}
    report["verifications"]["normalized_names"] = norm_checks

    # 4. Update Umaay
    umaay_id = ids.get("Umaay Fuar Stand Tasarım")
    update_payload = {
        "phone": "+90 312 555 9999",
        "website": "https://www.umaay-stand.com.tr",
        "description": "Modüler fuar stand tasarım ve üretim firması. Not: 2026 fuar sezonu için revize teklif gönderildi.",
    }
    update_resp = client.patch(f"/customers/{umaay_id}", json=update_payload)
    report["update"] = {
        "customer": "Umaay Fuar Stand Tasarım",
        "status_code": update_resp.status_code,
        "ok": update_resp.status_code == 200,
    }
    if update_resp.status_code == 200:
        body = update_resp.json()
        report["update"]["result"] = {
            "phone": body.get("phone"),
            "website": body.get("website"),
            "description": body.get("description"),
        }

    # 5. Archive Anadolu
    anadolu_id = ids.get("Anadolu Mobilya Sanayi")
    archive_resp = client.delete(f"/customers/{anadolu_id}")
    report["archive"] = {
        "customer": "Anadolu Mobilya Sanayi",
        "status_code": archive_resp.status_code,
        "ok": archive_resp.status_code == 200,
    }
    if archive_resp.status_code == 200:
        report["archive"]["result"] = {
            "status": archive_resp.json().get("status"),
            "deleted_at": archive_resp.json().get("deleted_at"),
        }

    # 6. Verify after changes
    umaay_get = client.get(f"/customers/{umaay_id}")
    report["verifications"]["umaay_after_update"] = {
        "ok": umaay_get.status_code == 200 and umaay_get.json().get("phone") == "903125559999",
        "phone": umaay_get.json().get("phone") if umaay_get.status_code == 200 else None,
        "website": umaay_get.json().get("website") if umaay_get.status_code == 200 else None,
    }

    active_list = client.get("/customers", params={"status": "active", "limit": 100})
    active_ids = {i["id"] for i in active_list.json().get("items", [])} if active_list.status_code == 200 else set()
    report["verifications"]["anadolu_not_in_active_list"] = {
        "ok": anadolu_id not in active_ids,
        "active_count": len(active_ids),
    }

    anadolu_get = client.get(f"/customers/{anadolu_id}")
    report["verifications"]["anadolu_fetch_by_id"] = {
        "status_code": anadolu_get.status_code,
        "supported": anadolu_get.status_code == 200,
        "note": "Archived records use soft-delete; GET by id returns 404 when deleted_at is set.",
    }

    report["swagger_usable"] = len(report["errors"]) == 0
    def _checks_ok(section: object) -> bool:
        if isinstance(section, dict):
            if "ok" in section:
                return bool(section["ok"])
            return all(_checks_ok(v) for v in section.values())
        return True

    report["summary"] = {
        "all_ok": (
            _checks_ok(report["verifications"])
            and report.get("update", {}).get("ok", False)
            and report.get("archive", {}).get("ok", False)
            and len(report["created"]) == 5
            and not report["errors"]
        ),
    }

    _write(report)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["summary"]["all_ok"] else 1


def _write(report: dict) -> None:
    out = Path(__file__).resolve().parent / "demo_scenario_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report written to {out}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
