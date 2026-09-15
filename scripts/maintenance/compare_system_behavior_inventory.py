#!/usr/bin/env python3
"""Fail when refined system-behavior findings regress relative to a comparison base."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from enrich_backend_permission_evidence import enrich_backend_permission_evidence
from refine_system_behavior_inventory import rebuild, write_markdown

PERMISSION_CODE_RE = re.compile(r'"((?:fair_crm|identity)\.[A-Za-z0-9_.-]+)"')


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: inventory root must be an object")
    return data


def canonical_permission_catalog(root: Path) -> set[str]:
    path = root / "frontend/src/permissions/corePermissions.ts"
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    return set(PERMISSION_CODE_RE.findall(text))


def route_signature(route: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(route.get("file") or ""),
        str(route.get("function") or ""),
        str(route.get("method") or ""),
        str(route.get("match_path") or ""),
    )


def normalize_permission_evidence(data: dict[str, Any], root: Path) -> None:
    """Keep only catalogued permissions as effective permission evidence.

    The broad extractor deliberately discovers all fair_crm.* strings, which can
    include audit action names such as fair_crm.fair.created. Those are useful raw
    candidates but must not be presented as RBAC permissions unless the product
    permission catalog recognizes them.
    """

    catalog = canonical_permission_catalog(root)
    if not catalog:
        return

    route_permissions: dict[tuple[str, str, str, str], list[str]] = {}
    for route in data.get("backend_routes") or []:
        if not isinstance(route, dict):
            continue
        raw = [str(code) for code in route.get("permission_codes") or []]
        effective = sorted(code for code in raw if code in catalog)
        noncatalog = sorted(code for code in raw if code not in catalog)
        route["permission_candidates"] = raw
        route["permission_codes"] = effective
        if noncatalog:
            route["noncatalog_permission_candidates"] = noncatalog
        route_permissions[route_signature(route)] = effective

    for link in data.get("links") or []:
        if not isinstance(link, dict):
            continue
        backend = link.get("backend")
        if not isinstance(backend, dict):
            continue
        key = (
            str(backend.get("file") or ""),
            str(backend.get("function") or ""),
            str(link.get("method") or ""),
            str(link.get("match_path") or ""),
        )
        if key in route_permissions:
            backend["permission_codes"] = route_permissions[key]


def normalize_findings(data: dict[str, Any]) -> None:
    """Remove stale/low-confidence findings and classify unresolved evidence honestly."""

    routes = [item for item in data.get("backend_routes") or [] if isinstance(item, dict)]
    route_by_key = {route_signature(route): route for route in routes}

    normalized: list[dict[str, Any]] = []
    existing_permission_unknown: set[tuple[str, str, str, str]] = set()

    for raw_item in data.get("findings") or []:
        if not isinstance(raw_item, dict):
            continue
        item = dict(raw_item)

        # A fully dynamic same-origin URL is unknown, not proof that a backend
        # route does not exist.
        if (
            item.get("category") == "frontend_api_without_backend_route"
            and item.get("match_path") == "/{}"
        ):
            item["category"] = "frontend_dynamic_api_path"
            item["severity"] = "review"

        # Current feature-contract linkage is intentionally path/file-level, not
        # exact route-level. Comparing an exact route permission against every
        # permission mentioned by every contract touching the file creates false
        # drift. Keep exact route permission evidence, but do not claim a
        # route-contract mismatch until contract linkage itself is route-specific.
        if item.get("category") == "backend_permission_not_in_linked_contracts":
            continue

        if item.get("category") == "backend_permission_evidence_unknown":
            key = (
                str(item.get("file") or ""),
                str(item.get("function") or ""),
                str(item.get("method") or ""),
                str(item.get("match_path") or ""),
            )
            route = route_by_key.get(key)
            # Raw discovery may have emitted UNKNOWN before the later provider/
            # catalog enrichment proved the effective permission. Never retain a
            # stale UNKNOWN after stronger evidence exists.
            if route is not None and route.get("permission_codes"):
                continue
            existing_permission_unknown.add(key)

        normalized.append(item)

    # Filtering audit/event strings out of permission evidence can reveal routes
    # that have a permission contract but no proven effective backend permission.
    for route in routes:
        expected = route.get("contract_permission_codes") or []
        actual = route.get("permission_codes") or []
        if not expected or actual:
            continue
        key = route_signature(route)
        if key in existing_permission_unknown:
            continue
        normalized.append(
            {
                "category": "backend_permission_evidence_unknown",
                "severity": "review",
                "method": route.get("method") or "",
                "path": route.get("path"),
                "match_path": route.get("match_path"),
                "file": route.get("file") or "",
                "function": route.get("function"),
            }
        )

    normalized.sort(key=signature)
    data["findings"] = normalized
    stats = data.get("stats")
    if isinstance(stats, dict):
        stats["findings_total"] = len(normalized)
        stats["regression_findings"] = sum(
            1 for item in normalized if item.get("severity") == "regression"
        )
        stats["review_findings"] = sum(
            1 for item in normalized if item.get("severity") == "review"
        )
        stats["routes_with_permission_evidence"] = sum(
            1 for route in routes if route.get("permission_codes")
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
    current_root = args.current_root.resolve()
    base_root = base_root.resolve()

    base_data = rebuild(base_root, load(args.base))
    current_data = rebuild(current_root, load(args.current))

    enrich_backend_permission_evidence(base_root, base_data)
    enrich_backend_permission_evidence(current_root, current_data)
    normalize_permission_evidence(base_data, base_root)
    normalize_permission_evidence(current_data, current_root)
    normalize_findings(base_data)
    normalize_findings(current_data)

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
