#!/usr/bin/env python3
"""Backend test debt baseline helpers and monotonic regression guard.

The repository currently has explicit, pre-existing backend test debt. CI may
accept only failures already recorded in .kyrox/backend-test-baseline.json.
The baseline is monotonic: normal CI allows it to shrink, never to grow.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / ".kyrox" / "backend-test-baseline.json"
PYTEST_SUMMARY_RE = re.compile(r"^(?:FAILED|ERROR)\s+(.+?)(?:\s+-\s+.*)?$")


def validate_baseline_data(data: Any, *, source: str) -> tuple[set[str], list[str]]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return set(), [f"{source}: root must be a JSON object"]

    if data.get("version") != 1:
        errors.append(f"{source}: version must be 1")
    if data.get("policy") != "zero_new_failures":
        errors.append(f"{source}: policy must be 'zero_new_failures'")
    if data.get("target_failure_count") != 0:
        errors.append(f"{source}: target_failure_count must remain 0")

    raw = data.get("known_failures")
    if not isinstance(raw, list):
        errors.append(f"{source}: known_failures must be an array")
        return set(), errors

    known: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{source}: known_failures[{index}] must be a non-empty string")
            continue
        nodeid = item.strip()
        if "::" not in nodeid or not nodeid.startswith("tests/"):
            errors.append(
                f"{source}: known_failures[{index}] must be a pytest node id under tests/"
            )
        known.append(nodeid)

    if len(known) != len(set(known)):
        errors.append(f"{source}: known_failures contains duplicate pytest node ids")

    return set(known), errors


def load_baseline(path: Path = BASELINE_PATH) -> tuple[set[str], list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set(), [f"{path.as_posix()}: baseline file is missing"]
    except json.JSONDecodeError as exc:
        return set(), [f"{path.as_posix()}: invalid JSON: {exc}"]
    return validate_baseline_data(data, source=path.as_posix())


def extract_pytest_failures(lines: Iterable[str]) -> set[str]:
    failures: set[str] = set()
    for raw_line in lines:
        line = raw_line.strip()
        match = PYTEST_SUMMARY_RE.match(line)
        if match:
            failures.add(match.group(1).strip())
    return failures


def _load_baseline_from_git(base: str) -> tuple[set[str] | None, list[str]]:
    result = subprocess.run(
        ["git", "show", f"{base}:.kyrox/backend-test-baseline.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # Initial baseline introduction is allowed. After the file exists on the
        # comparison base, every subsequent change is monotonic-shrink only.
        return None, []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return set(), [f"git:{base}:backend-test-baseline: invalid JSON: {exc}"]
    known, errors = validate_baseline_data(
        data,
        source=f"git:{base}:.kyrox/backend-test-baseline.json",
    )
    return known, errors


def validate_monotonic_baseline(base: str) -> list[str]:
    current, errors = load_baseline()
    if errors:
        return errors

    previous, previous_errors = _load_baseline_from_git(base)
    errors.extend(previous_errors)
    if previous_errors or previous is None:
        return errors

    added = sorted(current - previous)
    if added:
        errors.append(
            "backend test baseline may shrink but must not grow; newly baselined failures: "
            + ", ".join(added)
        )
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate backend test debt baseline.")
    parser.add_argument(
        "--base",
        help="Optional git SHA/ref. When supplied, the current known-failure set must be a subset of the base set.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.base:
        errors = validate_monotonic_baseline(args.base)
    else:
        _, errors = load_baseline()

    if errors:
        print("BACKEND TEST BASELINE GATE: FAIL")
        for error in errors:
            print(f" - {error}")
        return 1

    known, _ = load_baseline()
    print(f"BACKEND TEST BASELINE GATE: PASS ({len(known)} known failures; target=0)")
    if args.base:
        print("Baseline monotonicity: PASS (no new known-failure debt added).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
