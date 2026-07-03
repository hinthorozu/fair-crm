"""Exhibitor Scraper module — architecture for fair-site exhibitor list extraction.

Product layout reference: ``src/modules/scraper/`` (adapters, core, dto, …).
Backend path: ``app.modules.scraper``.

Site-specific adapters (TÜYAP, IFM, Hannover, Canton, …) plug into
``ScraperManager`` via ``IScraperAdapter``. Output is normalized for the
source-agnostic Import Engine (ADR-017).
"""

from app.modules.scraper.core.interfaces import IScraperAdapter
from app.modules.scraper.core.scraper_manager import ScraperManager
from app.modules.scraper.dto.normalized_company_dto import NormalizedCompanyDto
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.jobs.scraper_job import ScraperJob, ScraperJobStatus
from app.modules.scraper.normalizers.company_normalizer import CompanyNormalizer
from app.modules.scraper.types.scraper_result import ScraperResult

__all__ = [
    "CompanyNormalizer",
    "IScraperAdapter",
    "NormalizedCompanyDto",
    "RawCompanyDto",
    "ScraperJob",
    "ScraperJobStatus",
    "ScraperManager",
    "ScraperResult",
]
