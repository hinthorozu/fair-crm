"""TÜYAP new exhibitor portal — Foodist Expo list scraping."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from typing import Any
from urllib.parse import urljoin

from app.modules.scraper.core.browser_service import BrowserService
from app.modules.scraper.core.scraper_run_logger import ScraperRunLogger, resolve_run_logger
from app.modules.scraper.domain.requested_output_fields import needs_detail_scrape, resolve_requested_fields_from_context
from app.modules.scraper.dto.raw_company_dto import RawCompanyDto
from app.modules.scraper.fetchers.foodist_http_fetcher import (
    discover_pagination_urls,
    extract_list_items,
    fetch_html,
)
from app.modules.scraper.parsers.foodist_detail_parser import FoodistDetailInfo, parse_foodist_detail_html
from app.modules.scraper.parsers.foodist_list_parser import FoodistListItem, parse_foodist_list_text
from app.modules.scraper.types.scraper_context import ScraperContext
from app.modules.scraper.types.scraper_site import ScraperSiteKey
from app.modules.scraper.validators.website_validator import validate_website_url

logger = logging.getLogger(__name__)

DETAIL_PROGRESS_INTERVAL = 50


def _log_missing_website(run_log: ScraperRunLogger, company_name: str) -> None:
    run_log.warning(
        "detail_scrape_progress",
        f"Website bulunamadı: {company_name}",
        metadata={"company_name": company_name},
    )

# Foodist Expo / TÜYAP New list page selectors.
BRAND_LIST_LINK_SELECTOR = 'a[href*="brand/"]'
PAGINATION_LINK_SELECTOR = ".pagination a, nav[aria-label*='pagination'] a, [class*='pagination'] a"

SELECTOR_CONSTANTS: dict[str, str] = {
    "BRAND_LIST_LINK_SELECTOR": BRAND_LIST_LINK_SELECTOR,
    "PAGINATION_LINK_SELECTOR": PAGINATION_LINK_SELECTOR,
}

SELECTOR_PROBE_GROUPS: dict[str, dict[str, Any]] = {
    "brand_list_links": {
        "constant": "BRAND_LIST_LINK_SELECTOR",
        "selectors": [
            BRAND_LIST_LINK_SELECTOR,
            "a[href*='/brand']",
            ".brand-list a",
            "[class*='brand'] a[href]",
        ],
        "sample_kind": "href",
        "sample_attr": "href",
    },
    "pagination_links": {
        "constant": "PAGINATION_LINK_SELECTOR",
        "selectors": [
            PAGINATION_LINK_SELECTOR,
            "a.page-link",
            ".pager a",
            "a:has-text('2')",
            "a:has-text('3')",
        ],
        "sample_kind": "text",
    },
}


class TuyapNewScrapeError(Exception):
    """Controlled scrape failure for the TÜYAP New adapter."""


class TuyapNewAdapter:
    """Scrapes exhibitor lists from the new TÜYAP / Foodist Expo website."""

    def __init__(self, browser: BrowserService | None = None) -> None:
        self._browser = browser

    @property
    def site_key(self) -> str:
        return ScraperSiteKey.TUYAP_NEW

    @property
    def display_name(self) -> str:
        return "TÜYAP (New)"

    def scrape(self, context: ScraperContext) -> list[RawCompanyDto]:
        return asyncio.run(self.scrape_async(context))

    async def scrape_async(self, context: ScraperContext) -> list[RawCompanyDto]:
        url = context.url
        if not url:
            logger.info("TuyapNewAdapter fallback: url missing")
            return self._placeholder_data(context)

        use_http = self._resolve_use_http(context)
        if not use_http and self._browser is None:
            logger.info("TuyapNewAdapter fallback: browser missing and HTTP mode disabled")
            return self._placeholder_data(context)

        try:
            if use_http:
                rows = await asyncio.to_thread(self._scrape_all_pages_http, context, url)
            else:
                rows = await self._scrape_all_pages(context, url)
        except TuyapNewScrapeError:
            raise
        except Exception as exc:
            if not use_http and self._is_playwright_network_error(exc):
                logger.warning(
                    "TuyapNewAdapter Playwright network error for url=%r; retrying with HTTP fetch: %s",
                    url,
                    exc,
                )
                try:
                    rows = await asyncio.to_thread(self._scrape_all_pages_http, context, url)
                except Exception as http_exc:
                    logger.exception("TuyapNewAdapter HTTP fallback failed for url=%r", url)
                    raise TuyapNewScrapeError(
                        f"Failed to scrape TÜYAP New exhibitor list (HTTP fallback): {url}"
                    ) from http_exc
            else:
                logger.exception("TuyapNewAdapter scrape failed for url=%r", url)
                raise TuyapNewScrapeError(f"Failed to scrape TÜYAP New exhibitor list: {url}") from exc

        if not rows:
            logger.warning("TuyapNewAdapter found no brand list items for url=%r; using placeholder data", url)
            return self._placeholder_data(context)
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
            raw_items = extract_list_items(html, base_url=start_url)
            page_rows = self._list_items_to_dtos(
                raw_items,
                list_url=page_url,
                context=context,
                seen_detail_urls=seen_detail_urls,
            )
            rows.extend(page_rows)
            pages_scraped += 1

            for next_url in discover_pagination_urls(html, base_url=start_url):
                if next_url not in visited_urls and next_url not in pending_urls:
                    pending_urls.append(next_url)

        logger.info(
            "TuyapNewAdapter HTTP scraped %d list page(s) (max_pages=%s) starting from %r",
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
                detail = parse_foodist_detail_html(html)
                merged = self._merge_detail_into_dto(row, detail)
                if not str(merged.website or "").strip():
                    _log_missing_website(run_log, merged.company_name)
                enriched.append(merged)
            except Exception as exc:
                logger.warning(
                    "TuyapNewAdapter HTTP detail scrape failed for %r; keeping list data: %s",
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

    @staticmethod
    def _resolve_use_http(context: ScraperContext) -> bool:
        return bool(context.options.get("use_http", False))

    @staticmethod
    def _is_playwright_network_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "err_network_access_denied" in message or "net::err_" in message

    def inspect_selectors(self, context: ScraperContext) -> dict[str, Any]:
        """Probe candidate selectors on the target page for DOM discovery."""
        url = context.url
        if not url:
            raise TuyapNewScrapeError("ScraperContext.url is required for selector inspection")
        if self._browser is None:
            raise TuyapNewScrapeError("BrowserService is required for selector inspection")

        return asyncio.run(self._inspect_selectors_on_page(url))

    async def _inspect_selectors_on_page(self, url: str) -> dict[str, Any]:
        if self._browser is None:
            raise TuyapNewScrapeError("BrowserService is not configured")
        if not self._browser.is_launched:
            raise TuyapNewScrapeError("BrowserService.launch() must be called before selector inspection")

        await self._browser.new_page()
        await self._browser.goto(url)

        groups: dict[str, Any] = {}
        recommended_constants: dict[str, str] = {}

        for group_name, group in SELECTOR_PROBE_GROUPS.items():
            group_result = await self._probe_selector_group(group)
            groups[group_name] = group_result

            constant_name = group.get("constant")
            recommended = group_result.get("recommended")
            if constant_name and recommended:
                recommended_constants[constant_name] = recommended

        return {
            "url": url,
            "groups": groups,
            "recommended_constants": recommended_constants,
            "active_constants": dict(SELECTOR_CONSTANTS),
            "constant_updates": self._constant_updates(recommended_constants),
        }

    async def _probe_selector_group(self, group: dict[str, Any]) -> dict[str, Any]:
        if self._browser is None:
            raise TuyapNewScrapeError("BrowserService is not configured")

        selectors = group["selectors"]
        sample_kind = group.get("sample_kind", "text")
        sample_attr = group.get("sample_attr", "href")
        sample_limit = 5

        selector_results: dict[str, dict[str, Any]] = {}
        recommended: str | None = None

        for selector in selectors:
            count = await self._browser.query_count(selector)
            if sample_kind == "href":
                samples = await self._browser.attrs(selector, sample_attr, limit=sample_limit)
            else:
                samples = await self._browser.texts(selector, limit=sample_limit)

            selector_results[selector] = {
                "count": count,
                "samples": samples[:sample_limit],
            }
            if recommended is None and count > 0:
                recommended = selector

        return {
            "selectors": selector_results,
            "recommended": recommended,
        }

    @staticmethod
    def _constant_updates(recommended_constants: dict[str, str]) -> dict[str, dict[str, str]]:
        updates: dict[str, dict[str, str]] = {}
        for constant_name, recommended in recommended_constants.items():
            current = SELECTOR_CONSTANTS.get(constant_name)
            if current != recommended:
                updates[constant_name] = {
                    "current": current or "",
                    "recommended": recommended,
                }
        return updates

    async def _scrape_all_pages(self, context: ScraperContext, start_url: str) -> list[RawCompanyDto]:
        if self._browser is None:
            raise TuyapNewScrapeError("BrowserService is not configured")

        if not self._browser.is_launched:
            raise TuyapNewScrapeError("BrowserService.launch() must be called before scraping")

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
            page_rows = await self._scrape_current_list_page(
                context,
                list_url=page_url,
                seen_detail_urls=seen_detail_urls,
            )
            rows.extend(page_rows)
            pages_scraped += 1

            pagination_hrefs = await self._browser.attrs(PAGINATION_LINK_SELECTOR, "href", limit=200)
            for next_url in self._normalize_pagination_urls(pagination_hrefs, base_url=start_url):
                if next_url not in visited_urls and next_url not in pending_urls:
                    pending_urls.append(next_url)

        logger.info(
            "TuyapNewAdapter scraped %d list page(s) (max_pages=%s) starting from %r",
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
            rows = await self._enrich_with_detail_pages(rows, run_log)

        return rows

    async def _enrich_with_detail_pages(
        self,
        rows: list[RawCompanyDto],
        run_log: ScraperRunLogger,
    ) -> list[RawCompanyDto]:
        if self._browser is None:
            raise TuyapNewScrapeError("BrowserService is not configured")

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
                run_log.info(
                    "browser/open_url",
                    f"Sayfa açılıyor: {detail_url}",
                    metadata={"url": detail_url, "via": "browser", "phase": "detail"},
                )
                await self._browser.goto(detail_url)
                html = await self._browser.html()
                detail = parse_foodist_detail_html(html)
                merged = self._merge_detail_into_dto(row, detail)
                if not str(merged.website or "").strip():
                    _log_missing_website(run_log, merged.company_name)
                enriched.append(merged)
            except Exception as exc:
                logger.warning(
                    "TuyapNewAdapter detail scrape failed for %r; keeping list data: %s",
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

    @staticmethod
    def _resolve_scrape_detail(context: ScraperContext) -> bool:
        if "scrape_detail" in context.options:
            return bool(context.options.get("scrape_detail"))
        if "requested_fields" in context.options:
            return needs_detail_scrape(resolve_requested_fields_from_context(context))
        return True

    @staticmethod
    def _merge_detail_into_dto(row: RawCompanyDto, detail: FoodistDetailInfo) -> RawCompanyDto:
        extra_fields = dict(row.extra_fields)
        if detail.category and "category" not in extra_fields:
            extra_fields["category"] = detail.category
        if detail.description and "description" not in extra_fields:
            extra_fields["description"] = detail.description
        if detail.websites:
            extra_fields.setdefault("websites", ", ".join(detail.websites))
        for field_name in (
            "instagram_url",
            "linkedin_url",
            "facebook_url",
            "youtube_url",
            "x_url",
        ):
            value = getattr(detail, field_name, None)
            if value and field_name not in extra_fields:
                extra_fields[field_name] = value

        website = row.website or detail.website
        website_valid = validate_website_url(website) if website else False

        metadata = dict(row.metadata)
        metadata["detail_scraped"] = True
        metadata["website_valid"] = website_valid

        return replace(
            row,
            website=website,
            phone=row.phone or detail.phone,
            email=row.email or detail.email,
            address=row.address or detail.address,
            country=row.country or detail.country,
            hall=row.hall or detail.hall,
            stand=row.stand or detail.stand,
            notes=row.notes or detail.description,
            extra_fields=extra_fields,
            metadata=metadata,
        )

    async def _scrape_current_list_page(
        self,
        context: ScraperContext,
        *,
        list_url: str,
        seen_detail_urls: set[str],
    ) -> list[RawCompanyDto]:
        if self._browser is None:
            raise TuyapNewScrapeError("BrowserService is not configured")

        if not await self._browser.exists(BRAND_LIST_LINK_SELECTOR):
            logger.warning("TuyapNewAdapter found no brand links on list page %r", list_url)
            return []

        raw_items = await self._browser.evaluate(self._build_extract_script())
        if not isinstance(raw_items, list):
            raise TuyapNewScrapeError("Brand list extraction script returned unexpected payload")

        return self._list_items_to_dtos(
            raw_items,
            list_url=list_url,
            context=context,
            seen_detail_urls=seen_detail_urls,
        )

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
    def _normalize_pagination_urls(hrefs: list[str], *, base_url: str) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for href in hrefs:
            page_url = TuyapNewAdapter._normalize_page_url(href, base_url=base_url)
            if page_url is None or page_url in seen:
                continue
            seen.add(page_url)
            normalized.append(page_url)
        return normalized

    @staticmethod
    def _normalize_page_url(href: str, *, base_url: str) -> str | None:
        cleaned = str(href).strip()
        if not cleaned or cleaned.startswith("#") or cleaned.lower().startswith("javascript:"):
            return None
        return urljoin(base_url, cleaned)

    @staticmethod
    def _build_page_urls(start_url: str, pagination_urls: list[str], *, max_pages: int | None) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()

        for page_url in [start_url, *pagination_urls]:
            if page_url in seen:
                continue
            seen.add(page_url)
            ordered.append(page_url)
            if max_pages is not None and len(ordered) >= max_pages:
                break

        return ordered

    def _build_extract_script(self) -> str:
        return f"""
        () => {{
            const links = Array.from(document.querySelectorAll({BRAND_LIST_LINK_SELECTOR!r}));
            const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
            const extractListText = (link) => {{
                const container = link.querySelector(".brand-container") || link;
                const infoEl = container.querySelector(".brand-info");
                const locationEl = container.querySelector(".brand-location-info");
                const parts = [infoEl, locationEl]
                    .filter(Boolean)
                    .map((el) => normalize(el.textContent));
                if (parts.length > 0) {{
                    return parts.join(" ");
                }}
                const fallbackContainer = link.closest("li, article, .list-group-item, [class*='brand'], [class*='exhibitor']")
                    || link.parentElement
                    || link;
                return normalize(fallbackContainer.textContent || link.textContent || "");
            }};
            return links.map((link) => {{
                const href = link.href || "";
                return {{
                    detail_url: href,
                    list_text: extractListText(link),
                }};
            }}).filter((row) => row.detail_url.includes("brand/") && row.list_text);
        }}
        """

    def _list_items_to_dtos(
        self,
        items: list[dict[str, Any]],
        *,
        list_url: str,
        context: ScraperContext,
        seen_detail_urls: set[str] | None = None,
    ) -> list[RawCompanyDto]:
        rows: list[RawCompanyDto] = []
        seen = seen_detail_urls if seen_detail_urls is not None else set()

        for item in items:
            detail_url = self._normalize_detail_url(item.get("detail_url"), base_url=list_url)
            if not detail_url or "brand/" not in detail_url:
                continue
            if detail_url in seen:
                continue
            seen.add(detail_url)

            parsed = parse_foodist_list_text(item.get("list_text") or "", detail_url=detail_url)
            if parsed is None:
                logger.warning("TuyapNewAdapter skipped unparsable list item: %r", item.get("list_text"))
                continue

            rows.append(self._parsed_item_to_dto(parsed, list_url=list_url, context=context))

        return rows

    def _parsed_item_to_dto(
        self,
        item: FoodistListItem,
        *,
        list_url: str,
        context: ScraperContext,
    ) -> RawCompanyDto:
        extra_fields: dict[str, str] = {}
        if item.brands:
            extra_fields["brands"] = item.brands

        return RawCompanyDto(
            company_name=item.company_name,
            country=item.country,
            hall=item.hall,
            stand=item.stand,
            source_url=item.detail_url,
            extra_fields=extra_fields,
            metadata={
                "adapter": self.site_key,
                "placeholder": False,
                "detail_url": item.detail_url,
                "list_url": list_url,
                "raw_list_text": item.raw_text,
                "fair_id": str(context.fair_id) if context.fair_id else None,
            },
        )

    @staticmethod
    def _normalize_detail_url(detail_url: Any, *, base_url: str) -> str | None:
        if detail_url is None:
            return None
        href = str(detail_url).strip()
        if not href:
            return None
        return urljoin(base_url, href)

    def _placeholder_data(self, context: ScraperContext) -> list[RawCompanyDto]:
        return [
            RawCompanyDto(
                company_name="TÜYAP New Placeholder Exhibitor A",
                hall="5",
                stand="A10",
                source_url=context.url,
                metadata={"adapter": self.site_key, "placeholder": True},
            ),
            RawCompanyDto(
                company_name="TÜYAP New Placeholder Exhibitor B",
                hall="6",
                stand="B22",
                website="https://tuyap-new-placeholder.test",
                source_url=context.url,
                metadata={"adapter": self.site_key, "placeholder": True},
            ),
        ]
