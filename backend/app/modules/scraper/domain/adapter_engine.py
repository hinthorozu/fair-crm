"""Adapter Engine domain types."""

from __future__ import annotations

from enum import StrEnum


class AdapterEngineType(StrEnum):
    """Technical scraping engine implementation category."""

    STATIC = "static"
    DYNAMIC = "dynamic"
