from pathlib import Path

from app.modules.scraper.crawlers.website_contact_crawler import (
    crawl_customer_website,
    detect_client_side_redirect,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "customer_enrichment"


def _fixture_fetcher(url: str) -> str:
    mapping = {
        "https://ornek.com": "home_page.html",
        "https://ornek.com/iletisim": "contact_page.html",
        "https://ornek.com/kurumsal/hakkimizda": "contact_page.html",
    }
    file_name = mapping.get(url.rstrip("/"))
    if file_name is None:
        raise ValueError(f"Unexpected URL: {url}")
    return (FIXTURES / file_name).read_text(encoding="utf-8")


def test_crawl_customer_website_discovers_contact_pages():
    pages = crawl_customer_website(
        "ornek.com",
        max_pages=5,
        fetcher=_fixture_fetcher,
    )

    urls = [url.rstrip("/") for url, _ in pages]
    assert "https://ornek.com" in urls
    assert "https://ornek.com/iletisim" in urls
    assert len(pages) <= 5


def _js_redirect_fetcher(url: str) -> str:
    mapping = {
        "https://ornektarim.com.tr": "js_redirect_home.html",
        "https://ornektarim.com.tr/tr": "js_redirect_target.html",
        "https://ornektarim.com.tr/tr/": "js_redirect_target.html",
    }
    file_name = mapping.get(url.rstrip("/"))
    if file_name is None:
        raise ValueError(f"Unexpected URL: {url}")
    return (FIXTURES / file_name).read_text(encoding="utf-8")


def test_detect_client_side_redirect_follows_window_location_on_stub_page():
    html = (FIXTURES / "js_redirect_home.html").read_text(encoding="utf-8")
    target = detect_client_side_redirect(html, "https://ornektarim.com.tr")
    assert target == "https://ornektarim.com.tr/tr/"


def test_detect_client_side_redirect_follows_meta_refresh():
    html = (FIXTURES / "meta_refresh_home.html").read_text(encoding="utf-8")
    target = detect_client_side_redirect(html, "https://ornek.com")
    assert target == "https://ornek.com/en/"


def test_detect_client_side_redirect_ignores_window_location_on_content_rich_page():
    html = (FIXTURES / "home_page.html").read_text(encoding="utf-8")
    assert detect_client_side_redirect(html, "https://ornek.com") is None


def test_crawl_customer_website_follows_js_redirect_stub_homepage():
    """Agroder-style regression: homepage is a bare `window.location` shell."""
    pages = crawl_customer_website(
        "ornektarim.com.tr",
        max_pages=5,
        fetcher=_js_redirect_fetcher,
    )

    urls = [url.rstrip("/") for url, _ in pages]
    htmls = "".join(html for _, html in pages)
    assert "https://ornektarim.com.tr/tr" in urls
    assert "ornektarim@ornektarim.com.tr" in htmls
