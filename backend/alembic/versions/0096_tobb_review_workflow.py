"""Persist TOBB proposals and approved identity mappings."""
from alembic import op
import sqlalchemy as sa

revision = "0096_tobb_review_workflow"
down_revision = "0095_scraper_run_fair_name_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("crm_tobb_fair_mappings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("identity_name", sa.String(500), nullable=False),
        sa.Column("city_key", sa.String(500), nullable=False),
        sa.Column("fair_id", sa.Uuid(), sa.ForeignKey("crm_fairs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("uq_crm_tobb_mapping_identity_city", "crm_tobb_fair_mappings", ["identity_name", "city_key"], unique=True)
    op.create_table("crm_tobb_fair_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("review_key", sa.String(64), nullable=False),
        sa.Column("fair_id", sa.Uuid(), sa.ForeignKey("crm_fairs.id", ondelete="SET NULL")),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("stored_values", sa.JSON(), nullable=False),
        sa.Column("proposed_values", sa.JSON(), nullable=False),
        sa.Column("source_row", sa.JSON(), nullable=False),
        sa.Column("decided_by", sa.Uuid()), sa.Column("decision", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
    )
    op.create_index("uq_crm_tobb_review_pending", "crm_tobb_fair_reviews", ["review_key"], unique=True,
                    postgresql_where=sa.text("status = 'pending'"), sqlite_where=sa.text("status = 'pending'"))
    op.create_index("ix_crm_tobb_review_status_kind", "crm_tobb_fair_reviews", ["status", "kind"])


def downgrade() -> None:
    op.drop_table("crm_tobb_fair_reviews")
    op.drop_table("crm_tobb_fair_mappings")
