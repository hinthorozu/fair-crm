"""Tests for Foodist detail page parser."""

from app.modules.scraper.parsers.foodist_detail_parser import parse_foodist_detail_html

SAMPLE_DETAIL_HTML = """
<html><body>
  <div class="schedule-single-wrap">
    <h1>Alpha Co</h1>
    <p>Kategori: Gıda Ürünleri</p>
    <p>Adres: İstanbul Fuar Merkezi No: 12</p>
    <p>Telefon: +90 212 555 66 77</p>
    <p>E-posta: info@alpha.test</p>
    <p>Açıklama: Organik gıda üreticisi.</p>
    <a href="https://www.alpha.test">Website</a>
    <a href="mailto:sales@alpha.test">Mail</a>
    <a href="tel:+902125556677">Call</a>
  </div>
</body></html>
"""


def test_foodist_detail_parser_extracts_email_and_phone():
    detail = parse_foodist_detail_html(SAMPLE_DETAIL_HTML)

    assert detail.email == "info@alpha.test"
    assert detail.phone is not None
    assert "212" in detail.phone


def test_foodist_detail_parser_extracts_website_address_category_description():
    detail = parse_foodist_detail_html(SAMPLE_DETAIL_HTML)

    assert detail.website == "https://www.alpha.test"
    assert "alpha.test" in ",".join(detail.websites)
    assert detail.address == "İstanbul Fuar Merkezi No: 12"
    assert detail.category == "Gıda Ürünleri"
    assert detail.description == "Organik gıda üreticisi."


def test_foodist_detail_parser_email_regex_from_plain_text():
    html = """
    <html><body>
      <div class="schedule-detail-info">İletişim: destek@firma.com.tr veya 0212 444 55 66</div>
    </body></html>
    """
    detail = parse_foodist_detail_html(html)

    assert detail.email == "destek@firma.com.tr"
    assert detail.phone is not None


def test_foodist_detail_parser_ignores_head_font_links():
    html = """
    <html><head>
      <link href="https://fonts.googleapis.com/css2?family=Poppins">
      <link href="https://fonts.gstatic.com/s/poppins">
    </head><body>
      <div class="schedule-detail-info">
        <a href="https://www.acme.test">Website</a>
      </div>
    </body></html>
    """
    detail = parse_foodist_detail_html(html)

    assert detail.website == "https://www.acme.test"
    assert all("googleapis" not in url for url in detail.websites)


def test_foodist_detail_parser_reads_website_from_company_info_container():
    html = """
    <html><body>
      <div class="schedule-sidebar">
        <div class="widget">
          <h4 class="widget-title">İletişim</h4>
          <div class="schedule-list">
            <ul>
              <li><i class="far fa-globe"></i>
                <a href="https://44beydaggida.com/" target="_blank">https://44beydaggida.com/</a>
              </li>
            </ul>
            <div class="social">
              <a href="https://www.instagram.com/44beydaggida/"><i class="fab fa-instagram"></i></a>
            </div>
          </div>
        </div>
      </div>
    </body></html>
    """
    detail = parse_foodist_detail_html(html)

    assert detail.website == "https://44beydaggida.com/"
    assert all("instagram.com" not in url for url in detail.websites)
    assert detail.instagram_url == "https://www.instagram.com/44beydaggida/"


def test_foodist_detail_parser_extracts_social_links_without_using_as_website():
    html = """
    <html><body>
      <div class="schedule-sidebar">
        <div class="schedule-list">
          <a href="https://www.acme.test">Website</a>
          <div class="social">
            <a href="https://www.instagram.com/acme/">Instagram</a>
            <a href="https://www.linkedin.com/company/acme">LinkedIn</a>
            <a href="https://www.facebook.com/acme">Facebook</a>
            <a href="https://x.com/acme">X</a>
            <a href="https://www.youtube.com/@acme">YouTube</a>
          </div>
        </div>
      </div>
    </body></html>
    """
    detail = parse_foodist_detail_html(html)

    assert detail.website == "https://www.acme.test"
    assert detail.instagram_url == "https://www.instagram.com/acme/"
    assert detail.linkedin_url == "https://www.linkedin.com/company/acme"
    assert detail.facebook_url == "https://www.facebook.com/acme"
    assert detail.x_url == "https://x.com/acme"
    assert detail.youtube_url == "https://www.youtube.com/@acme"
    assert all("instagram.com" not in url for url in detail.websites)
    assert all("facebook.com" not in url for url in detail.websites)


def test_foodist_detail_parser_parses_real_foodist_sidebar_html():
    html = """
    <html><body>
      <div class="schedule-single-wrap">
        <div class="schedule-detail">
          <span><i class="fa fa-globe"></i> Türkiye</span>
        </div>
        <div class="schedule-sidebar">
          <div class="widget">
            <h4 class="widget-title">Konum Bilgisi</h4>
            <div class="schedule-list">
              <ul>
                <li><i class="far fa-building"></i> Salon: 3</li>
                <li><i class="far fa-map-marker"></i> Stant: 308A</li>
              </ul>
            </div>
          </div>
          <div class="widget">
            <h4 class="widget-title">İletişim</h4>
            <div class="schedule-list">
              <ul>
                <li><i class="far fa-phone"></i> +905462770043</li>
                <li><i class="far fa-location-dot"></i> Organize Sanayi Bölgesi No: 12 İstanbul</li>
                <li><i class="far fa-globe"></i>
                  <a href="https://www.ahugida.com.tr" target="_blank">https://www.ahugida.com.tr</a>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </body></html>
    """
    detail = parse_foodist_detail_html(html)

    assert detail.phone == "+905462770043"
    assert detail.website == "https://www.ahugida.com.tr"
    assert detail.address == "Organize Sanayi Bölgesi No: 12 İstanbul"
    assert detail.hall == "3"
    assert detail.stand == "308A"
    assert detail.country == "Türkiye"


def test_foodist_detail_parser_parses_saved_detail_fixture():
    from pathlib import Path

    html = Path(__file__).resolve().parents[3].joinpath("detail_full.html").read_text(encoding="utf-8")
    detail = parse_foodist_detail_html(html)

    assert detail.phone == "+905355706844"
    assert detail.website == "https://44beydaggida.com/"
    assert "Bayrampaşa" in (detail.address or "")
    assert detail.hall == "8"
    assert detail.stand == "819B"
    assert detail.country == "Türkiye"


def test_foodist_detail_parser_leaves_website_empty_without_detail_container():
    html = """
    <html><head>
      <link href="https://fonts.googleapis.com/css2?family=Poppins">
    </head><body>
      <nav><a href="https://www.acme.test">Nav</a></nav>
      <footer><a href="https://www.acme.test">Footer</a></footer>
    </body></html>
    """
    detail = parse_foodist_detail_html(html)

    assert detail.website is None
    assert detail.websites == ()
