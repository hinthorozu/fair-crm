#!/usr/bin/env python3
"""Fail when a frontend change introduces new UI governance violations.

The full UI inventory contains historical/legacy debt. This comparator makes CI
strict for regressions without pretending that the existing baseline is clean.
A current violation is allowed only up to the count already present for the same
violation class/file in the comparison base.

Canonical UI rules remain in kyrox-platform; this script is enforcement tooling,
not a second policy source.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ViolationSpec = tuple[str, str, tuple[str, ...]]

SPECS: tuple[ViolationSpec, ...] = (
    ("p0", "bare_checkbox_radio", ("file", "kind")),
    ("p0", "local_filters_without_filter_panel", ("file",)),
    ("p0", "raw_form_controls", ("file", "tag")),
    ("p1", "bare_alert_toast", ("file",)),
    ("p1", "bare_card", ("file",)),
    ("p2", "bare_form_error", ("file",)),
    ("p2", "link_button", ("file",)),
    ("p2", "adhoc_empty", ("file",)),
    ("p2", "adhoc_loading", ("file",)),
    ("p2", "bare_action_wrappers", ("file",)),
    ("p3", "bare_icon_buttons", ("file",)),
    ("p3", "login_form_error", ("file",)),
    ("p3", "bare_nav_links", ("file",)),
    ("p3", "missing_pageshell", ("file",)),
    ("p3", "missing_navlink_layouts", ("file",)),
    ("routes", "missing_pageshell_on_mounted", ("file", "route_component")),
    ("routes", "unmounted_page_files", ("file",)),
    ("routes", "routes_missing_smoke_coverage", ("file", "route")),
    ("final", "bare_field_error", ("file",)),
    ("final", "bare_modal_actions", ("file",)),
    ("final", "form_actions_in_modal", ("file",)),
    ("final", "legacy_breakpoints", ("file", "px")),
    ("final", "a11y_icon_buttons_missing_label", ("file",)),
)


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: inventory root must be an object")
    return data


def nested(data: dict[str, Any], section: str, key: str) -> list[dict[str, Any]]:
    section_data = data.get(section)
    if not isinstance(section_data, dict):
        return []
    value = section_data.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def signature(bucket: str, item: dict[str, Any], fields: Iterable[str]) -> tuple[str, ...]:
    values = [bucket]
    for field in fields:
        value = item.get(field, "")
        values.append(str(value))
    return tuple(values)


def inventory_counts(data: dict[str, Any]) -> Counter[tuple[str, ...]]:
    counts: Counter[tuple[str, ...]] = Counter()
    for section, key, fields in SPECS:
        bucket = f"{section}.{key}"
        for item in nested(data, section, key):
            counts[signature(bucket, item, fields)] += 1
    return counts


def format_signature(sig: tuple[str, ...]) -> str:
    bucket, *parts = sig
    detail = " | ".join(part for part in parts if part)
    return f"{bucket}: {detail}" if detail else bucket


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare UI governance inventory against a git-base baseline.")
    parser.add_argument("--base", type=Path, required=True, help="Base inventory.json")
    parser.add_argument("--current", type=Path, required=True, help="Current inventory.json")
    args = parser.parse_args()

    base = inventory_counts(load(args.base))
    current = inventory_counts(load(args.current))

    regressions: list[tuple[tuple[str, ...], int, int]] = []
    improvements = 0

    for sig in sorted(set(base) | set(current)):
        before = base[sig]
        after = current[sig]
        if after > before:
            regressions.append((sig, before, after))
        elif after < before:
            improvements += before - after

    if regressions:
        print("UI GOVERNANCE REGRESSION GATE: FAIL")
        print("New/increased violations:")
        for sig, before, after in regressions:
            print(f" - {format_signature(sig)} ({before} -> {after})")
        if improvements:
            print(f"Improvements elsewhere: {improvements} violation(s) removed.")
        print("Existing legacy violations may remain at baseline count, but no regression is allowed.")
        return 1

    print("UI GOVERNANCE REGRESSION GATE: PASS")
    print(f"No violation class/file increased; improvements={improvements}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
