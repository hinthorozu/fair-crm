"""Enforce ON DELETE/UPDATE CASCADE on every existing foreign key.

Revision ID: 0075_all_foreign_keys_cascade
Revises: 0074_quote_price
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0075_all_foreign_keys_cascade"
down_revision = "0074_quote_price"
branch_labels = None
depends_on = None


def _foreign_keys() -> list[dict]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    result: list[dict] = []
    for table_name in inspector.get_table_names():
        for fk in inspector.get_foreign_keys(table_name):
            if not fk.get("name"):
                raise RuntimeError(f"Unnamed foreign key on {table_name} cannot be migrated safely")
            result.append({"table": table_name, **fk})
    return result


def _replace_fk(*, fk: dict, ondelete: str, onupdate: str) -> None:
    options = dict(fk.get("options") or {})
    options.pop("ondelete", None)
    options.pop("onupdate", None)

    op.drop_constraint(fk["name"], fk["table"], type_="foreignkey")
    op.create_foreign_key(
        fk["name"],
        fk["table"],
        fk["referred_table"],
        fk["constrained_columns"],
        fk["referred_columns"],
        referent_schema=fk.get("referred_schema"),
        ondelete=ondelete,
        onupdate=onupdate,
        **options,
    )


def upgrade() -> None:
    for fk in _foreign_keys():
        options = fk.get("options") or {}
        if options.get("ondelete") == "CASCADE" and options.get("onupdate") == "CASCADE":
            continue
        _replace_fk(fk=fk, ondelete="CASCADE", onupdate="CASCADE")


def downgrade() -> None:
    # This migration establishes a system-wide FK policy. The previous database
    # contained mixed NO ACTION / RESTRICT / SET NULL / CASCADE semantics, so a
    # generic downgrade cannot reconstruct the exact former state safely.
    raise RuntimeError("0075 is an irreversible foreign-key policy migration")
