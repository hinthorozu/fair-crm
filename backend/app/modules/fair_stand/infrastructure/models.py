from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text as sa_text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Alembic 0085/0087 seed mapping only. Not part of CRM Base.metadata."""

CASCADE = {"ondelete": "CASCADE", "onupdate": "CASCADE"}


class FairStandCategoryModel(Base):
    __tablename__ = "fair_stand_categories"
    __table_args__ = (
        UniqueConstraint("catalog_index", name="uq_fair_stand_categories_catalog_index"),
        CheckConstraint("catalog_index > 0", name="ck_fair_stand_categories_catalog_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    catalog_name: Mapped[str] = mapped_column(String(128), nullable=False)
    catalog_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    items: Mapped[list["FairStandItemModel"]] = relationship(back_populates="category")


class FairStandCatalogPreviewKindModel(Base):
    __tablename__ = "fair_stand_catalog_preview_kinds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    markup: Mapped[str] = mapped_column(sa_text(), nullable=False)
    css_code: Mapped[str] = mapped_column(sa_text(), nullable=False)
    sort_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FairStandItemModel(Base):
    __tablename__ = "fair_stand_items"
    __table_args__ = (
        CheckConstraint(
            "eye_count IS NULL OR eye_count IN (2, 3)",
            name="ck_fair_stand_items_eye_count",
        ),
        CheckConstraint(
            "composition_mode IS NULL OR composition_mode IN ('recipe')",
            name="ck_fair_stand_items_composition_mode",
        ),
        CheckConstraint(
            "NOT catalog_visible OR (category_id IS NOT NULL AND catalog_item_index IS NOT NULL AND preview_id IS NOT NULL)",
            name="ck_fair_stand_items_catalog_visible",
        ),
        Index("ix_fair_stand_items_item_type", "item_type"),
        Index("ix_fair_stand_items_category_id", "category_id"),
        Index("ix_fair_stand_items_preview_id", "preview_id"),
        Index("ix_fair_stand_items_is_active", "is_active"),
        Index(
            "uq_fair_stand_items_catalog_order",
            "category_id",
            "catalog_item_index",
            unique=True,
            postgresql_where=text("catalog_visible IS TRUE"),
            sqlite_where=text("catalog_visible IS TRUE"),
        ),
    )

    item_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    catalog_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("fair_stand_categories.id", **CASCADE),
        nullable=True,
    )
    catalog_item_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preview_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("fair_stand_catalog_preview_kinds.id", **CASCADE),
        nullable=True,
    )
    material: Mapped[str | None] = mapped_column(String(64), nullable=True)
    default_color: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preserve_model_scale: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    model_rotation_y_deg: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    visual_rotation_y_deg: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    composition_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    paintable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    shape: Mapped[str | None] = mapped_column(String(16), nullable=True)
    variant: Mapped[str | None] = mapped_column(String(64), nullable=True)
    eye_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    category: Mapped[FairStandCategoryModel | None] = relationship(back_populates="items")
    dimensions: Mapped["FairStandItemDimensionsModel | None"] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    scene_dimensions: Mapped["FairStandItemSceneDimensionsModel | None"] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    strip_occupancy: Mapped["FairStandItemStripOccupancyModel | None"] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    assets: Mapped[list["FairStandItemAssetModel"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    components: Mapped[list["FairStandItemComponentModel"]] = relationship(
        back_populates="parent",
        foreign_keys="FairStandItemComponentModel.parent_item_key",
        cascade="all, delete-orphan",
    )
    video_wall: Mapped["FairStandItemVideoWallModel | None"] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys="FairStandItemVideoWallModel.parent_item_key",
    )
    body_parts: Mapped[list["FairStandItemBodyPartModel"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys="FairStandItemBodyPartModel.parent_item_key",
    )


class FairStandItemDimensionsModel(Base):
    __tablename__ = "fair_stand_item_dimensions"
    __table_args__ = (
        CheckConstraint(
            "width_cm IS NOT NULL OR depth_cm IS NOT NULL OR height_cm IS NOT NULL "
            "OR length_cm IS NOT NULL OR thickness_cm IS NOT NULL "
            "OR mount_height_cm IS NOT NULL OR wall_gap_cm IS NOT NULL",
            name="ck_fair_stand_item_dimensions_present",
        ),
    )

    item_key: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("fair_stand_items.item_key", **CASCADE),
        primary_key=True,
    )
    width_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    depth_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    length_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    thickness_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    mount_height_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    wall_gap_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    item: Mapped[FairStandItemModel] = relationship(back_populates="dimensions")


class FairStandItemSceneDimensionsModel(Base):
    __tablename__ = "fair_stand_item_scene_dimensions"
    __table_args__ = (
        CheckConstraint(
            "width_cm IS NOT NULL OR depth_cm IS NOT NULL OR height_cm IS NOT NULL",
            name="ck_fair_stand_item_scene_dimensions_present",
        ),
    )

    item_key: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("fair_stand_items.item_key", **CASCADE),
        primary_key=True,
    )
    width_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    depth_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    item: Mapped[FairStandItemModel] = relationship(back_populates="scene_dimensions")


class FairStandItemStripOccupancyModel(Base):
    __tablename__ = "fair_stand_item_strip_occupancy"
    __table_args__ = (
        CheckConstraint("strip_count > 0", name="ck_fair_stand_item_strip_count"),
        CheckConstraint("align IN ('top')", name="ck_fair_stand_item_strip_align"),
    )

    item_key: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("fair_stand_items.item_key", **CASCADE),
        primary_key=True,
    )
    align: Mapped[str] = mapped_column(String(16), nullable=False)
    strip_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    item: Mapped[FairStandItemModel] = relationship(back_populates="strip_occupancy")


class FairStandItemAssetModel(Base):
    __tablename__ = "fair_stand_item_assets"
    __table_args__ = (
        UniqueConstraint("item_key", "asset_role", name="uq_fair_stand_item_assets_role"),
        CheckConstraint(
            "asset_role IN ('model', 'default_screen', 'catalog_image', 'thumbnail', 'texture')",
            name="ck_fair_stand_item_assets_role",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    item_key: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("fair_stand_items.item_key", **CASCADE),
        nullable=False,
        index=True,
    )
    asset_role: Mapped[str] = mapped_column(String(32), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    item: Mapped[FairStandItemModel] = relationship(back_populates="assets")


class FairStandItemComponentModel(Base):
    __tablename__ = "fair_stand_item_components"
    __table_args__ = (
        UniqueConstraint("parent_item_key", "sort_order", name="uq_fair_stand_item_components_sort"),
        CheckConstraint("quantity > 0", name="ck_fair_stand_item_components_quantity"),
        CheckConstraint("parent_item_key <> child_item_key", name="ck_fair_stand_item_components_self"),
        Index("ix_fair_stand_item_components_child", "child_item_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    parent_item_key: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("fair_stand_items.item_key", **CASCADE),
        nullable=False,
    )
    child_item_key: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("fair_stand_items.item_key", **CASCADE),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    parent: Mapped[FairStandItemModel] = relationship(
        back_populates="components",
        foreign_keys=[parent_item_key],
    )


class FairStandItemVideoWallModel(Base):
    __tablename__ = "fair_stand_item_video_walls"
    __table_args__ = (
        CheckConstraint("rows > 0", name="ck_fair_stand_video_wall_rows"),
        CheckConstraint("cols > 0", name="ck_fair_stand_video_wall_cols"),
    )

    parent_item_key: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("fair_stand_items.item_key", **CASCADE),
        primary_key=True,
    )
    rows: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    cols: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    panel_item_key: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("fair_stand_items.item_key", **CASCADE),
        nullable=False,
    )
    parent: Mapped[FairStandItemModel] = relationship(
        back_populates="video_wall",
        foreign_keys=[parent_item_key],
    )


class FairStandItemBodyPartModel(Base):
    __tablename__ = "fair_stand_item_body_parts"
    __table_args__ = (
        CheckConstraint(
            "body_role IN ('side', 'horizontal', 'glass_shelf')",
            name="ck_fair_stand_body_role",
        ),
    )

    parent_item_key: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("fair_stand_items.item_key", **CASCADE),
        primary_key=True,
    )
    body_role: Mapped[str] = mapped_column(String(32), primary_key=True)
    child_item_key: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("fair_stand_items.item_key", **CASCADE),
        nullable=False,
    )
    parent: Mapped[FairStandItemModel] = relationship(
        back_populates="body_parts",
        foreign_keys=[parent_item_key],
    )
