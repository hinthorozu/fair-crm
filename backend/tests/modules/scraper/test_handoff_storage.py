"""Tests for scraper handoff file storage."""

import json
from uuid import uuid4

from app.modules.scraper.exporters.scraper_import_exporter import ScraperImportHandoff
from app.modules.scraper.infrastructure.handoff_storage import resolve_handoff_path, write_handoff_json
from app.modules.scraper.types.scraper_site import ScraperSiteKey
from app.shared.canonical_import.validator import validate_canonical_import


def test_write_handoff_json_creates_canonical_file(tmp_path):
    run_id = uuid4()
    handoff = ScraperImportHandoff(
        canonical_rows=[{"company_name": "Alpha", "website": "", "email": "a@alpha.test", "phone": "111"}],
        row_metadata=[{"source_url": "https://example.test/alpha"}],
        metadata={"source_url": "https://example.test/list"},
    )

    path = write_handoff_json(
        handoff,
        run_id,
        adapter_key=ScraperSiteKey.TUYAP_NEW,
        source_url="https://example.test/list",
        base_dir=tmp_path,
    )

    assert path == str(resolve_handoff_path(run_id, base_dir=tmp_path).resolve())
    payload = json.loads(resolve_handoff_path(run_id, base_dir=tmp_path).read_text(encoding="utf-8"))
    validated = validate_canonical_import(payload)
    assert validated.source.type.value == "scraper"
    assert validated.source.adapter_key == ScraperSiteKey.TUYAP_NEW
    assert validated.source.run_id == run_id
    assert validated.metadata.row_count == 1
    assert validated.rows[0].company_name == "Alpha"
    assert validated.rows[0].emails == ["a@alpha.test"]
