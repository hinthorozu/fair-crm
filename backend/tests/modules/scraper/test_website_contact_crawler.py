from pathlib import Path

from app.modules.scraper.crawlers.website_contact_crawler import crawl_customer_website

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
