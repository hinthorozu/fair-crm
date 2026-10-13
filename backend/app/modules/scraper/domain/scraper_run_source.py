"""Scraper run origin — fair automation vs manual test."""

from enum import StrEnum


class ScraperRunSource(StrEnum):
    FAIR_AUTOMATION = "fair_automation"
    MANUAL_TEST = "manual_test"
    ENRICHMENT = "enrichment"
    TOBB_MANUAL = "tobb_manual"
    TOBB_WEEKLY = "tobb_weekly"
