#!/usr/bin/env python3
"""Seed Fair CRM demo customers for local development (dev-only, idempotent).

Inserts Turkish fair/exhibitor customers into the Fair CRM database for the
dev-bypass organization. Safe to run multiple times — skips existing records
by organization_id + normalized_name.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")

DEV_ORG_ID = UUID(
    os.environ.get("FAIR_CRM_DEV_ORGANIZATION_ID", "00000000-0000-4000-8000-000000000010")
)
ALLOWED_ENVS = frozenset({"development", "local", "test"})


@dataclass(frozen=True)
class SeedCustomer:
    display_name: str
    legal_name: str
    trade_name: str
    customer_type: str
    target_status: str  # lead | active | inactive | archived
    country: str
    city: str
    district: str
    address: str
    website: str
    phone: str
    email: str
    description: str


SEED_CUSTOMERS: tuple[SeedCustomer, ...] = (
    SeedCustomer(
        display_name="Sinan Elektronik A.Ş.",
        legal_name="Sinan Elektronik Anonim Şirketi",
        trade_name="Sinan Elektronik",
        customer_type="exhibitor",
        target_status="active",
        country="Türkiye",
        city="İstanbul",
        district="Ümraniye",
        address="Fatih Sultan Mehmet Mah. Sanayi Cad. No:42",
        website="https://www.sinanelektronik.com.tr",
        phone="+90 216 555 0101",
        email="info@sinanelektronik.com.tr",
        description="Elektronik fuar stand ekipmanları tedarikçisi.",
    ),
    SeedCustomer(
        display_name="Umaay Fuar Stand Tasarım",
        legal_name="Umaay Fuar Stand Tasarım Ltd. Şti.",
        trade_name="Umaay Stand",
        customer_type="supplier",
        target_status="active",
        country="Türkiye",
        city="Ankara",
        district="Sincan",
        address="Ostim OSB 1208. Sokak No:5",
        website="https://www.umaay.com",
        phone="+90 312 555 0202",
        email="iletisim@umaay.com",
        description="Modüler fuar stand tasarım ve üretim firması.",
    ),
    SeedCustomer(
        display_name="Kyrox Metal & Wood",
        legal_name="Kyrox Metal ve Ahşap Sanayi Tic. Ltd. Şti.",
        trade_name="Kyrox Metal",
        customer_type="exhibitor",
        target_status="active",
        country="Türkiye",
        city="Bursa",
        district="Nilüfer",
        address="Hasanağa OSB 3. Cadde No:18",
        website="https://www.kyroxmetal.com",
        phone="+90 224 555 0303",
        email="sales@kyroxmetal.com",
        description="Metal ve ahşap fuar standı üreticisi.",
    ),
    SeedCustomer(
        display_name="İstanbul Reklam ve Tabela",
        legal_name="İstanbul Reklam ve Tabela Hizmetleri Ltd. Şti.",
        trade_name="İstanbul Reklam",
        customer_type="partner",
        target_status="active",
        country="Türkiye",
        city="İstanbul",
        district="Başakşehir",
        address="İkitelli OSB Mutfakçılar Sitesi B Blok No:7",
        website="https://www.istanbulreklam.com",
        phone="+90 212 555 0505",
        email="info@istanbulreklam.com",
        description="Fuar tabelası, dijital baskı ve brand uygulamaları.",
    ),
    SeedCustomer(
        display_name="Marmara Fuar Hizmetleri",
        legal_name="Marmara Fuar Hizmetleri Ltd. Şti.",
        trade_name="Marmara Fuar",
        customer_type="organizer",
        target_status="lead",
        country="Türkiye",
        city="İstanbul",
        district="Kadıköy",
        address="Caferağa Mah. Moda Cad. No:88",
        website="https://www.marmarafuar.com",
        phone="+90 216 555 0606",
        email="info@marmarafuar.com",
        description="Bölgesel fuar organizasyon adayı.",
    ),
    SeedCustomer(
        display_name="Ege Stand Tasarım Atölyesi",
        legal_name="Ege Stand Tasarım Atölyesi Ltd. Şti.",
        trade_name="Ege Stand",
        customer_type="supplier",
        target_status="inactive",
        country="Türkiye",
        city="İzmir",
        district="Bornova",
        address="Atatürk OSB 1003 Sokak No:12",
        website="https://www.egestand.com.tr",
        phone="+90 232 555 0707",
        email="info@egestand.com.tr",
        description="Geçici olarak pasif — 2025 sezonu kapalı.",
    ),
    SeedCustomer(
        display_name="Antalya Turizm Fuar Ltd. Şti.",
        legal_name="Antalya Turizm Fuar Ltd. Şti.",
        trade_name="Antalya Turizm Fuar",
        customer_type="exhibitor",
        target_status="lead",
        country="Türkiye",
        city="Antalya",
        district="Muratpaşa",
        address="Fener Mah. Tekelioğlu Cad. No:55",
        website="https://www.antalyafuar.com",
        phone="+90 242 555 0808",
        email="info@antalyafuar.com",
        description="Turizm ve otel fuarları katılımcı adayı.",
    ),
    SeedCustomer(
        display_name="Konya Tekstil Fuarcılık",
        legal_name="Konya Tekstil Fuarcılık San. Tic. A.Ş.",
        trade_name="Konya Tekstil Fuar",
        customer_type="exhibitor",
        target_status="inactive",
        country="Türkiye",
        city="Konya",
        district="Selçuklu",
        address="Sille OSB 2. Cadde No:9",
        website="https://www.konyatekstilfuar.com.tr",
        phone="+90 332 555 0909",
        email="export@konyatekstilfuar.com.tr",
        description="Tekstil fuarları için stand ve lojistik hizmeti.",
    ),
    SeedCustomer(
        display_name="Gebze Endüstriyel Fuarcılık",
        legal_name="Gebze Endüstriyel Fuarcılık Ltd. Şti.",
        trade_name="Gebze Endüstriyel",
        customer_type="exhibitor",
        target_status="active",
        country="Türkiye",
        city="Kocaeli",
        district="Gebze",
        address="Gebze OSB 700. Sokak No:3",
        website="https://www.gebzeendustri.com",
        phone="+90 262 555 1010",
        email="info@gebzeendustri.com",
        description="Endüstriyel fuar standı ve makine sergileme çözümleri.",
    ),
    SeedCustomer(
        display_name="Trabzon Karadeniz Fuar",
        legal_name="Trabzon Karadeniz Fuar Organizasyon Ltd. Şti.",
        trade_name="Karadeniz Fuar",
        customer_type="organizer",
        target_status="lead",
        country="Türkiye",
        city="Trabzon",
        district="Ortahisar",
        address="Sanayi Mah. Fuar Sokak No:1",
        website="https://www.karadenizfuar.com.tr",
        phone="+90 462 555 1111",
        email="info@karadenizfuar.com.tr",
        description="Karadeniz bölgesi fuar organizasyon lead kaydı.",
    ),
    SeedCustomer(
        display_name="Anadolu Mobilya Sanayi",
        legal_name="Anadolu Mobilya Sanayi ve Ticaret A.Ş.",
        trade_name="Anadolu Mobilya",
        customer_type="exhibitor",
        target_status="archived",
        country="Türkiye",
        city="Kayseri",
        district="Melikgazi",
        address="Organize Sanayi Bölgesi 4. Cadde No:12",
        website="https://www.anadolumobilya.com.tr",
        phone="+90 352 555 0404",
        email="export@anadolumobilya.com.tr",
        description="Arşivlenmiş demo kaydı — eski fuar lead.",
    ),
    SeedCustomer(
        display_name="Adana Tarım Fuarcılık",
        legal_name="Adana Tarım Fuarcılık Ltd. Şti.",
        trade_name="Adana Tarım Fuar",
        customer_type="exhibitor",
        target_status="active",
        country="Türkiye",
        city="Adana",
        district="Seyhan",
        address="Turhan Cemal Beriker Bulvarı No:221",
        website="https://www.adanatarimfuar.com",
        phone="+90 322 555 1212",
        email="info@adanatarimfuar.com",
        description="Tarım ve gıda fuarları katılımcısı.",
    ),
    SeedCustomer(
        display_name="Gaziantep Halı Fuar Stand",
        legal_name="Gaziantep Halı Fuar Stand San. Tic. Ltd. Şti.",
        trade_name="Gaziantep Halı Stand",
        customer_type="supplier",
        target_status="lead",
        country="Türkiye",
        city="Gaziantep",
        district="Şehitkamil",
        address="Başpınar OSB 12. Cadde No:6",
        website="https://www.gaziantephali.com.tr",
        phone="+90 342 555 1313",
        email="info@gaziantephali.com.tr",
        description="Halı ve ev tekstili fuar standları.",
    ),
    SeedCustomer(
        display_name="Eski Fuar Lead A.Ş.",
        legal_name="Eski Fuar Lead Anonim Şirketi",
        trade_name="Eski Fuar Lead",
        customer_type="lead",
        target_status="archived",
        country="Türkiye",
        city="Ankara",
        district="Yenimahalle",
        address="Demo Arşiv Sokak No:1",
        website="https://www.eskifuarlead.example.com",
        phone="+90 312 555 1414",
        email="archive@eskifuarlead.example.com",
        description="Arşivlenmiş demo — soft-delete test kaydı.",
    ),
)


def _pagination_demo_customers() -> tuple[SeedCustomer, ...]:
    """Extra idempotent records so page_size=10 yields multiple pages in dev."""
    demos: list[SeedCustomer] = []
    cities = ("İstanbul", "Ankara", "İzmir", "Bursa", "Antalya")
    for index in range(1, 26):
        city = cities[(index - 1) % len(cities)]
        demos.append(
            SeedCustomer(
                display_name=f"Pagination Demo Fuar {index:02d}",
                legal_name=f"Pagination Demo Fuar {index:02d} Ltd. Şti.",
                trade_name=f"Demo Fuar {index:02d}",
                customer_type="exhibitor",
                target_status="active" if index % 3 else "lead",
                country="Türkiye",
                city=city,
                district="Merkez",
                address=f"Demo Cadde No:{index}",
                website=f"https://demo-fuar-{index:02d}.example.com",
                phone=f"+90 212 555 {1000 + index:04d}",
                email=f"demo{index:02d}@example.com",
                description="Pagination test kaydı.",
            )
        )
    return tuple(demos)


SEED_CUSTOMERS = SEED_CUSTOMERS + _pagination_demo_customers()


def _ensure_dev_only() -> None:
    app_env = os.environ.get("APP_ENV", "development").strip().lower()
    if app_env not in ALLOWED_ENVS:
        print(
            f"Refusing to run: APP_ENV={app_env!r} is not allowed. "
            f"Set APP_ENV to one of: {', '.join(sorted(ALLOWED_ENVS))}",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _apply_target_status(customer, *, target_status: str, now: datetime):
    from app.modules.customers.domain.value_objects import CustomerStatus

    if target_status == "archived":
        customer.archive(now=now)
        return

    status_map = {
        "lead": CustomerStatus.LEAD,
        "active": CustomerStatus.ACTIVE,
        "inactive": CustomerStatus.INACTIVE,
    }
    customer.status = status_map[target_status]
    customer.updated_at = now


def _configure_stdio_utf8() -> None:
    """Windows consoles often use cp1252; seed output includes Turkish text."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def main() -> int:
    _configure_stdio_utf8()
    _ensure_dev_only()

    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.modules.customers.domain.entities import Customer
    from app.modules.customers.domain.services.normalizers import compute_normalized_name
    from app.modules.customers.domain.value_objects import CustomerSource, CustomerStatus, CustomerType
    from app.modules.customers.infrastructure.repositories.customer_repository import (
        SqlAlchemyCustomerRepository,
    )

    get_settings.cache_clear()
    settings = get_settings()
    if settings.app_env not in ALLOWED_ENVS:
        print(f"Refusing to run: backend APP_ENV={settings.app_env!r}", file=sys.stderr)
        return 1

    db = SessionLocal()
    repo = SqlAlchemyCustomerRepository(db)
    now = datetime.now(tz=UTC)
    created = 0
    skipped = 0

    try:
        for seed in SEED_CUSTOMERS:
            normalized = compute_normalized_name(
                display_name=seed.display_name,
                legal_name=seed.legal_name,
            )
            from app.modules.customers.infrastructure.persistence.models import CustomerModel

            already_exists = bool(repo.find_by_normalized_name(DEV_ORG_ID, normalized))
            if not already_exists:
                already_exists = (
                    db.query(CustomerModel)
                    .filter(
                        CustomerModel.organization_id == DEV_ORG_ID,
                        CustomerModel.normalized_name == normalized,
                    )
                    .first()
                    is not None
                )

            if already_exists:
                skipped += 1
                print(f"SKIP  {seed.display_name} ({normalized})")
                continue

            customer = Customer.create(
                organization_id=DEV_ORG_ID,
                display_name=seed.display_name,
                legal_name=seed.legal_name,
                trade_name=seed.trade_name,
                customer_type=CustomerType(seed.customer_type),
                status=CustomerStatus.LEAD,
                website=seed.website,
                phone=seed.phone,
                email=seed.email,
                country=seed.country,
                city=seed.city,
                district=seed.district,
                address=seed.address,
                description=seed.description,
                source=CustomerSource.MANUAL,
                now=now,
            )
            _apply_target_status(customer, target_status=seed.target_status, now=now)
            repo.add(customer)
            created += 1
            print(f"ADD   {seed.display_name} [{seed.target_status}]")

        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(
        f"\nDone — organization {DEV_ORG_ID}: "
        f"{created} created, {skipped} skipped (already seeded), "
        f"{len(SEED_CUSTOMERS)} total definitions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
