#!/usr/bin/env python3
"""Fail when refined system-behavior findings regress relative to a comparison base."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from refine_system_behavior_inventory import rebuild, write_markdown


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: inventory root must be an object")
    return data


def normalize_dynamic_findings(data: dict[str, Any]) -> None:
    """A fully dynamic same-origin URL is unknown, not proof of route drift."""

    findings = data.get("findings") or []
    for item in findings:
        if not isinstance(item, dict):
            continue
        if (
            item.get("category") == "frontend_api_without_backend_route"
            and item.get("match_path") == "/{}"
        ):
            item["category"] = "frontend_dynamic_api_path"
            item["severity"] = "review"

    stats = data.get("stats")
    if isinstance(stats, dict):
        stats["findings_total"] = len(findings)
        stats["regression_findings"] = sum(
            1 for item in findings if isinstance(item, dict) and item.get("severity") == "regression"
        )
        stats["review_findings"] = sum(
            1 for item in findings if isinstance(item, dict) and item.get("severity") == "review"
        )


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


def write_refined(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare refined system behavior inventories and reject new findings."
    )
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument(
        "--base-root",
        type=Path,
        help="Comparison checkout root. Defaults to /tmp/fair-crm-system-base when present.",
    )
    parser.add_argument(
        "--current-root",
        type=Path,
        default=Path.cwd(),
        help="Current checkout root.",
    )
    args = parser.parse_args()

    inferred_base_root = Path("/tmp/fair-crm-system-base")
    base_root = args.base_root or (inferred_base_root if inferred_base_root.exists() else args.current_root)

    base_data = rebuild(base_root.resolve(), load(args.base))
    current_data = rebuild(args.current_root.resolve(), load(args.current))
    normalize_dynamic_findings(base_data)
    normalize_dynamic_findings(current_data)

    # Persist exactly the evidence that the gate compares so CI artifacts and the
    # human report cannot disagree with pass/fail semantics.
    write_refined(args.base, base_data)
    write_refined(args.current, current_data)
    write_markdown(current_data, args.current.parent / "SYSTEM_BEHAVIOR_CURRENT.md")

    base = counts(base_data)
    current = counts(current_data)

    print("SYSTEM BEHAVIOR REFINED COVERAGE")
    for key, value in (current_data.get("stats") or {}).items():
        print(f" - {key}: {value}")

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
