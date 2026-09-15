#!/usr/bin/env python3
"""Fail when system-behavior findings regress relative to a comparison base."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: inventory root must be an object")
    return data


def signature(item: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(item.get("category") or ""),
        str(item.get("method") or ""),
        str(item.get("match_path") or item.get("path") or ""),
        str(item.get("file") or ""),
        str(item.get("function") or ""),
    )


def counts(data: dict[str, Any]) -> Counter[tuple[str, ...]]:
    findings = data.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("inventory findings must be an array")
    result: Counter[tuple[str, ...]] = Counter()
    for item in findings:
        if isinstance(item, dict):
            result[signature(item)] += 1
    return result


def format_signature(sig: tuple[str, ...]) -> str:
    category, method, path, file, function = sig
    source = f"{file}:{function}" if function else file
    return f"{category}: {method} {path} | {source}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare system behavior inventories and reject new findings."
    )
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    args = parser.parse_args()

    base = counts(load(args.base))
    current = counts(load(args.current))

    regressions: list[tuple[tuple[str, ...], int, int]] = []
    improvements: list[tuple[tuple[str, ...], int, int]] = []

    for sig in sorted(set(base) | set(current)):
        before = base[sig]
        after = current[sig]
        if after > before:
            regressions.append((sig, before, after))
        elif after < before:
            improvements.append((sig, before, after))

    if regressions:
        print("SYSTEM BEHAVIOR REGRESSION GATE: FAIL")
        print("New/increased findings:")
        for sig, before, after in regressions:
            print(f" - {format_signature(sig)} ({before} -> {after})")
        if improvements:
            removed = sum(before - after for _, before, after in improvements)
            print(f"Improvements elsewhere: {removed} finding(s) removed.")
        print(
            "Existing unresolved behavior may remain at its comparison-base level, "
            "but no new finding is allowed."
        )
        return 1

    removed = sum(before - after for _, before, after in improvements)
    print("SYSTEM BEHAVIOR REGRESSION GATE: PASS")
    print(f"No finding signature increased; improvements={removed}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
