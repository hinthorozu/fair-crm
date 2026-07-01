"""Tests for shared pagination helpers."""

import pytest

from app.core.pagination import (
    compute_total_pages,
    normalize_page_params,
    normalize_sort_direction,
)


def test_normalize_page_params_defaults():
    params = normalize_page_params(0, 0)
    assert params.page == 1
    assert params.page_size == 1
    assert params.offset == 0


def test_normalize_page_params_caps_page_size():
    params = normalize_page_params(2, 500)
    assert params.page == 2
    assert params.page_size == 100
    assert params.offset == 100


def test_compute_total_pages():
    assert compute_total_pages(0, 25) == 0
    assert compute_total_pages(1, 25) == 1
    assert compute_total_pages(25, 25) == 1
    assert compute_total_pages(26, 25) == 2


def test_normalize_sort_direction():
    assert normalize_sort_direction("asc") == "asc"
    assert normalize_sort_direction("DESC") == "desc"
    assert normalize_sort_direction(None) == "desc"
