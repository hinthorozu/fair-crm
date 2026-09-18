"""Regression: maintenance contracts without a product UI cannot mark frontend_tests required."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_feature_contracts import validate_contract  # noqa: E402

CONTRACT_PATH = (
    REPO_ROOT / ".kyrox" / "features" / "source-contract-line-ending-portability.json"
)


def test_on_disk_source_contract_pairs_frontend_false_with_frontend_tests_na() -> None:
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert data["frontend"]["required"] is False
    assert data["applicability"]["frontend_tests"]["status"] == "na"
    assert validate_contract(CONTRACT_PATH, data) == []


def test_frontend_required_false_rejects_frontend_tests_required() -> None:
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    invalid = deepcopy(data)
    invalid["applicability"]["frontend_tests"] = {"status": "required"}

    errors = validate_contract(CONTRACT_PATH, invalid)

    assert any(
        "frontend.required=false requires applicability.frontend_tests=na" in error
        for error in errors
    )
