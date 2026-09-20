#!/usr/bin/env python3
"""Refine the raw Fair CRM system-behavior inventory with stronger static evidence.

The first-pass extractor favors broad discovery. This pass removes known parser
ambiguity without hiding it: TypeScript path expressions are re-evaluated,
permission-factory dependencies are resolved, local helper scope propagation is
followed, and cross-service/internal transport calls are classified separately.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

PERMISSION_RE = re.compile(r"\b(?:fair_crm|identity)\.[a-zA-Z0-9_.-]+\b")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_$][\w$]*$")
CONST_STRING_RE = re.compile(
    r"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*([\"'])(.*?)\2\s*;",
    re.DOTALL,
)


def repo_rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


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


def python_module_file(root: Path, module: str) -> Path:
    return root / "backend" / f"{module.replace('.', '/')}.py"


def imported_string_constants(root: Path, tree: ast.AST) -> dict[str, str]:
    result: dict[str, str] = {}
    cache: dict[Path, dict[str, str]] = {}
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        source = python_module_file(root, node.module)
        if not source.exists():
            continue
        if source not in cache:
            try:
                cache[source] = assignment_strings(ast.parse(source.read_text(encoding="utf-8")))
            except (SyntaxError, UnicodeDecodeError):
                cache[source] = {}
        constants = cache[source]
        for alias in node.names:
            value = constants.get(alias.name)
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


def nested_dependency_permissions(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    constants: dict[str, str],
) -> set[str]:
    """Resolve Depends(require_permission(PERMISSION)) style factories."""

    result: set[str] = set()
    all_args = list(node.args.args) + list(node.args.kwonlyargs)
    defaults: list[ast.AST | None] = (
        [None] * (len(node.args.args) - len(node.args.defaults))
        + list(node.args.defaults)
        + list(node.args.kw_defaults)
    )
    for _, default in zip(all_args, defaults):
        if not isinstance(default, ast.Call):
            continue
        if dotted_name(default.func) not in {"Depends", "fastapi.Depends"} or not default.args:
            continue
        provider = default.args[0]
        if not isinstance(provider, ast.Call):
            continue
        provider_name = (dotted_name(provider.func) or "").split(".")[-1]
        if provider_name not in {
            "require_permission",
            "require_any_permission",
            "require_all_permissions",
            "permission_dependency",
        }:
            continue
        result.update(permission_values(provider, constants))
    return result


def has_auth_org_reference(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and child.attr == "organization_id":
            if isinstance(child.value, ast.Name) and child.value.id == "auth":
                return True
    return False


def called_local_functions(node: ast.AST, known: set[str]) -> set[str]:
    result: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id in known:
            result.add(child.func.id)
    return result


def scope_via_local_helpers(
    start: ast.FunctionDef | ast.AsyncFunctionDef,
    functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
) -> str | None:
    if has_auth_org_reference(start):
        return "auth.organization_id"
    queue = list(called_local_functions(start, set(functions)))
    visited: set[str] = set()
    while queue:
        name = queue.pop(0)
        if name in visited:
            continue
        visited.add(name)
        helper = functions[name]
        if has_auth_org_reference(helper):
            return f"local_helper:{name}"
        queue.extend(called_local_functions(helper, set(functions)) - visited)
    return None


def contract_scope_index(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    directory = root / ".kyrox/features"
    if not directory.exists():
        return result
    for file in directory.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(data, dict) and data.get("id"):
            result[str(data["id"])] = str(data.get("tenant_scope") or "none")
    return result


def refine_backend(root: Path, routes: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for route in routes:
        grouped[str(route.get("file") or "")].append(route)
    contract_scopes = contract_scope_index(root)

    for rel, items in grouped.items():
        source = root / rel
        if not source.exists():
            continue
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except (SyntaxError, UnicodeDecodeError):
            continue
        constants = assignment_strings(tree)
        constants.update(imported_string_constants(root, tree))
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for route in items:
            fn = functions.get(str(route.get("function") or ""))
            if fn is None:
                continue
            nested = nested_dependency_permissions(fn, constants)
            if nested:
                merged = set(route.get("permission_codes") or []) | nested
                route["permission_codes"] = sorted(merged)
                route["permission_evidence"] = "route_permission_factory"

            helper_scope = scope_via_local_helpers(fn, functions)
            if helper_scope:
                route["organization_scope_evidence"] = helper_scope

            scopes = {
                contract_scopes.get(contract_id, "none")
                for contract_id in route.get("feature_contracts") or []
            }
            route["contract_tenant_scopes"] = sorted(scopes - {"none"})
            if scopes and scopes <= {"system", "none"}:
                route["scope_classification"] = "system"
            elif "organization" in scopes or "mixed" in scopes:
                route["scope_classification"] = "organization_or_mixed"
            elif str(route.get("path") or "").startswith("/api/v1/system-admin/"):
                route["scope_classification"] = "system_path_review"
            else:
                route["scope_classification"] = "unknown"


def skip_quoted(text: str, pos: int, quote: str) -> int:
    pos += 1
    escaped = False
    while pos < len(text):
        ch = text[pos]
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == quote:
            return pos + 1
        pos += 1
    return pos


def skip_template(text: str, pos: int) -> int:
    pos += 1
    escaped = False
    while pos < len(text):
        ch = text[pos]
        if escaped:
            escaped = False
            pos += 1
            continue
        if ch == "\\":
            escaped = True
            pos += 1
            continue
        if ch == "`":
            return pos + 1
        if ch == "$" and pos + 1 < len(text) and text[pos + 1] == "{":
            pos = skip_balanced(text, pos + 1, "{", "}")
            continue
        pos += 1
    return pos


def skip_balanced(text: str, pos: int, opener: str, closer: str) -> int:
    depth = 1
    pos += 1
    while pos < len(text) and depth:
        ch = text[pos]
        if ch in {"'", '"'}:
            pos = skip_quoted(text, pos, ch)
            continue
        if ch == "`":
            pos = skip_template(text, pos)
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
        pos += 1
    return pos


def extract_first_argument(text: str, open_paren: int) -> str | None:
    start = open_paren + 1
    pos = start
    depths = {"(": 0, "[": 0, "{": 0}
    closing = {")": "(", "]": "[", "}": "{"}
    while pos < len(text):
        ch = text[pos]
        if ch in {"'", '"'}:
            pos = skip_quoted(text, pos, ch)
            continue
        if ch == "`":
            pos = skip_template(text, pos)
            continue
        if ch in depths:
            depths[ch] += 1
        elif ch in closing:
            opener = closing[ch]
            if depths[opener] > 0:
                depths[opener] -= 1
            elif ch == ")":
                return text[start:pos].strip()
        elif ch == "," and all(value == 0 for value in depths.values()):
            return text[start:pos].strip()
        pos += 1
    return None


def find_transport_call_at_line(text: str, callee: str, line: int) -> tuple[str | None, int, int]:
    line_starts = [0]
    for match in re.finditer("\n", text):
        line_starts.append(match.end())
    start = line_starts[max(0, min(line - 1, len(line_starts) - 1))]
    pattern = re.compile(rf"\b{re.escape(callee)}\b")
    match = pattern.search(text, start)
    if not match:
        return None, start, start
    pos = match.end()
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos < len(text) and text[pos] == "<":
        depth = 1
        pos += 1
        while pos < len(text) and depth:
            if text[pos] == "<":
                depth += 1
            elif text[pos] == ">":
                depth -= 1
            pos += 1
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos >= len(text) or text[pos] != "(":
        return None, match.start(), match.end()
    return extract_first_argument(text, pos), match.start(), pos


def simple_ts_constants(text: str) -> dict[str, str]:
    return {match.group(1): match.group(3) for match in CONST_STRING_RE.finditer(text)}


def parse_template_parts(expr: str) -> list[tuple[str, str]] | None:
    expr = expr.strip()
    if len(expr) < 2 or expr[0] != "`" or expr[-1] != "`":
        return None
    parts: list[tuple[str, str]] = []
    literal_start = 1
    pos = 1
    while pos < len(expr) - 1:
        if expr[pos] == "$" and pos + 1 < len(expr) and expr[pos + 1] == "{":
            if pos > literal_start:
                parts.append(("literal", expr[literal_start:pos]))
            end = skip_balanced(expr, pos + 1, "{", "}")
            parts.append(("expr", expr[pos + 2 : end - 1]))
            pos = end
            literal_start = pos
            continue
        if expr[pos] == "\\":
            pos += 2
            continue
        pos += 1
    if literal_start < len(expr) - 1:
        parts.append(("literal", expr[literal_start:-1]))
    return parts


FAIR_STAND_API_PREFIX = "/api/v1/fair-stand"
CROSS_SERVICE_TARGETS = frozenset({"kyrox-core", "fair-stand"})
PRODUCT_HTTP_TARGETS = frozenset({"fair-crm", "kyrox-core", "fair-stand"})


def product_http_target(path: str | None, *, current: str = "unknown") -> str:
    """Classify a resolved HTTP path. Fair Stand catalog is proxied off-process."""

    if current == "kyrox-core":
        return current
    if path and path.startswith(FAIR_STAND_API_PREFIX):
        return "fair-stand"
    if current != "unknown":
        return current
    if path and path.startswith("/api/"):
        return "fair-crm"
    return "unknown"


def eval_path_expression(expr: str, constants: dict[str, str]) -> tuple[str | None, str, str]:
    """Return (path, target, evidence). target=fair-crm|kyrox-core|fair-stand|unknown."""

    expr = expr.strip()
    if not expr:
        return None, "unknown", "empty"
    if (expr[0:1] in {"'", '"'} and expr[-1:] == expr[0]) and len(expr) >= 2:
        value = expr[1:-1]
        return value, product_http_target(value), "literal"
    if IDENTIFIER_RE.fullmatch(expr):
        if expr in constants:
            value = constants[expr]
            return value, product_http_target(value), f"const:{expr}"
        return None, "unknown", f"identifier:{expr}"

    parts = parse_template_parts(expr)
    if parts is None:
        return None, "unknown", "dynamic_expression"

    target = "unknown"
    output: list[str] = []
    for kind, value in parts:
        if kind == "literal":
            output.append(value)
            continue
        inner = value.strip()
        if inner == "config.apiBaseUrl":
            target = "fair-crm"
            continue
        if inner == "config.coreBaseUrl":
            target = "kyrox-core"
            continue
        if inner in constants:
            resolved = constants[inner]
            output.append(resolved)
            if resolved.startswith("/api/") and target == "unknown":
                target = product_http_target(resolved)
            continue
        lower = inner.lower()
        if (
            ("query" in lower or re.search(r"\bqs\b", lower) or "suffix" in lower)
            and ("?" in inner or inner in {"query", "qs", "suffix"})
        ):
            continue
        output.append("{param}")

    result = "".join(output)
    target = product_http_target(result, current=target)
    return result or None, target, "template"


def normalize_match_path(path: str | None) -> str | None:
    if not path:
        return None
    value = path.split("?", 1)[0].split("#", 1)[0].strip()
    value = re.sub(r"\{param\}", "{}", value)
    value = re.sub(r"\{[^{}]+\}", "{}", value)
    value = re.sub(r"/+", "/", value)
    if not value.startswith("/"):
        value = "/" + value
    if len(value) > 1 and value.endswith("/"):
        value = value[:-1]
    return value


def refine_frontend(root: Path, calls: list[dict[str, Any]]) -> None:
    cache: dict[str, tuple[str, dict[str, str]]] = {}
    for call in calls:
        rel = str(call.get("file") or "")
        source = root / rel
        if not source.exists():
            continue
        if rel not in cache:
            text = source.read_text(encoding="utf-8")
            cache[rel] = (text, simple_ts_constants(text))
        text, constants = cache[rel]
        expr, _, _ = find_transport_call_at_line(
            text,
            str(call.get("callee") or "apiRequest"),
            int(call.get("line") or 1),
        )
        if expr is None:
            call["target"] = "unknown"
            call["path_evidence"] = "transport_call_not_reparsed"
            continue
        path, target, evidence = eval_path_expression(expr, constants)
        call["path_expression"] = expr
        call["path_evidence"] = evidence
        call["target"] = target
        call["path"] = path
        call["match_path"] = normalize_match_path(path)
        call["resolved"] = bool(path and target in PRODUCT_HTTP_TARGETS)
        if target == "unknown" and evidence.startswith("identifier:"):
            call["classification"] = "internal_or_indirect_transport"
        elif target in CROSS_SERVICE_TARGETS:
            call["classification"] = "cross_service_transport"
        else:
            call["classification"] = "product_http_call"


def finding_signature_fields(item: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(item.get("category") or ""),
        str(item.get("method") or ""),
        str(item.get("match_path") or item.get("path") or ""),
        str(item.get("file") or ""),
        str(item.get("function") or ""),
    )


def rebuild(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    backend = [dict(item) for item in data.get("backend_routes", []) if isinstance(item, dict)]
    frontend = [dict(item) for item in data.get("frontend_api_calls", []) if isinstance(item, dict)]
    refine_backend(root, backend)
    refine_frontend(root, frontend)

    backend_index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for route in backend:
        match_path = route.get("match_path")
        if match_path:
            backend_index[(str(route.get("method") or "").upper(), str(match_path))].append(route)

    links: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    cross_service: list[dict[str, Any]] = []

    for call in frontend:
        target = call.get("target") or "unknown"
        if target in CROSS_SERVICE_TARGETS:
            cross_service.append(
                {
                    "target": target,
                    "method": call.get("method"),
                    "path": call.get("path"),
                    "match_path": call.get("match_path"),
                    "file": call.get("file"),
                    "function": call.get("function"),
                    "classification": call.get("classification"),
                }
            )
            continue
        if target == "unknown":
            findings.append(
                {
                    "category": "frontend_transport_target_unknown",
                    "severity": "review",
                    "method": call.get("method") or "",
                    "path": call.get("path"),
                    "match_path": call.get("match_path"),
                    "file": call.get("file") or "",
                    "function": call.get("function"),
                }
            )
            continue
        match_path = call.get("match_path")
        if not match_path:
            findings.append(
                {
                    "category": "frontend_api_unresolved_path",
                    "severity": "regression",
                    "method": call.get("method") or "",
                    "path": call.get("path"),
                    "match_path": match_path,
                    "file": call.get("file") or "",
                    "function": call.get("function"),
                }
            )
            continue
        key = (str(call.get("method") or "").upper(), str(match_path))
        matches = backend_index.get(key, [])
        if not matches:
            findings.append(
                {
                    "category": "frontend_api_without_backend_route",
                    "severity": "regression",
                    "method": call.get("method") or "",
                    "path": call.get("path"),
                    "match_path": match_path,
                    "file": call.get("file") or "",
                    "function": call.get("function"),
                }
            )
            continue
        for route in matches:
            links.append(
                {
                    "method": call.get("method"),
                    "match_path": match_path,
                    "frontend": {
                        "file": call.get("file"),
                        "function": call.get("function"),
                        "path": call.get("path"),
                    },
                    "backend": {
                        "file": route.get("file"),
                        "function": route.get("function"),
                        "path": route.get("path"),
                        "permission_codes": route.get("permission_codes") or [],
                        "permission_evidence": route.get("permission_evidence"),
                        "organization_scope_evidence": route.get("organization_scope_evidence"),
                        "scope_classification": route.get("scope_classification"),
                    },
                }
            )

    for route in backend:
        expected_permissions = set(route.get("contract_permission_codes") or [])
        actual_permissions = set(route.get("permission_codes") or [])
        if expected_permissions and not actual_permissions:
            findings.append(
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
        if actual_permissions and expected_permissions and actual_permissions.isdisjoint(expected_permissions):
            findings.append(
                {
                    "category": "backend_permission_not_in_linked_contracts",
                    "severity": "review",
                    "method": route.get("method") or "",
                    "path": route.get("path"),
                    "match_path": route.get("match_path"),
                    "file": route.get("file") or "",
                    "function": route.get("function"),
                    "permission_codes": sorted(actual_permissions),
                    "contract_permission_codes": sorted(expected_permissions),
                }
            )

        if not actual_permissions:
            continue
        classification = route.get("scope_classification")
        if classification in {"system", "system_path_review"}:
            continue
        if classification == "organization_or_mixed" and route.get("organization_scope_evidence") == "unknown":
            findings.append(
                {
                    "category": "protected_route_scope_unknown",
                    "severity": "review",
                    "method": route.get("method") or "",
                    "path": route.get("path"),
                    "match_path": route.get("match_path"),
                    "file": route.get("file") or "",
                    "function": route.get("function"),
                }
            )

    findings.sort(key=finding_signature_fields)
    links.sort(
        key=lambda item: (
            str(item.get("method") or ""),
            str(item.get("match_path") or ""),
            str(item.get("frontend", {}).get("file") or ""),
            str(item.get("backend", {}).get("file") or ""),
        )
    )
    cross_service.sort(
        key=lambda item: (
            str(item.get("target") or ""),
            str(item.get("method") or ""),
            str(item.get("match_path") or ""),
            str(item.get("file") or ""),
        )
    )

    backend_only = []
    linked_backend = {
        (link["backend"]["file"], link["backend"]["function"], link["method"], link["match_path"])
        for link in links
    }
    for route in backend:
        signature = (
            route.get("file"),
            route.get("function"),
            route.get("method"),
            route.get("match_path"),
        )
        if signature not in linked_backend and str(route.get("path") or "").startswith("/api/v1"):
            backend_only.append(
                {
                    "method": route.get("method"),
                    "path": route.get("path"),
                    "match_path": route.get("match_path"),
                    "file": route.get("file"),
                    "function": route.get("function"),
                }
            )

    stats = dict(data.get("stats") or {})
    stats.update(
        {
            "backend_routes": len(backend),
            "frontend_api_calls": len(frontend),
            "frontend_backend_links": len(links),
            "backend_only_routes": len(backend_only),
            "cross_service_transport_calls": len(cross_service),
            "findings_total": len(findings),
            "regression_findings": sum(1 for item in findings if item.get("severity") == "regression"),
            "review_findings": sum(1 for item in findings if item.get("severity") == "review"),
            "routes_with_permission_evidence": sum(1 for route in backend if route.get("permission_codes")),
            "routes_with_org_scope_evidence": sum(
                1 for route in backend if route.get("organization_scope_evidence") != "unknown"
            ),
        }
    )

    result = dict(data)
    result["refiner"] = "scripts/maintenance/refine_system_behavior_inventory.py"
    result["stats"] = stats
    result["findings"] = findings
    result["links"] = links
    result["frontend_api_calls"] = frontend
    result["backend_routes"] = backend
    result["backend_only_routes"] = backend_only
    result["cross_service_calls"] = cross_service
    return result


def write_markdown(data: dict[str, Any], path: Path) -> None:
    stats = data.get("stats") or {}
    lines = [
        "# Fair CRM System Behavior Inventory",
        "",
        "Generated from executable repository code. UNKNOWN/review evidence is intentionally preserved rather than guessed.",
        "",
        "## Coverage summary",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
    ]
    for key, value in stats.items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Findings", ""])
    findings = data.get("findings") or []
    if not findings:
        lines.append("No static findings.")
    else:
        lines.extend(
            [
                "| Severity | Category | Method | Path | Source |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for item in findings:
            source = f"{item.get('file', '')}:{item.get('function') or ''}"
            lines.append(
                f"| {item.get('severity', '')} | `{item.get('category', '')}` | "
                f"{item.get('method', '')} | `{item.get('path') or item.get('match_path') or ''}` | `{source}` |"
            )
    lines.extend(["", "## Cross-service transport", ""])
    cross = data.get("cross_service_calls") or []
    if not cross:
        lines.append("No directly discovered cross-service transport calls.")
    else:
        lines.extend(
            [
                "| Target | Method | Path | Source |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in cross:
            lines.append(
                f"| {item.get('target', '')} | {item.get('method', '')} | "
                f"`{item.get('path') or item.get('match_path') or ''}` | "
                f"`{item.get('file', '')}:{item.get('function') or ''}` |"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Refine Fair CRM system behavior inventory evidence.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()

    data = rebuild(args.root.resolve(), load_json(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.markdown:
        write_markdown(data, args.markdown)

    print("SYSTEM BEHAVIOR REFINEMENT")
    for key, value in (data.get("stats") or {}).items():
        print(f" - {key}: {value}")
    print("SYSTEM BEHAVIOR REFINEMENT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
