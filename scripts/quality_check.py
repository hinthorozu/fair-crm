#!/usr/bin/env python3
"""Fair CRM quality gate — standards, compile/import and zero-new pytest regressions."""

from __future__ import annotations

import compileall
import json
import subprocess
import sys
from pathlib import Path

from backend_test_baseline import extract_pytest_failures, load_baseline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
FEATURE_CONTRACT_SCHEMA = PROJECT_ROOT / ".kyrox" / "feature-contract.schema.json"


def run_step(name: str, command: list[str], cwd: Path) -> bool:
    print(f"\n== {name} ==", flush=True)
    result = subprocess.run(command, cwd=cwd, check=False)
    ok = result.returncode == 0
    print(f"{'PASS' if ok else 'FAIL'}: {name}", flush=True)
    return ok


def validate_feature_contract_schema() -> bool:
    print("\n== feature contract schema ==", flush=True)
    try:
        with FEATURE_CONTRACT_SCHEMA.open("r", encoding="utf-8") as handle:
            schema = json.load(handle)
        if not isinstance(schema, dict):
            raise ValueError("schema root must be a JSON object")
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise ValueError("unexpected or missing JSON Schema draft")
    except Exception as exc:
        print(f"FAIL: feature contract schema — {exc}", flush=True)
        return False

    print("PASS: feature contract schema", flush=True)
    return True


def run_pytest_regression_gate() -> tuple[bool, int]:
    """Run full pytest and fail only on failures outside the explicit baseline.

    The existing baseline is temporary technical debt, not a success state. CI
    blocks every newly failing test and reports resolved baseline entries so the
    debt file can shrink toward zero.
    """

    print("\n== pytest / zero-new-regression ==", flush=True)
    known_failures, baseline_errors = load_baseline()
    if baseline_errors:
        print("FAIL: backend test baseline is invalid", flush=True)
        for error in baseline_errors:
            print(f" - {error}", flush=True)
        return False, 0

    process = subprocess.Popen(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=BACKEND_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output_lines: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        output_lines.append(line.rstrip("\n"))
    return_code = process.wait()

    if return_code == 0:
        if known_failures:
            print(
                "PASS: pytest has zero failures. "
                f"All {len(known_failures)} baseline entries are candidates for removal.",
                flush=True,
            )
        else:
            print("PASS: pytest (strict zero-failure state)", flush=True)
        return True, 0

    current_failures = extract_pytest_failures(output_lines)
    if not current_failures:
        print(
            "FAIL: pytest exited non-zero but no parseable FAILED/ERROR node ids were found; "
            "treating this as an infrastructure or collection failure.",
            flush=True,
        )
        return False, 0

    new_failures = sorted(current_failures - known_failures)
    baseline_failures = sorted(current_failures & known_failures)
    resolved_failures = sorted(known_failures - current_failures)

    if new_failures:
        print("FAIL: new backend test regressions detected:", flush=True)
        for nodeid in new_failures:
            print(f" - {nodeid}", flush=True)
        print(
            f"Known baseline still failing: {len(baseline_failures)}; "
            f"new failures: {len(new_failures)}.",
            flush=True,
        )
        return False, len(baseline_failures)

    print(
        "PASS: zero-new-regression backend gate — "
        f"{len(baseline_failures)} known baseline failures, 0 new failures.",
        flush=True,
    )
    if resolved_failures:
        print(
            f"BASELINE IMPROVEMENT: {len(resolved_failures)} known failures did not reproduce; "
            "remove them from .kyrox/backend-test-baseline.json after confirming stability:",
            flush=True,
        )
        for nodeid in resolved_failures:
            print(f" - {nodeid}", flush=True)

    return True, len(baseline_failures)


def main() -> int:
    print(f"Fair CRM quality check — {PROJECT_ROOT}", flush=True)

    steps_ok = True

    if not validate_feature_contract_schema():
        steps_ok = False

    if not run_step(
        "backend test baseline structure",
        [sys.executable, "scripts/backend_test_baseline.py"],
        PROJECT_ROOT,
    ):
        steps_ok = False

    if not run_step(
        "development standard / feature contracts",
        [sys.executable, "scripts/validate_feature_contracts.py", "--contracts-only"],
        PROJECT_ROOT,
    ):
        steps_ok = False

    if not compileall.compile_dir(BACKEND_ROOT / "app", quiet=1):
        print("FAIL: Python compile", flush=True)
        steps_ok = False
    else:
        print("PASS: Python compile", flush=True)

    try:
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.main import app, create_app  # noqa: F401

        print("PASS: FastAPI app import", flush=True)
    except Exception as exc:
        print(f"FAIL: FastAPI app import — {exc}", flush=True)
        steps_ok = False

    pytest_ok, known_failure_count = run_pytest_regression_gate()
    if not pytest_ok:
        steps_ok = False

    if steps_ok and known_failure_count:
        print(
            "\nRESULT: QUALITY CHECK PASSED — ZERO NEW REGRESSIONS; "
            f"KNOWN BACKEND TEST DEBT REMAINS ({known_failure_count}, target=0)",
            flush=True,
        )
    else:
        print(
            "\n" + ("RESULT: QUALITY CHECK PASSED" if steps_ok else "RESULT: QUALITY CHECK FAILED"),
            flush=True,
        )
    return 0 if steps_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
