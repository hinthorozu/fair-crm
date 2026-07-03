"""Shared paths for the maintenance developer toolkit."""

from __future__ import annotations

import sys
from pathlib import Path

MAINTENANCE_DIR = Path(__file__).resolve().parent
ROOT = MAINTENANCE_DIR.parents[1]
BACKEND = ROOT / "backend"
REPORTS_DIR = MAINTENANCE_DIR / "reports"
EXPORTS_DIR = MAINTENANCE_DIR / "exports"
ANALYSIS_DIR = MAINTENANCE_DIR / "analysis"


def bootstrap() -> None:
    """Add maintenance + backend to sys.path and load backend .env."""
    for path in (MAINTENANCE_DIR, BACKEND):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

    from dotenv import load_dotenv

    load_dotenv(BACKEND / ".env")
