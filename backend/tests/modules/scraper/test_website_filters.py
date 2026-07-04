"""Tests for website URL filtering."""

from app.modules.scraper.parsers.website_filters import (
    classify_social_url,
    extract_social_urls,
    is_company_website,
    pick_first_company_website,
)


def test_is_company_website_rejects_font_and_fair_domains():
    assert is_company_website("https://fonts.googleapis.com") is False
    assert is_company_website("https://fonts.gstatic.com/s/poppins") is False
    assert is_company_website("https://www.googletagmanager.com/gtm.js") is False
    assert is_company_website("https://www.foodistexpo.com/brand/acme") is False
    assert is_company_website("https://cdn.mytuyap.com/assets/css/style.css") is False
    assert is_company_website("https://www.instagram.com/acme") is False


def test_is_company_website_accepts_real_company_domain():
    assert is_company_website("https://www.adafood.com.tr") is True
    assert is_company_website("https://44beydaggida.com/") is True


def test_pick_first_company_website_skips_noise():
    urls = [
        "https://fonts.googleapis.com",
        "https://www.instagram.com/acme",
        "https://www.acme.test",
        "https://shop.acme.test",
    ]
    assert pick_first_company_website(urls) == "https://www.acme.test"


def test_classify_social_url_maps_known_networks():
    assert classify_social_url("https://www.instagram.com/acme") == "instagram_url"
    assert classify_social_url("https://www.linkedin.com/company/acme") == "linkedin_url"
    assert classify_social_url("https://www.facebook.com/acme") == "facebook_url"
    assert classify_social_url("https://x.com/acme") == "x_url"
    assert classify_social_url("https://www.youtube.com/@acme") == "youtube_url"
    assert classify_social_url("https://www.acme.test") is None


def test_extract_social_urls_keeps_first_per_network():
    urls = [
        "https://www.instagram.com/one",
        "https://www.instagram.com/two",
        "https://www.facebook.com/acme",
    ]
    assert extract_social_urls(urls) == {
        "instagram_url": "https://www.instagram.com/one",
        "facebook_url": "https://www.facebook.com/acme",
    }
