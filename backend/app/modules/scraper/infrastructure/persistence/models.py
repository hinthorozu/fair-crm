"""SQLAlchemy models for scraper run history."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

JsonType = JSON().with_variant(SQLiteJSON(), "sqlite")


class ScraperRunHistoryModel(Base):
    __tablename__ = "scraper_run_history"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    adapter_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True, index=True)
    fair_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("crm_fairs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    input_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    fair_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fair_year: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    website_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    email_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    phone_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    instagram_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    linkedin_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    facebook_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    youtube_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    x_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    output_json_path: Mapped[str | None] = mapped_column(Text(), nullable=True)
    output_excel_path: Mapped[str | None] = mapped_column(Text(), nullable=True)

    logs: Mapped[list["ScraperRunLogModel"]] = relationship(
        "ScraperRunLogModel",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class ScraperRunLogModel(Base):
    __tablename__ = "scraper_run_log"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("scraper_run_history.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text(), nullable=True)

    run: Mapped[ScraperRunHistoryModel] = relationship("ScraperRunHistoryModel", back_populates="logs")


class ScraperAdapterModel(Base):
    __tablename__ = "scraper_adapters"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    adapter_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="experimental")
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    manifest: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, index=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
