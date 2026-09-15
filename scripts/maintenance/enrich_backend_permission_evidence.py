#!/usr/bin/env python3
"""Enrich backend route permission evidence through dependency-provider imports."""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

PERMISSION_RE = re.compile(r"\b(?:fair_crm|identity)\.[A-Za-z0-9_.-]+\b")


def dotted_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def assignment_strings(tree: ast.AST) -> dict[str, str]:
    result: dict[str, str] = {}
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = literal_string(node.value)
            if value is not None:
                result[node.targets[0].id] = value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            value = literal_string(node.value)
            if value is not None:
                result[node.target.id] = value
    return result


def module_file(root: Path, module: str) -> Path:
    return root / "backend" / f"{module.replace('.', '/')}.py"


def imported_string_constants(root: Path, tree: ast.AST) -> dict[str, str]:
    result: dict[str, str] = {}
    cache: dict[Path, dict[str, str]] = {}
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        source = module_file(root, node.module)
        if not source.exists():
            continue
        if source not in cache:
            try:
                cache[source] = assignment_strings(ast.parse(source.read_text(encoding="utf-8")))
            except (SyntaxError, UnicodeDecodeError):
                cache[source] = {}
        source_constants = cache[source]
        for alias in node.names:
            value = source_constants.get(alias.name)
            if value is not None:
                result[alias.asname or alias.name] = value
    return result


def permission_values(node: ast.AST, constants: dict[str, str]) -> set[str]:
    result: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            if PERMISSION_RE.fullmatch(child.value):
                result.add(child.value)
        elif isinstance(child, ast.Name):
            value = constants.get(child.id)
            if value and PERMISSION_RE.fullmatch(value):
                result.add(value)
    return result


def provider_map(root: Path, file: Path) -> dict[str, set[str]]:
    if not file.exists():
        return {}
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
    except (SyntaxError, UnicodeDecodeError):
        return {}
    constants = assignment_strings(tree)
    constants.update(imported_string_constants(root, tree))
    result: dict[str, set[str]] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        codes = permission_values(node, constants)
        if codes:
            result[node.name] = codes
    return result


def enrich_backend_permission_evidence(root: Path, data: dict[str, Any]) -> None:
    routes = [item for item in data.get("backend_routes") or [] if isinstance(item, dict)]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for route in routes:
        grouped[str(route.get("file") or "")].append(route)

    for rel, route_items in grouped.items():
        route_file = root / rel
        provider_permissions: dict[str, set[str]] = {}
        for candidate in (route_file, route_file.with_name("dependencies.py")):
            for name, codes in provider_map(root, candidate).items():
                provider_permissions.setdefault(name, set()).update(codes)

        for route in route_items:
            discovered: set[str] = set(route.get("permission_codes") or [])
            providers: list[str] = []
            for dependency in route.get("dependencies") or []:
                if not isinstance(dependency, dict):
                    continue
                dep_name = str(dependency.get("dependency") or "").split(".")[-1]
                codes = provider_permissions.get(dep_name, set())
                if codes:
                    discovered.update(codes)
                    providers.append(dep_name)
            if discovered:
                route["permission_codes"] = sorted(discovered)
            if providers:
                route["permission_provider_evidence"] = sorted(set(providers))
                if route.get("permission_evidence") in {None, "unknown"}:
                    route["permission_evidence"] = "dependency_provider_import_chain"

    # Keep already-built frontend/backend link evidence synchronized with the
    # enriched backend route records.
    route_index = {
        (
            str(route.get("file") or ""),
            str(route.get("function") or ""),
            str(route.get("method") or ""),
            str(route.get("match_path") or ""),
        ): route
        for route in routes
    }
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
        route = route_index.get(key)
        if route is None:
            continue
        backend["permission_codes"] = route.get("permission_codes") or []
        backend["permission_evidence"] = route.get("permission_evidence")
        if route.get("permission_provider_evidence"):
            backend["permission_provider_evidence"] = route["permission_provider_evidence"]
