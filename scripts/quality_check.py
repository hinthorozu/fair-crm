#!/usr/bin/env python3
"""Fair CRM quality gate — compile, import, pytest."""

from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"


def run_step(name: str, command: list[str], cwd: Path) -> bool:
    print(f"\n== {name} ==")
    result = subprocess.run(command, cwd=cwd, check=False)
    ok = result.returncode == 0
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
    return ok


def main() -> int:
    print(f"Fair CRM quality check — {PROJECT_ROOT}")

    steps_ok = True

    if not compileall.compile_dir(BACKEND_ROOT / "app", quiet=1):
        print("FAIL: Python compile")
        steps_ok = False
    else:
        print("PASS: Python compile")

    try:
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.main import app, create_app  # noqa: F401

        print("PASS: FastAPI app import")
    except Exception as exc:
        print(f"FAIL: FastAPI app import — {exc}")
        steps_ok = False

    if not run_step(
        "pytest",
        [sys.executable, "-m", "pytest", "-q"],
        BACKEND_ROOT,
    ):
        steps_ok = False

    print("\n" + ("RESULT: QUALITY CHECK PASSED" if steps_ok else "RESULT: QUALITY CHECK FAILED"))
    return 0 if steps_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
