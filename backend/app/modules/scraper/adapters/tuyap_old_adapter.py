"""TÜYAP legacy exhibitor portal — İstanbul Kitap Fuarı list scraping."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace

from app.modules.scraper.core.browser_service import BrowserService
from app.modules.scraper.core.scraper_run_logger import ScraperRunLogger, resolve_run_logger
from app.modules.scraper.domain.requested_output_fields import resolve_requested_fields_from_context
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.fetchers.tuyap_old_http_fetcher import (
    discover_pagination_urls,
    fetch_html,
    normalize_page_url,
)
from app.modules.scraper.parsers.tuyap_old_detail_parser import TuyapOldDetailInfo, parse_tuyap_old_detail_html
from app.modules.scraper.parsers.tuyap_old_list_parser import TuyapOldListItem, parse_tuyap_old_list_html
from app.modules.scraper.services.scraper_run_cancellation import ensure_run_not_cancelled
from app.modules.scraper.types.scraper_context import ScraperContext
from app.modules.scraper.types.scraper_site import ScraperSiteKey
from app.modules.scraper.validators.website_validator import validate_website_url

logger = logging.getLogger(__name__)

DETAIL_PROGRESS_INTERVAL = 50
LIST_TABLE_SELECTOR = "table.filter-table"
PAGINATION_SELECTOR = ".pagination-wrapper a[href*='page=']"

# Fields available on the list page for istanbulkitapfuari.com.
TUYAP_OLD_LIST_REQUESTED_FIELDS: frozenset[str] = frozenset(
    {"customerName", "phone", "address", "website", "hall", "stand"}
)


class TuyapOldScrapeError(Exception):
    """Controlled scrape failure for the TÜYAP Old adapter."""


class TuyapOldAdapter:
    """Scrapes exhibitor lists from the legacy TÜYAP / İstanbul Kitap Fuarı website."""

    def __init__(self, browser: BrowserService | None = None) -> None:
        self._browser = browser

    @property
    def site_key(self) -> str:
        return ScraperSiteKey.TUYAP_OLD

    @property
    def display_name(self) -> str:
        return "TÜYAP (Old)"

    def scrape(self, context: ScraperContext) -> list[RawCompanyDto]:
        return asyncio.run(self.scrape_async(context))

    async def scrape_async(self, context: ScraperContext) -> list[RawCompanyDto]:
        url = context.url
        if not url:
            logger.info("TuyapOldAdapter fallback: url missing")
            return []

        use_http = self._resolve_use_http(context)
        if not use_http and self._browser is None:
            logger.info("TuyapOldAdapter fallback: browser missing and HTTP mode disabled")
            return []

        try:
            if use_http:
                rows = await asyncio.to_thread(self._scrape_all_pages_http, context, url)
            else:
                rows = await self._scrape_all_pages(context, url)
        except TuyapOldScrapeError:
            raise
        except Exception as exc:
            if not use_http and self._is_playwright_network_error(exc):
                logger.warning(
                    "TuyapOldAdapter Playwright network error for url=%r; retrying with HTTP fetch: %s",
                    url,
                    exc,
                )
                try:
                    rows = await asyncio.to_thread(self._scrape_all_pages_http, context, url)
                except Exception as http_exc:
                    logger.exception("TuyapOldAdapter HTTP fallback failed for url=%r", url)
                    raise TuyapOldScrapeError(
                        f"Failed to scrape TÜYAP Old exhibitor list (HTTP fallback): {url}"
                    ) from http_exc
            else:
                logger.exception("TuyapOldAdapter scrape failed for url=%r", url)
                raise TuyapOldScrapeError(f"Failed to scrape TÜYAP Old exhibitor list: {url}") from exc

        if not rows:
            logger.warning("TuyapOldAdapter found no exhibitor list items for url=%r", url)
        return rows

    def _scrape_all_pages_http(self, context: ScraperContext, start_url: str) -> list[RawCompanyDto]:
        run_log = resolve_run_logger(context)
        run_log.info("list_scrape_started", "Katılımcı listesi okunuyor", metadata={"url": start_url, "via": "http"})

        max_pages = self._resolve_max_pages(context)
        visited_urls: set[str] = set()
        pending_urls: list[str] = [start_url]
        rows: list[RawCompanyDto] = []
        seen_detail_urls: set[str] = set()
        pages_scraped = 0

        while pending_urls:
            ensure_run_not_cancelled(context)
            page_url = pending_urls.pop(0)
            if page_url in visited_urls:
                continue
            visited_urls.add(page_url)

            if max_pages is not None and pages_scraped >= max_pages:
                break

            run_log.info(
                "browser/open_url",
                f"HTTP isteği gönderiliyor: {page_url}",
                metadata={"url": page_url, "via": "http"},
            )
            html = fetch_html(page_url)
            page_rows = self._list_items_to_dtos(
                parse_tuyap_old_list_html(html, base_url=start_url),
                list_url=page_url,
                seen_detail_urls=seen_detail_urls,
            )
            rows.extend(page_rows)
            pages_scraped += 1

            for next_url in discover_pagination_urls(html, base_url=start_url):
                if next_url not in visited_urls and next_url not in pending_urls:
                    pending_urls.append(next_url)

        logger.info(
            "TuyapOldAdapter HTTP scraped %d list page(s) (max_pages=%s) starting from %r",
            pages_scraped,
            max_pages if max_pages is not None else "unlimited",
            start_url,
        )
        run_log.info(
            "pagination_found",
            self._pagination_summary_message(pages_scraped, max_pages),
            metadata=self._pagination_summary_metadata(pages_scraped, max_pages, via="http"),
        )

        if self._resolve_scrape_detail(context):
            rows = self._enrich_with_detail_pages_http(rows, run_log)

        return rows

    async def _scrape_all_pages(self, context: ScraperContext, start_url: str) -> list[RawCompanyDto]:
        if self._browser is None:
            raise TuyapOldScrapeError("BrowserService is not configured")
        if not self._browser.is_launched:
            raise TuyapOldScrapeError("BrowserService.launch() must be called before scraping")

        run_log = resolve_run_logger(context)
        run_log.info("list_scrape_started", "Katılımcı listesi okunuyor", metadata={"url": start_url, "via": "browser"})

        max_pages = self._resolve_max_pages(context)
        await self._browser.new_page()

        visited_urls: set[str] = set()
        pending_urls: list[str] = [start_url]
        rows: list[RawCompanyDto] = []
        seen_detail_urls: set[str] = set()
        pages_scraped = 0

        while pending_urls:
            ensure_run_not_cancelled(context)
            page_url = pending_urls.pop(0)
            if page_url in visited_urls:
                continue
            visited_urls.add(page_url)

            if max_pages is not None and pages_scraped >= max_pages:
                break

            run_log.info(
                "browser/open_url",
                f"Sayfa açılıyor: {page_url}",
                metadata={"url": page_url, "via": "browser"},
            )
            await self._browser.goto(page_url)
            await self._browser.wait_for(LIST_TABLE_SELECTOR)
            html = await self._browser.html()
            page_rows = self._list_items_to_dtos(
                parse_tuyap_old_list_html(html, base_url=start_url),
                list_url=page_url,
                seen_detail_urls=seen_detail_urls,
            )
            rows.extend(page_rows)
            pages_scraped += 1

            pagination_hrefs = await self._browser.attrs(PAGINATION_SELECTOR, "href", limit=200)
            for next_url in self._normalize_pagination_urls(pagination_hrefs, base_url=start_url):
                if next_url not in visited_urls and next_url not in pending_urls:
                    pending_urls.append(next_url)

        logger.info(
            "TuyapOldAdapter scraped %d list page(s) (max_pages=%s) starting from %r",
            pages_scraped,
            max_pages if max_pages is not None else "unlimited",
            start_url,
        )
        run_log.info(
            "pagination_found",
            self._pagination_summary_message(pages_scraped, max_pages),
            metadata=self._pagination_summary_metadata(pages_scraped, max_pages, via="browser"),
        )

        if self._resolve_scrape_detail(context):
            rows = await self._enrich_with_detail_pages(context, rows, run_log)

        return rows

    def _enrich_with_detail_pages_http(self, rows: list[RawCompanyDto], run_log: ScraperRunLogger) -> list[RawCompanyDto]:
        total = len(rows)
        run_log.info(
            "detail_scrape_started",
            f"{total} detay sayfası geziliyor",
            metadata={"detail_count": total, "via": "http"},
        )
        enriched: list[RawCompanyDto] = []
        for index, row in enumerate(rows, start=1):
            detail_url = row.source_url
            if not detail_url:
                enriched.append(row)
                continue
            try:
                html = fetch_html(detail_url)
                detail = parse_tuyap_old_detail_html(html)
                enriched.append(self._merge_detail_into_dto(row, detail))
            except Exception as exc:
                logger.warning(
                    "TuyapOldAdapter HTTP detail scrape failed for %r; keeping list data: %s",
                    detail_url,
                    exc,
                )
                run_log.error(
                    "detail_scrape_progress",
                    f"Detail page okunamadı: {detail_url}",
                    metadata={"url": detail_url, "company_name": row.company_name, "error": str(exc)},
                )
                enriched.append(row)

            if index % DETAIL_PROGRESS_INTERVAL == 0 or index == total:
                run_log.info(
                    "detail_scrape_progress",
                    f"{index}/{total} detay sayfası işlendi",
                    metadata={"current": index, "total": total, "via": "http"},
                )
        return enriched

    async def _enrich_with_detail_pages(
        self,
        context: ScraperContext,
        rows: list[RawCompanyDto],
        run_log: ScraperRunLogger,
    ) -> list[RawCompanyDto]:
        if self._browser is None:
            raise TuyapOldScrapeError("BrowserService is not configured")

        total = len(rows)
        run_log.info(
            "detail_scrape_started",
            f"{total} detay sayfası geziliyor",
            metadata={"detail_count": total, "via": "browser"},
        )
        enriched: list[RawCompanyDto] = []
        for index, row in enumerate(rows, start=1):
            detail_url = row.source_url
            if not detail_url:
                enriched.append(row)
                continue
            try:
                await self._browser.goto(detail_url)
                html = await self._browser.html()
                detail = parse_tuyap_old_detail_html(html)
                enriched.append(self._merge_detail_into_dto(row, detail))
            except Exception as exc:
                logger.warning(
                    "TuyapOldAdapter detail scrape failed for %r; keeping list data: %s",
                    detail_url,
                    exc,
                )
                run_log.error(
                    "detail_scrape_progress",
                    f"Detail page okunamadı: {detail_url}",
                    metadata={"url": detail_url, "company_name": row.company_name, "error": str(exc)},
                )
                enriched.append(row)

            if index % DETAIL_PROGRESS_INTERVAL == 0 or index == total:
                run_log.info(
                    "detail_scrape_progress",
                    f"{index}/{total} detay sayfası işlendi",
                    metadata={"current": index, "total": total, "via": "browser"},
                )
        return enriched

    def _list_items_to_dtos(
        self,
        items: list[TuyapOldListItem],
        *,
        list_url: str,
        seen_detail_urls: set[str],
    ) -> list[RawCompanyDto]:
        rows: list[RawCompanyDto] = []
        for item in items:
            detail_url = item.detail_url
            if detail_url:
                if detail_url in seen_detail_urls:
                    continue
                seen_detail_urls.add(detail_url)
            rows.append(self._list_item_to_dto(item, list_url=list_url))
        return rows

    @staticmethod
    def _list_item_to_dto(item: TuyapOldListItem, *, list_url: str) -> RawCompanyDto:
        extra_fields: dict[str, str] = {}
        notes = None
        if item.product_groups:
            product_groups = ", ".join(item.product_groups)
            extra_fields["product_groups"] = product_groups
            notes = product_groups

        website = item.website
        website_valid = validate_website_url(website) if website else False

        return RawCompanyDto(
            company_name=item.company_name,
            source_url=item.detail_url,
            hall=item.hall,
            stand=item.stand,
            email=item.email,
            phone=item.phone,
            website=website,
            address=item.address,
            notes=notes,
            extra_fields=extra_fields,
            metadata={
                "adapter": ScraperSiteKey.TUYAP_OLD,
                "list_url": list_url,
                "detail_url": item.detail_url,
                "website_valid": website_valid,
                "placeholder": False,
            },
        )

    @staticmethod
    def _merge_detail_into_dto(row: RawCompanyDto, detail: TuyapOldDetailInfo) -> RawCompanyDto:
        extra_fields = dict(row.extra_fields)
        if detail.product_groups:
            groups = ", ".join(detail.product_groups)
            extra_fields.setdefault("product_groups", groups)

        notes_parts: list[str] = []
        if row.notes:
            notes_parts.append(row.notes)
        if detail.about:
            notes_parts.append(detail.about)
        notes = "\n\n".join(notes_parts) if notes_parts else None

        for field_name in (
            "instagram_url",
            "linkedin_url",
            "facebook_url",
            "youtube_url",
        ):
            value = getattr(detail, field_name, None)
            if value and field_name not in extra_fields:
                extra_fields[field_name] = value

        metadata = dict(row.metadata)
        metadata["detail_scraped"] = True

        return replace(
            row,
            email=row.email or detail.email,
            notes=notes,
            extra_fields=extra_fields,
            metadata=metadata,
        )

    @staticmethod
    def _resolve_use_http(context: ScraperContext) -> bool:
        return bool(context.options.get("use_http", False))

    @staticmethod
    def _resolve_scrape_detail(context: ScraperContext) -> bool:
        if "scrape_detail" in context.options:
            return bool(context.options.get("scrape_detail"))

        requested = set(resolve_requested_fields_from_context(context))
        if "notes" in requested:
            return True

        detail_only = requested - TUYAP_OLD_LIST_REQUESTED_FIELDS
        return bool(detail_only)

    @staticmethod
    def _is_playwright_network_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "err_network_access_denied" in message or "net::err_" in message

    @staticmethod
    def _resolve_max_pages(context: ScraperContext) -> int | None:
        if "max_pages" not in context.options:
            return None
        raw = context.options.get("max_pages")
        if raw is None:
            return None
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        return max(1, value)

    @staticmethod
    def _pagination_summary_message(pages_scraped: int, max_pages: int | None) -> str:
        if max_pages is not None:
            return f"{pages_scraped}/{max_pages} liste sayfası tarandı (max_pages={max_pages})"
        return f"{pages_scraped} liste sayfası tarandı"

    @staticmethod
    def _pagination_summary_metadata(
        pages_scraped: int,
        max_pages: int | None,
        *,
        via: str,
    ) -> dict[str, object]:
        metadata: dict[str, object] = {"page_count": pages_scraped, "via": via}
        if max_pages is not None:
            metadata["max_pages"] = max_pages
        return metadata

    @staticmethod
    def _normalize_pagination_urls(hrefs: list[str], *, base_url: str) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for href in hrefs:
            page_url = normalize_page_url(href, base_url=base_url)
            if page_url is None or page_url in seen:
                continue
            seen.add(page_url)
            normalized.append(page_url)
        return normalized
