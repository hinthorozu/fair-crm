from app.modules.cost_catalog.slug import next_available_slug, slugify


def test_slugify_handles_turkish_characters() -> None:
    assert slugify("İşçilik & Çözüm Ürünleri") == "iscilik-cozum-urunleri"


def test_next_available_slug_keeps_free_slug() -> None:
    assert next_available_slug("mobilya", {"elektrik"}) == "mobilya"


def test_next_available_slug_adds_next_numeric_suffix() -> None:
    assert next_available_slug("mobilya", {"mobilya", "mobilya-2", "mobilya-3"}) == "mobilya-4"
