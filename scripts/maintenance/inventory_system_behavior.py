#!/usr/bin/env python3
"""Generate a static Fair CRM system-behavior inventory.

This is enforcement tooling, not a second policy source. Canonical semantics live
in kyrox-platform's System Behavior Map Standard.

The inventory is intentionally conservative: facts that cannot be proven
statically are reported as unknown instead of being guessed.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERSION = 1
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
PERMISSION_RE = re.compile(r"\b(?:fair_crm|identity)\.[a-zA-Z0-9_.-]+\b")
TEMPLATE_EXPR_RE = re.compile(r"\$\{[^{}]*\}")
PATH_PARAM_RE = re.compile(r"\{[^{}]+\}")
EXPORT_FN_RE = re.compile(
    r"\bexport\s+(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
    re.MULTILINE,
)
EXPORT_CONST_RE = re.compile(
    r"\bexport\s+const\s+([A-Za-z_$][\w$]*)\s*=",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Mount:
    source_file: str
    source_symbol: str
    mount_prefix: str
    include_in_schema: bool


def repo_rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def dotted_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def annotation_name(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return dotted_name(node)


def normalize_join(*parts: str) -> str:
    value = "".join(part or "" for part in parts)
    value = re.sub(r"/+", "/", value)
    if not value.startswith("/"):
        value = "/" + value
    if len(value) > 1 and value.endswith("/"):
        value = value[:-1]
    return value


def normalize_match_path(path: str) -> str:
    path = path.split("?", 1)[0].split("#", 1)[0].strip()
    path = TEMPLATE_EXPR_RE.sub("{}", path)
    path = PATH_PARAM_RE.sub("{}", path)
    path = re.sub(r"/+", "/", path)
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def source_module_to_file(module: str) -> str:
    return f"backend/{module.replace('.', '/')}.py"


def router_prefixes(tree: ast.AST) -> dict[str, str]:
    result: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        target: ast.AST | None
        value: ast.AST | None
        if isinstance(node, ast.Assign):
            target = node.targets[0] if len(node.targets) == 1 else None
            value = node.value
        else:
            target = node.target
            value = node.value
        if not isinstance(target, ast.Name) or not isinstance(value, ast.Call):
            continue
        if dotted_name(value.func) not in {"APIRouter", "fastapi.APIRouter"}:
            continue
        prefix = ""
        for kw in value.keywords:
            if kw.arg == "prefix":
                prefix = literal_string(kw.value) or ""
        result[target.id] = prefix
    return result


def parse_v1_mounts(root: Path) -> tuple[str, list[Mount]]:
    router_path = root / "backend/app/api/v1/router.py"
    if not router_path.exists():
        return "/api/v1", []
    text = router_path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(router_path))
    imports: dict[str, tuple[str, str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        source_file = source_module_to_file(node.module)
        for alias in node.names:
            imports[alias.asname or alias.name] = (source_file, alias.name)

    base_prefix = router_prefixes(tree).get("api_v1_router", "/api/v1")
    mounts: list[Mount] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "include_router":
            continue
        if dotted_name(node.func.value) != "api_v1_router" or not node.args:
            continue
        alias_name = dotted_name(node.args[0])
        if not alias_name or alias_name not in imports:
            continue
        source_file, source_symbol = imports[alias_name]
        mount_prefix = ""
        include_in_schema = True
        for kw in node.keywords:
            if kw.arg == "prefix":
                mount_prefix = literal_string(kw.value) or ""
            elif kw.arg == "include_in_schema" and isinstance(kw.value, ast.Constant):
                include_in_schema = bool(kw.value.value)
        mounts.append(
            Mount(
                source_file=source_file,
                source_symbol=source_symbol,
                mount_prefix=mount_prefix,
                include_in_schema=include_in_schema,
            )
        )
    return base_prefix, mounts


def assignment_strings(tree: ast.AST) -> dict[str, str]:
    values: dict[str, str] = {}
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = literal_string(node.value)
            if value is not None:
                values[node.targets[0].id] = value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            value = literal_string(node.value)
            if value is not None:
                values[node.target.id] = value
    return values


def permission_codes_in_node(node: ast.AST, constants: dict[str, str]) -> set[str]:
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            if PERMISSION_RE.fullmatch(child.value):
                found.add(child.value)
        elif isinstance(child, ast.Name):
            value = constants.get(child.id)
            if value and PERMISSION_RE.fullmatch(value):
                found.add(value)
    return found


def provider_permission_map(py_file: Path) -> dict[str, set[str]]:
    if not py_file.exists():
        return {}
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    except SyntaxError:
        return {}
    constants = assignment_strings(tree)
    result: dict[str, set[str]] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            codes = permission_codes_in_node(node, constants)
            if codes:
                result[node.name] = codes
    return result


def class_permission_index(root: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    app_root = root / "backend/app"
    if not app_root.exists():
        return {}
    for py_file in app_root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue
        constants = assignment_strings(tree)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                codes = permission_codes_in_node(node, constants)
                if codes:
                    result[node.name].update(codes)
    return {key: set(value) for key, value in result.items()}


def depends_name(default: ast.AST | None) -> str | None:
    if not isinstance(default, ast.Call) or dotted_name(default.func) not in {"Depends", "fastapi.Depends"}:
        return None
    if not default.args:
        return None
    return dotted_name(default.args[0])


def function_dependencies(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict[str, str | None]]:
    args = list(node.args.args)
    defaults: list[ast.AST | None] = [None] * (len(args) - len(node.args.defaults)) + list(node.args.defaults)
    result: list[dict[str, str | None]] = []
    for arg, default in zip(args, defaults):
        dep = depends_name(default)
        if dep:
            result.append(
                {
                    "parameter": arg.arg,
                    "dependency": dep,
                    "annotation": annotation_name(arg.annotation),
                }
            )
    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        dep = depends_name(default)
        if dep:
            result.append(
                {
                    "parameter": arg.arg,
                    "dependency": dep,
                    "annotation": annotation_name(arg.annotation),
                }
            )
    return result


def has_auth_org_reference(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and child.attr == "organization_id":
            if isinstance(child.value, ast.Name) and child.value.id == "auth":
                return True
        if isinstance(child, ast.keyword) and child.arg == "organization_id":
            value = child.value
            if isinstance(value, ast.Attribute) and value.attr == "organization_id":
                if isinstance(value.value, ast.Name) and value.value.id == "auth":
                    return True
    return False


def decorator_route(decorator: ast.AST) -> tuple[str, str, str] | None:
    if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
        return None
    method = decorator.func.attr.lower()
    if method not in HTTP_METHODS:
        return None
    router_var = dotted_name(decorator.func.value)
    if not router_var:
        return None
    route_path = ""
    if decorator.args:
        route_path = literal_string(decorator.args[0]) or ""
    return router_var, method.upper(), route_path


def decorator_keyword(decorator: ast.Call, name: str) -> str | int | None:
    for kw in decorator.keywords:
        if kw.arg != name:
            continue
        if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, (str, int)):
            return kw.value.value
        try:
            return ast.unparse(kw.value)
        except Exception:
            return dotted_name(kw.value)
    return None


def load_feature_contracts(root: Path) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, list[str]]]:
    directory = root / ".kyrox/features"
    contracts: list[dict[str, Any]] = []
    path_to_ids: dict[str, list[str]] = defaultdict(list)
    path_to_permissions: dict[str, list[str]] = defaultdict(list)
    if not directory.exists():
        return contracts, {}, {}
    for file in sorted(directory.glob("*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        contract_id = str(data.get("id") or file.stem)
        affected_paths = [str(item) for item in data.get("affected_paths", []) if isinstance(item, str)]
        permission_items = (
            data.get("permissions", {}).get("items", [])
            if isinstance(data.get("permissions"), dict)
            else []
        )
        permission_codes = [
            str(item.get("code"))
            for item in permission_items
            if isinstance(item, dict) and item.get("code")
        ]
        contracts.append(
            {
                "id": contract_id,
                "file": repo_rel(root, file),
                "tenant_scope": data.get("tenant_scope"),
                "affected_paths": affected_paths,
                "permissions": sorted(set(permission_codes)),
            }
        )
        for affected in affected_paths:
            path_to_ids[affected].append(contract_id)
            path_to_permissions[affected].extend(permission_codes)
    return contracts, dict(path_to_ids), {
        key: sorted(set(value)) for key, value in path_to_permissions.items()
    }


def backend_routes(root: Path) -> list[dict[str, Any]]:
    base_prefix, mounts = parse_v1_mounts(root)
    class_permissions = class_permission_index(root)
    mounts_by_source_symbol: dict[tuple[str, str], list[Mount]] = defaultdict(list)
    for mount in mounts:
        mounts_by_source_symbol[(mount.source_file, mount.source_symbol)].append(mount)

    routes: list[dict[str, Any]] = []
    backend_root = root / "backend/app"
    if not backend_root.exists():
        return routes

    for py_file in sorted(backend_root.rglob("*.py")):
        if "tests" in py_file.parts or "__pycache__" in py_file.parts:
            continue
        rel = repo_rel(root, py_file)
        try:
            text = py_file.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue
        prefixes = router_prefixes(tree)
        constants = assignment_strings(tree)

        dependency_permissions: dict[str, set[str]] = {}
        sibling_dependencies = py_file.with_name("dependencies.py")
        if sibling_dependencies != py_file:
            dependency_permissions.update(provider_permission_map(sibling_dependencies))
        dependency_permissions.update(provider_permission_map(py_file))

        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            dependencies = function_dependencies(node)
            direct_permission_codes: set[str] = set()
            use_case_permission_codes: set[str] = set()
            use_case_types: set[str] = set()
            for dep in dependencies:
                dep_name = (dep.get("dependency") or "").split(".")[-1]
                direct_permission_codes.update(dependency_permissions.get(dep_name, set()))
                annotation = dep.get("annotation")
                if annotation:
                    tail = annotation.split(".")[-1].replace(" | None", "")
                    if tail.endswith(("UseCase", "Service")):
                        use_case_types.add(tail)
                        use_case_permission_codes.update(class_permissions.get(tail, set()))

            body_permission_codes = permission_codes_in_node(node, constants)
            permission_codes = sorted(
                direct_permission_codes | use_case_permission_codes | body_permission_codes
            )

            for decorator in node.decorator_list:
                route_info = decorator_route(decorator)
                if not route_info:
                    continue
                router_var, method, route_path = route_info
                router_prefix = prefixes.get(router_var, "")
                local_path = normalize_join(router_prefix, route_path)
                decorator_call = decorator if isinstance(decorator, ast.Call) else None
                status_code = decorator_keyword(decorator_call, "status_code") if decorator_call else None
                response_model = decorator_keyword(decorator_call, "response_model") if decorator_call else None

                relevant_mounts = mounts_by_source_symbol.get((rel, router_var), [])
                if rel == "backend/app/main.py" and router_var == "app":
                    relevant_mounts = [Mount(rel, "app", "", True)]
                if not relevant_mounts:
                    relevant_mounts = [Mount(rel, router_var, "", True)]

                for mount in relevant_mounts:
                    if rel == "backend/app/main.py":
                        full_path = local_path
                    elif (rel, router_var) in mounts_by_source_symbol:
                        full_path = normalize_join(base_prefix, mount.mount_prefix, local_path)
                    else:
                        full_path = local_path
                    routes.append(
                        {
                            "method": method,
                            "path": full_path,
                            "match_path": normalize_match_path(full_path),
                            "local_path": local_path,
                            "file": rel,
                            "function": node.name,
                            "router": router_var,
                            "mount_prefix": mount.mount_prefix,
                            "include_in_schema": mount.include_in_schema,
                            "line": node.lineno,
                            "dependencies": dependencies,
                            "use_case_types": sorted(use_case_types),
                            "permission_codes": permission_codes,
                            "permission_evidence": (
                                "route_dependency"
                                if direct_permission_codes or body_permission_codes
                                else "application_use_case"
                                if use_case_permission_codes
                                else "unknown"
                            ),
                            "organization_scope_evidence": (
                                "auth.organization_id" if has_auth_org_reference(node) else "unknown"
                            ),
                            "status_code": status_code,
                            "response_model": response_model,
                        }
                    )
    routes.sort(key=lambda item: (item["path"], item["method"], item["file"], item["function"]))
    return routes


def enclosing_export_name(text: str, position: int) -> str | None:
    candidates: list[tuple[int, str]] = []
    for pattern in (EXPORT_FN_RE, EXPORT_CONST_RE):
        for match in pattern.finditer(text, 0, position):
            candidates.append((match.start(), match.group(1)))
    return max(candidates)[1] if candidates else None


def extract_js_string_argument(text: str, open_paren_index: int) -> tuple[str | None, int]:
    pos = open_paren_index + 1
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos >= len(text) or text[pos] not in {"'", '"', "`"}:
        return None, pos
    quote = text[pos]
    pos += 1
    start = pos
    escaped = False
    while pos < len(text):
        ch = text[pos]
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == quote:
            return text[start:pos], pos + 1
        pos += 1
    return None, pos


def frontend_display_path(raw: str) -> str:
    raw = raw.replace("${config.apiBaseUrl}", "")
    raw = TEMPLATE_EXPR_RE.sub("{param}", raw)
    return raw


def find_call_end(text: str, open_paren_index: int) -> int:
    depth = 0
    quote: str | None = None
    escaped = False
    for pos in range(open_paren_index, len(text)):
        ch = text[pos]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in {"'", '"', "`"}:
            quote = ch
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return pos + 1
    return min(len(text), open_paren_index + 1200)


def request_method_near(text: str, start: int, end: int, default: str = "GET") -> str:
    fragment = text[start:end]
    match = re.search(r"\bmethod\s*:\s*[\"'](GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)[\"']", fragment, re.I)
    return match.group(1).upper() if match else default


def frontend_api_calls(root: Path) -> list[dict[str, Any]]:
    api_root = root / "frontend/src/api"
    if not api_root.exists():
        return []
    records: list[dict[str, Any]] = []
    call_pattern = re.compile(r"\b(apiRequest|fetchWithTimeout)\s*(?:<[^;\n(]+>)?\s*\(")
    for file in sorted(api_root.rglob("*.ts")):
        if file.name.endswith((".test.ts", ".spec.ts")):
            continue
        text = file.read_text(encoding="utf-8")
        rel = repo_rel(root, file)
        for match in call_pattern.finditer(text):
            callee = match.group(1)
            open_paren = text.find("(", match.start())
            raw_path, arg_end = extract_js_string_argument(text, open_paren)
            call_end = find_call_end(text, open_paren)
            function_name = enclosing_export_name(text, match.start())
            line = text.count("\n", 0, match.start()) + 1
            if raw_path is None:
                records.append(
                    {
                        "function": function_name,
                        "callee": callee,
                        "method": request_method_near(text, arg_end, call_end),
                        "path": None,
                        "match_path": None,
                        "file": rel,
                        "line": line,
                        "resolved": False,
                    }
                )
                continue
            display_path = frontend_display_path(raw_path)
            method = request_method_near(text, arg_end, call_end)
            records.append(
                {
                    "function": function_name,
                    "callee": callee,
                    "method": method,
                    "path": display_path,
                    "match_path": normalize_match_path(display_path),
                    "file": rel,
                    "line": line,
                    "resolved": display_path.startswith("/"),
                }
            )
    records.sort(
        key=lambda item: (
            item["file"],
            item["function"] or "",
            item["line"],
        )
    )
    return records


def line_snippet(text: str, line_number: int) -> str:
    lines = text.splitlines()
    if 1 <= line_number <= len(lines):
        return lines[line_number - 1].strip()[:240]
    return ""


def attach_ui_references(root: Path, api_calls: list[dict[str, Any]]) -> None:
    names = sorted({item["function"] for item in api_calls if item.get("function")})
    if not names:
        return
    source_root = root / "frontend/src"
    candidate_files = [
        path
        for path in source_root.rglob("*")
        if path.suffix in {".ts", ".tsx"}
        and "/api/" not in path.as_posix()
        and not path.name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
    ]
    refs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for file in candidate_files:
        text = file.read_text(encoding="utf-8")
        rel = repo_rel(root, file)
        for name in names:
            pattern = re.compile(rf"\b{re.escape(name)}\b")
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                snippet = line_snippet(text, line)
                kind = "call" if re.search(rf"\b{re.escape(name)}\s*\(", snippet) else "reference"
                refs[name].append(
                    {
                        "file": rel,
                        "line": line,
                        "kind": kind,
                        "snippet": snippet,
                    }
                )
                if len(refs[name]) >= 30:
                    break
    for item in api_calls:
        name = item.get("function")
        item["ui_references"] = refs.get(name, []) if name else []


def route_key(method: str, match_path: str | None) -> tuple[str, str] | None:
    if not match_path:
        return None
    return method.upper(), match_path


def build_inventory(root: Path) -> dict[str, Any]:
    contracts, path_contracts, path_contract_permissions = load_feature_contracts(root)
    backend = backend_routes(root)
    frontend = frontend_api_calls(root)
    attach_ui_references(root, frontend)

    for route in backend:
        route["feature_contracts"] = path_contracts.get(route["file"], [])
        route["contract_permission_codes"] = path_contract_permissions.get(route["file"], [])
    for call in frontend:
        call["feature_contracts"] = path_contracts.get(call["file"], [])
        call["contract_permission_codes"] = path_contract_permissions.get(call["file"], [])

    backend_index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for route in backend:
        key = route_key(route["method"], route["match_path"])
        if key:
            backend_index[key].append(route)

    frontend_index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for call in frontend:
        key = route_key(call["method"], call.get("match_path"))
        if key:
            frontend_index[key].append(call)

    findings: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    for call in frontend:
        key = route_key(call["method"], call.get("match_path"))
        if not call.get("resolved") or key is None:
            findings.append(
                {
                    "category": "frontend_api_unresolved_path",
                    "severity": "regression",
                    "method": call["method"],
                    "path": call.get("path"),
                    "match_path": call.get("match_path"),
                    "file": call["file"],
                    "function": call.get("function"),
                }
            )
            continue
        matches = backend_index.get(key, [])
        if not matches and str(call.get("path") or "").startswith("/api/"):
            if str(call.get("path") or "").startswith("/api/v1/fair-stand"):
                continue
            findings.append(
                {
                    "category": "frontend_api_without_backend_route",
                    "severity": "regression",
                    "method": call["method"],
                    "path": call.get("path"),
                    "match_path": call.get("match_path"),
                    "file": call["file"],
                    "function": call.get("function"),
                }
            )
        for route in matches:
            links.append(
                {
                    "method": call["method"],
                    "match_path": call["match_path"],
                    "frontend": {
                        "file": call["file"],
                        "function": call.get("function"),
                        "path": call.get("path"),
                    },
                    "backend": {
                        "file": route["file"],
                        "function": route["function"],
                        "path": route["path"],
                        "permission_codes": route["permission_codes"],
                        "organization_scope_evidence": route["organization_scope_evidence"],
                    },
                }
            )

    for route in backend:
        if not route["path"].startswith("/api/v1"):
            continue
        if not route["permission_codes"]:
            findings.append(
                {
                    "category": "backend_route_without_permission_evidence",
                    "severity": "review",
                    "method": route["method"],
                    "path": route["path"],
                    "match_path": route["match_path"],
                    "file": route["file"],
                    "function": route["function"],
                }
            )
        if route["permission_codes"] and any(
            code.startswith(("fair_crm.", "identity.")) for code in route["permission_codes"]
        ):
            if route["organization_scope_evidence"] == "unknown":
                findings.append(
                    {
                        "category": "protected_route_scope_unknown",
                        "severity": "review",
                        "method": route["method"],
                        "path": route["path"],
                        "match_path": route["match_path"],
                        "file": route["file"],
                        "function": route["function"],
                    }
                )

    backend_only = []
    for key, routes in backend_index.items():
        if key not in frontend_index:
            for route in routes:
                backend_only.append(
                    {
                        "method": route["method"],
                        "path": route["path"],
                        "match_path": route["match_path"],
                        "file": route["file"],
                        "function": route["function"],
                    }
                )

    findings.sort(
        key=lambda item: (
            item["category"],
            item.get("method") or "",
            item.get("match_path") or "",
            item.get("file") or "",
            item.get("function") or "",
        )
    )
    links.sort(
        key=lambda item: (
            item["method"],
            item["match_path"],
            item["frontend"]["file"],
            item["backend"]["file"],
        )
    )

    stats = {
        "backend_routes": len(backend),
        "frontend_api_calls": len(frontend),
        "frontend_backend_links": len(links),
        "backend_only_routes": len(backend_only),
        "feature_contracts": len(contracts),
        "findings_total": len(findings),
        "regression_findings": sum(1 for item in findings if item["severity"] == "regression"),
        "review_findings": sum(1 for item in findings if item["severity"] == "review"),
        "routes_with_permission_evidence": sum(1 for route in backend if route["permission_codes"]),
        "routes_with_direct_org_scope_evidence": sum(
            1 for route in backend if route["organization_scope_evidence"] != "unknown"
        ),
        "frontend_api_functions_with_ui_reference": len(
            {
                item["function"]
                for item in frontend
                if item.get("function") and item.get("ui_references")
            }
        ),
    }

    return {
        "version": VERSION,
        "generator": "scripts/maintenance/inventory_system_behavior.py",
        "root": ".",
        "stats": stats,
        "findings": findings,
        "links": links,
        "frontend_api_calls": frontend,
        "backend_routes": backend,
        "backend_only_routes": backend_only,
        "feature_contracts": contracts,
    }


def write_markdown(inventory: dict[str, Any], output: Path) -> None:
    stats = inventory["stats"]
    lines = [
        "# Fair CRM System Behavior Inventory",
        "",
        "Generated from executable repository code. This report is evidence, not a normative source of truth.",
        "",
        "## Coverage summary",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
    ]
    for key, value in stats.items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Findings", ""])
    if not inventory["findings"]:
        lines.append("No static findings.")
    else:
        lines.extend(
            [
                "| Severity | Category | Method | Path | Source |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for item in inventory["findings"]:
            source = f"{item.get('file', '')}:{item.get('function', '')}"
            lines.append(
                f"| {item.get('severity', '')} | `{item.get('category', '')}` | "
                f"{item.get('method', '')} | `{item.get('path') or item.get('match_path') or ''}` | `{source}` |"
            )
    lines.extend(["", "## Linked frontend → backend calls", ""])
    if not inventory["links"]:
        lines.append("No static frontend/backend links found.")
    else:
        lines.extend(
            [
                "| Method | Path | Frontend | Backend | Permission | Org scope evidence |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in inventory["links"]:
            backend_info = item["backend"]
            permissions = ", ".join(backend_info.get("permission_codes", [])) or "UNKNOWN"
            lines.append(
                f"| {item['method']} | `{item['match_path']}` | "
                f"`{item['frontend']['file']}:{item['frontend'].get('function') or '?'}` | "
                f"`{backend_info['file']}:{backend_info['function']}` | "
                f"`{permissions}` | `{backend_info.get('organization_scope_evidence', 'unknown')}` |"
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Fair CRM system behavior inventory.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument(
        "--fail-on-regression-findings",
        action="store_true",
        help="Fail when the generated inventory contains any regression-severity finding.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    inventory = build_inventory(root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.markdown:
        write_markdown(inventory, args.markdown)

    stats = inventory["stats"]
    print("SYSTEM BEHAVIOR INVENTORY")
    for key, value in stats.items():
        print(f" - {key}: {value}")

    if args.fail_on_regression_findings and stats["regression_findings"]:
        print("SYSTEM BEHAVIOR INVENTORY: FAIL — regression findings remain.")
        return 1
    print("SYSTEM BEHAVIOR INVENTORY: PASS (inventory generated).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
