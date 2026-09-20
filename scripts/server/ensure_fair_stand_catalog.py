#!/usr/bin/env python3
"""Fill fair_stand catalog only when empty.

Prefer leftover fair_crm.fair_stand_* rows (no reseed, no DROP of source).
If CRM tables are already gone, seed the canonical catalog. Never truncate a
non-empty fair_stand catalog.
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.orm import Session

TABLES = (
    "fair_stand_categories",
    "fair_stand_catalog_preview_kinds",
    "fair_stand_items",
    "fair_stand_item_dimensions",
    "fair_stand_item_scene_dimensions",
    "fair_stand_item_strip_occupancy",
    "fair_stand_item_assets",
    "fair_stand_item_components",
    "fair_stand_item_video_walls",
    "fair_stand_item_body_parts",
)


def _count_categories(engine) -> int:
    with engine.connect() as conn:
        if "fair_stand_categories" not in inspect(engine).get_table_names():
            return 0
        return int(conn.execute(text("SELECT COUNT(*) FROM fair_stand_categories")).scalar() or 0)


def _copy_from_crm(src_url: str, dst_url: str) -> int:
    src = create_engine(src_url)
    dst = create_engine(dst_url)
    src_tables = set(inspect(src).get_table_names())
    if "fair_stand_categories" not in src_tables:
        return 0
    src_count = _count_categories(src)
    if src_count == 0:
        return 0
    present = [name for name in TABLES if name in src_tables]
    src_meta = MetaData()
    dst_meta = MetaData()
    src_meta.reflect(bind=src, only=tuple(present))
    dst_meta.reflect(bind=dst, only=tuple(present))
    with dst.begin() as conn:
        conn.execute(text("SET session_replication_role = replica"))
        for name in reversed(present):
            conn.execute(text(f'TRUNCATE TABLE "{name}" CASCADE'))
        conn.execute(text("SET session_replication_role = origin"))
        copied = 0
        for name in present:
            rows = src.connect().execute(src_meta.tables[name].select()).mappings().all()
            if not rows:
                print(f"copy {name} 0")
                continue
            conn.execute(dst_meta.tables[name].insert(), [dict(row) for row in rows])
            print(f"copy {name} {len(rows)}")
            if name == "fair_stand_categories":
                copied = len(rows)
    return copied


def _seed(dst_url: str) -> None:
    from app.db.session import SessionLocal
    from app.modules.fair_stand.infrastructure.seed_catalog import seed_fair_stand_catalog

    os.environ.setdefault("FAIR_STAND_DATABASE_URL", dst_url)
    session = SessionLocal()
    try:
        seed_fair_stand_catalog(session)
        session.commit()
        print("seed_fair_stand_catalog applied")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> int:
    dst = os.environ.get("FAIR_STAND_DATABASE_URL") or os.environ.get("DATABASE_URL")
    src = os.environ.get("FAIR_CRM_DATABASE_URL") or os.environ.get("FAIR_CRM_SOURCE_DATABASE_URL")
    if not dst:
        print("FAIR_STAND_DATABASE_URL missing", file=sys.stderr)
        return 1
    dst_engine = create_engine(dst)
    existing = _count_categories(dst_engine)
    if existing > 0:
        print(f"fair_stand catalog already populated ({existing} categories); leaving rows untouched")
        return 0
    if src:
        copied = _copy_from_crm(src, dst)
        if copied > 0:
            print(f"copied catalog from fair_crm ({copied} categories)")
            return 0
        print("fair_crm leftover fair_stand_* tables missing or empty; seeding canonical catalog")
    else:
        print("FAIR_CRM_DATABASE_URL unset; seeding canonical catalog")
    _seed(dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
