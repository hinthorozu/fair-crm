"""Scraper run origin — fair automation vs manual test."""

from enum import StrEnum


class ScraperRunSource(StrEnum):
    FAIR_AUTOMATION = "fair_automation"
    MANUAL_TEST = "manual_test"
