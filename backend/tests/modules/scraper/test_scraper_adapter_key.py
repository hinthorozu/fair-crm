"""Tests for adapter key slug generation."""

import pytest

from app.modules.scraper.domain.scraper_adapter import (
    allocate_adapter_key,
    slugify_adapter_key,
)
from app.modules.scraper.domain.scraper_adapter_exceptions import InvalidAdapterNameError


def test_slugify_adapter_key_from_turkish_name() -> None:
    assert slugify_adapter_key("Tüyap Ambalaj 2026") == "tuyap_ambalaj_2026"


def test_slugify_adapter_key_collapses_separators() -> None:
    assert slugify_adapter_key("  Demo   Adapter  ") == "demo_adapter"


def test_slugify_adapter_key_rejects_empty_result() -> None:
    with pytest.raises(InvalidAdapterNameError):
        slugify_adapter_key("***")


def test_allocate_adapter_key_adds_suffix_for_conflicts() -> None:
    reserved = {"demo_adapter", "demo_adapter_2"}
    assert allocate_adapter_key("demo_adapter", reserved) == "demo_adapter_3"
