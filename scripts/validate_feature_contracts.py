#!/usr/bin/env python3
"""Validate KYROX Fair CRM machine-readable Feature Contracts.

Canonical semantics:
kyrox-platform/projects/fair-crm/FEATURE_APPLICABILITY_STANDARD.md

This gate intentionally validates only properties it can prove reliably:
contract structure/consistency plus detectable material-change coverage.
Runtime authorization and tenant correctness remain separate acceptance gates.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FEATURE_DIR = ROOT / ".kyrox" / "features"

FEATURE_TYPES = {
    "crud_module",
    "read_only_module",
    "backend_service",
    "background_job",
    "scheduled_job",
    "user_triggered_operation",
    "integration_adapter",
    "system_admin",
    "core_platform_capability",
    "ui_only",
    "maintenance",
    "other",
}
OWNERS = {"fair-crm", "kyrox-core"}
PLATFORM_REUSABILITY = {"product_specific", "platform_generic", "existing_core_capability"}
TRIGGERS = {"user", "api", "scheduled", "internal", "event", "mixed", "none"}
TENANT_SCOPES = {"organization", "system", "mixed", "none"}
PERMISSION_SCOPES = {"organization", "system"}
GATE_STATES = {"required", "na"}
GATES = (
    "database",
    "migration",
    "permissions",
    "backend",
    "api",
    "tenant_isolation",
    "audit",
    "frontend",
    "ui_permissions",
    "menu",
    "route_guard",
    "forms",
    "visual_qa",
    "backend_tests",
    "frontend_tests",
    "runtime_authorization",
    "runtime_verification",
    "deployment",
)
PERMISSION_RE = re.compile(r"\b(?:fair_crm|identity|audit)\.[a-z0-9_]+(?:\.[a-z0-9_]+)+\b")
FAIR_PERMISSION_RE = re.compile(r"\bfair_crm\.[a-z0-9_]+(?:\.[a-z0-9_]+)+\b")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
BACKGROUND_NAME_RE = re.compile(
    r"(?:^|/)(?:[^/]*(?:job|worker|scheduler|adapter)[^/]*)\.py$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Contract:
    path: Path
    data: dict[str, Any]

    @property
    def feature_id(self) -> str:
        value = self.data.get("id")
        return value if isinstance(value, str) else self.path.stem

    @property
    def affected_paths(self) -> list[str]:
        raw = self.data.get("affected_paths")
        return [item for item in raw if isinstance(item, str)] if isinstance(raw, list) else []

    @property
    def permission_codes(self) -> set[str]:
        permissions = self.data.get("permissions")
        if not isinstance(permissions, dict):
            return set()
        items = permissions.get("items")
        if not isinstance(items, list):
            return set()
        codes: set[str] = set()
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("code"), str):
                codes.add(item["code"])
        return codes


def _fail(errors: list[str], path: Path, message: str) -> None:
    errors.append(f"{path.as_posix()}: {message}")


def _nonempty_reason(value: Any) -> bool:
    return isinstance(value, str) and len(value.strip()) >= 8


def _gate_status(data: dict[str, Any], name: str) -> str | None:
    applicability = data.get("applicability")
    if not isinstance(applicability, dict):
        return None
    gate = applicability.get(name)
    if not isinstance(gate, dict):
        return None
    status = gate.get("status")
    return status if isinstance(status, str) else None


def validate_contract(path: Path, data: Any) -> list[str]:
    errors: list[str] = []

    if not isinstance(data, dict):
        return [f"{path.as_posix()}: root must be a JSON object"]

    required_top = (
        "version",
        "id",
        "title",
        "feature_type",
        "owner",
        "platform_reusability",
        "trigger",
        "tenant_scope",
        "user_facing",
        "affected_paths",
        "permissions",
        "frontend",
        "applicability",
    )
    for key in required_top:
        if key not in data:
            _fail(errors, path, f"missing required field '{key}'")

    if data.get("version") != 1:
        _fail(errors, path, "version must be 1")

    feature_id = data.get("id")
    if not isinstance(feature_id, str) or not ID_RE.fullmatch(feature_id):
        _fail(errors, path, "id must be lowercase letters/numbers with optional '-' or '_'")

    title = data.get("title")
    if not isinstance(title, str) or len(title.strip()) < 2:
        _fail(errors, path, "title must be a non-empty string")

    feature_type = data.get("feature_type")
    if feature_type not in FEATURE_TYPES:
        _fail(errors, path, f"feature_type must be one of {sorted(FEATURE_TYPES)}")

    if data.get("owner") not in OWNERS:
        _fail(errors, path, f"owner must be one of {sorted(OWNERS)}")

    if data.get("platform_reusability") not in PLATFORM_REUSABILITY:
        _fail(errors, path, f"platform_reusability must be one of {sorted(PLATFORM_REUSABILITY)}")

    trigger = data.get("trigger")
    if trigger not in TRIGGERS:
        _fail(errors, path, f"trigger must be one of {sorted(TRIGGERS)}")

    tenant_scope = data.get("tenant_scope")
    if tenant_scope not in TENANT_SCOPES:
        _fail(errors, path, f"tenant_scope must be one of {sorted(TENANT_SCOPES)}")

    user_facing = data.get("user_facing")
    if not isinstance(user_facing, bool):
        _fail(errors, path, "user_facing must be boolean")

    affected_paths = data.get("affected_paths")
    if not isinstance(affected_paths, list) or not affected_paths:
        _fail(errors, path, "affected_paths must be a non-empty array")
    elif not all(isinstance(item, str) and item.strip() for item in affected_paths):
        _fail(errors, path, "affected_paths entries must be non-empty strings")

    applicability = data.get("applicability")
    if not isinstance(applicability, dict):
        _fail(errors, path, "applicability must be an object")
    else:
        missing_gates = [gate for gate in GATES if gate not in applicability]
        if missing_gates:
            _fail(errors, path, f"applicability missing gates: {', '.join(missing_gates)}")
        unknown_gates = sorted(set(applicability) - set(GATES))
        if unknown_gates:
            _fail(errors, path, f"applicability has unknown gates: {', '.join(unknown_gates)}")

        for gate_name in GATES:
            gate = applicability.get(gate_name)
            if not isinstance(gate, dict):
                continue
            status = gate.get("status")
            if status not in GATE_STATES:
                _fail(errors, path, f"applicability.{gate_name}.status must be 'required' or 'na'")
            if status == "na" and not _nonempty_reason(gate.get("reason")):
                _fail(
                    errors,
                    path,
                    f"applicability.{gate_name}=na requires a concrete reason (>= 8 chars)",
                )

    permissions = data.get("permissions")
    if not isinstance(permissions, dict):
        _fail(errors, path, "permissions must be an object")
    else:
        perm_required = permissions.get("required")
        items = permissions.get("items")
        if not isinstance(perm_required, bool):
            _fail(errors, path, "permissions.required must be boolean")
        if not isinstance(items, list):
            _fail(errors, path, "permissions.items must be an array")
            items = []

        if perm_required is False:
            if items:
                _fail(errors, path, "permissions.required=false requires an empty items array")
            if not _nonempty_reason(permissions.get("reason")):
                _fail(
                    errors,
                    path,
                    "permissions.required=false requires a concrete reason (>= 8 chars)",
                )
            if _gate_status(data, "permissions") != "na":
                _fail(errors, path, "permissions.required=false requires applicability.permissions=na")
        elif perm_required is True:
            if not items:
                _fail(errors, path, "permissions.required=true requires at least one permission item")
            if _gate_status(data, "permissions") != "required":
                _fail(errors, path, "permissions.required=true requires applicability.permissions=required")

        seen_codes: set[str] = set()
        for index, item in enumerate(items):
            prefix = f"permissions.items[{index}]"
            if not isinstance(item, dict):
                _fail(errors, path, f"{prefix} must be an object")
                continue
            code = item.get("code")
            action = item.get("action")
            scope = item.get("scope")
            assignable = item.get("assignable")
            if not isinstance(code, str) or not PERMISSION_RE.fullmatch(code):
                _fail(errors, path, f"{prefix}.code is not a valid permission code")
            elif code in seen_codes:
                _fail(errors, path, f"duplicate permission code '{code}'")
            else:
                seen_codes.add(code)
            if not isinstance(action, str) or not action.strip():
                _fail(errors, path, f"{prefix}.action must be non-empty")
            if scope not in PERMISSION_SCOPES:
                _fail(errors, path, f"{prefix}.scope must be organization or system")
            if not isinstance(assignable, bool):
                _fail(errors, path, f"{prefix}.assignable must be boolean")
            if scope == "system" and assignable is not False:
                _fail(errors, path, f"{prefix}: SYSTEM permissions must have assignable=false")

    frontend = data.get("frontend")
    if not isinstance(frontend, dict):
        _fail(errors, path, "frontend must be an object")
    else:
        frontend_required = frontend.get("required")
        routes = frontend.get("routes")
        menu = frontend.get("menu")
        if not isinstance(frontend_required, bool):
            _fail(errors, path, "frontend.required must be boolean")
        if not isinstance(routes, list) or not all(
            isinstance(route, str) and route.strip() for route in routes
        ):
            _fail(errors, path, "frontend.routes must be an array of non-empty strings")
            routes = []
        if not isinstance(menu, bool):
            _fail(errors, path, "frontend.menu must be boolean")

        if frontend_required is False:
            if routes:
                _fail(errors, path, "frontend.required=false requires routes=[]")
            if menu is True:
                _fail(errors, path, "frontend.required=false requires menu=false")
            if not _nonempty_reason(frontend.get("reason")):
                _fail(
                    errors,
                    path,
                    "frontend.required=false requires a concrete reason (>= 8 chars)",
                )
            for gate_name in (
                "frontend",
                "ui_permissions",
                "menu",
                "route_guard",
                "forms",
                "visual_qa",
                "frontend_tests",
            ):
                if _gate_status(data, gate_name) != "na":
                    _fail(
                        errors,
                        path,
                        f"frontend.required=false requires applicability.{gate_name}=na",
                    )
        elif frontend_required is True:
            if user_facing is False:
                _fail(errors, path, "frontend.required=true requires user_facing=true")
            if _gate_status(data, "frontend") != "required":
                _fail(errors, path, "frontend.required=true requires applicability.frontend=required")
            if _gate_status(data, "visual_qa") != "required":
                _fail(errors, path, "frontend.required=true requires applicability.visual_qa=required")
            if _gate_status(data, "frontend_tests") != "required":
                _fail(errors, path, "frontend.required=true requires applicability.frontend_tests=required")

        if menu is True:
            menu_permission = frontend.get("menu_permission")
            if not isinstance(menu_permission, str) or not menu_permission.strip():
                _fail(errors, path, "frontend.menu=true requires menu_permission")
            if _gate_status(data, "menu") != "required":
                _fail(errors, path, "frontend.menu=true requires applicability.menu=required")

    if tenant_scope == "organization" and _gate_status(data, "backend") == "required":
        if _gate_status(data, "tenant_isolation") != "required":
            _fail(
                errors,
                path,
                "organization-scoped backend requires applicability.tenant_isolation=required",
            )

    if feature_type == "crud_module":
        for gate_name in (
            "database",
            "permissions",
            "backend",
            "api",
            "backend_tests",
            "runtime_authorization",
        ):
            if _gate_status(data, gate_name) != "required":
                _fail(errors, path, f"crud_module requires applicability.{gate_name}=required")
        if not isinstance(frontend, dict) or frontend.get("required") is not True:
            _fail(errors, path, "crud_module requires frontend.required=true")

    if feature_type == "read_only_module":
        for gate_name in ("backend", "api", "backend_tests"):
            if _gate_status(data, gate_name) != "required":
                _fail(errors, path, f"read_only_module requires applicability.{gate_name}=required")
        if not isinstance(frontend, dict) or frontend.get("required") is not True:
            _fail(errors, path, "read_only_module requires frontend.required=true")

    if feature_type in {"backend_service", "background_job", "scheduled_job", "integration_adapter"}:
        for gate_name in ("backend", "backend_tests"):
            if _gate_status(data, gate_name) != "required":
                _fail(errors, path, f"{feature_type} requires applicability.{gate_name}=required")

    if feature_type == "scheduled_job" and trigger not in {"scheduled", "internal", "mixed"}:
        _fail(errors, path, "scheduled_job trigger must be scheduled, internal or mixed")

    if feature_type == "user_triggered_operation":
        if trigger not in {"user", "api", "mixed"}:
            _fail(errors, path, "user_triggered_operation trigger must be user, api or mixed")
        if not isinstance(permissions, dict) or permissions.get("required") is not True:
            _fail(errors, path, "user_triggered_operation requires permissions.required=true")
        for gate_name in ("backend", "api", "backend_tests", "runtime_authorization"):
            if _gate_status(data, gate_name) != "required":
                _fail(
                    errors,
                    path,
                    f"user_triggered_operation requires applicability.{gate_name}=required",
                )

    if feature_type == "system_admin":
        if not isinstance(permissions, dict) or permissions.get("required") is not True:
            _fail(errors, path, "system_admin requires permissions.required=true")
        else:
            for index, item in enumerate(permissions.get("items") or []):
                if isinstance(item, dict) and item.get("scope") != "system":
                    _fail(
                        errors,
                        path,
                        f"system_admin permissions.items[{index}] must use scope=system",
                    )
        if _gate_status(data, "runtime_authorization") != "required":
            _fail(
                errors,
                path,
                "system_admin requires applicability.runtime_authorization=required",
            )

    if feature_type == "ui_only":
        if _gate_status(data, "frontend") != "required":
            _fail(errors, path, "ui_only requires applicability.frontend=required")
        if _gate_status(data, "backend") != "na":
            _fail(errors, path, "ui_only requires applicability.backend=na")

    if _gate_status(data, "backend") == "required" and _gate_status(data, "backend_tests") != "required":
        _fail(errors, path, "backend executable behavior requires applicability.backend_tests=required")

    if _gate_status(data, "frontend") == "required" and _gate_status(data, "frontend_tests") != "required":
        _fail(errors, path, "frontend behavior requires applicability.frontend_tests=required")

    return errors


def load_contracts() -> tuple[list[Contract], list[str]]:
    contracts: list[Contract] = []
    errors: list[str] = []
    if not FEATURE_DIR.exists():
        return contracts, errors

    for path in sorted(FEATURE_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.as_posix()}: invalid JSON: {exc}")
            continue
        contract_errors = validate_contract(path, data)
        errors.extend(contract_errors)
        if not contract_errors and isinstance(data, dict):
            contracts.append(Contract(path=path, data=data))
    return contracts, errors


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def base_has_prefix(base: str, prefix: str) -> bool:
    result = run_git(["ls-tree", "-r", "--name-only", base, "--", prefix], check=False)
    return result.returncode == 0 and bool(result.stdout.strip())


def changed_entries(base: str, head: str) -> list[tuple[str, str]]:
    result = run_git(["diff", "--name-status", "--find-renames", f"{base}...{head}"])
    entries: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        entries.append((status, path))
    return entries


def added_permission_codes(base: str, head: str) -> set[str]:
    result = run_git(
        ["diff", "--unified=0", f"{base}...{head}", "--", "backend", "frontend"],
        check=False,
    )
    codes: set[str] = set()
    if result.returncode != 0:
        return codes
    for line in result.stdout.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        codes.update(FAIR_PERMISSION_RE.findall(line))
    return codes


def contract_matches_path(contract: Contract, path: str) -> bool:
    for pattern in contract.affected_paths:
        normalized = pattern.rstrip("/")
        if fnmatch.fnmatch(path, normalized):
            return True
        if normalized.endswith("/**") and path.startswith(normalized[:-3].rstrip("/") + "/"):
            return True
        if not any(char in normalized for char in "*?[") and (
            path == normalized or path.startswith(normalized.rstrip("/") + "/")
        ):
            return True
    return False


def material_change_errors(contracts: list[Contract], base: str, head: str) -> list[str]:
    errors: list[str] = []
    entries = changed_entries(base, head)
    added_paths = [path for status, path in entries if status.startswith("A")]

    material_paths: set[str] = set()
    new_modules: set[str] = set()

    for path in added_paths:
        parts = Path(path).parts
        if len(parts) >= 4 and parts[:3] == ("backend", "app", "modules"):
            module = parts[3]
            prefix = f"backend/app/modules/{module}"
            if not base_has_prefix(base, prefix):
                new_modules.add(module)
                material_paths.add(path)

        if path.startswith("frontend/src/pages/") and path.endswith((".tsx", ".ts")):
            material_paths.add(path)

        if path.startswith("backend/app/modules/") and BACKGROUND_NAME_RE.search(path):
            material_paths.add(path)

    for material_path in sorted(material_paths):
        if not any(contract_matches_path(contract, material_path) for contract in contracts):
            errors.append(
                f"material change '{material_path}' is not covered by any "
                ".kyrox/features/*.json affected_paths"
            )

    new_permissions = added_permission_codes(base, head)
    declared_permissions = (
        set().union(*(contract.permission_codes for contract in contracts)) if contracts else set()
    )
    for code in sorted(new_permissions - declared_permissions):
        errors.append(
            f"new permission '{code}' is not declared by any .kyrox/features/*.json contract"
        )

    if (new_modules or new_permissions or material_paths) and not contracts:
        errors.append(
            "material feature changes detected but no valid .kyrox/features/*.json Feature Contract exists"
        )

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate KYROX Fair CRM Feature Contracts.")
    parser.add_argument("--base", help="Base git SHA/ref for material-change coverage checks.")
    parser.add_argument("--head", default="HEAD", help="Head git SHA/ref (default: HEAD).")
    parser.add_argument(
        "--contracts-only",
        action="store_true",
        help="Validate contract consistency only; skip git diff material-change checks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contracts, errors = load_contracts()

    if args.base and not args.contracts_only:
        errors.extend(material_change_errors(contracts, args.base, args.head))

    if errors:
        print("DEVELOPMENT STANDARD GATE: FAIL")
        for error in errors:
            print(f" - {error}")
        return 1

    print(
        "DEVELOPMENT STANDARD GATE: PASS "
        f"({len(contracts)} valid feature contract{'s' if len(contracts) != 1 else ''})"
    )
    if not args.base and not args.contracts_only:
        print("NOTE: no --base supplied; material-change coverage check skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
