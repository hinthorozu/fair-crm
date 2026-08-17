#!/usr/bin/env python3
"""Generate a validated KYROX Fair CRM Feature Contract.

The generator provides safe profile defaults, but it does not make product or
security decisions. Review every generated REQUIRED/N/A value before coding.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_feature_contracts import GATES, validate_contract

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / ".kyrox" / "features"

FEATURE_TYPES = (
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
)

FRONTEND_DEFAULT_TRUE = {
    "crud_module",
    "read_only_module",
    "user_triggered_operation",
    "system_admin",
    "ui_only",
}

BACKEND_DEFAULT_TRUE = {
    "crud_module",
    "read_only_module",
    "backend_service",
    "background_job",
    "scheduled_job",
    "user_triggered_operation",
    "integration_adapter",
    "system_admin",
    "core_platform_capability",
    "maintenance",
}

PERMISSION_REQUIRED_TYPES = {
    "crud_module",
    "read_only_module",
    "user_triggered_operation",
    "system_admin",
}

AUDIT_DEFAULT_TYPES = {
    "crud_module",
    "background_job",
    "scheduled_job",
    "user_triggered_operation",
    "integration_adapter",
    "system_admin",
}


def gate(required: bool, reason: str | None = None) -> dict[str, str]:
    if required:
        return {"status": "required"}
    return {"status": "na", "reason": reason or "Not applicable to this feature profile."}


def parse_permission(raw: str) -> dict[str, object]:
    parts = raw.split(":")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "permission must be code:action:scope:assignable, for example "
            "fair_crm.xyz.execute:execute:organization:true"
        )
    code, action, scope, assignable_raw = (part.strip() for part in parts)
    if scope not in {"organization", "system"}:
        raise argparse.ArgumentTypeError("permission scope must be organization or system")
    lowered = assignable_raw.lower()
    if lowered not in {"true", "false"}:
        raise argparse.ArgumentTypeError("permission assignable must be true or false")
    return {
        "code": code,
        "action": action,
        "scope": scope,
        "assignable": lowered == "true",
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Create a validated .kyrox/features/<id>.json Feature Contract."
    )
    p.add_argument("feature_id")
    p.add_argument("--type", required=True, choices=FEATURE_TYPES, dest="feature_type")
    p.add_argument("--title")
    p.add_argument("--owner", choices=("fair-crm", "kyrox-core"), default="fair-crm")
    p.add_argument(
        "--platform-reusability",
        choices=("product_specific", "platform_generic", "existing_core_capability"),
        default="product_specific",
    )
    p.add_argument(
        "--trigger",
        choices=("user", "api", "scheduled", "internal", "event", "mixed", "none"),
        default="none",
    )
    p.add_argument(
        "--tenant-scope",
        required=True,
        choices=("organization", "system", "mixed", "none"),
    )
    p.add_argument(
        "--path",
        action="append",
        dest="paths",
        required=True,
        help="Affected repo path or glob. Repeat for multiple paths.",
    )
    p.add_argument(
        "--permission",
        action="append",
        type=parse_permission,
        default=[],
        help="code:action:scope:assignable. Repeat for multiple permissions.",
    )
    p.add_argument("--route", action="append", default=[])
    p.add_argument("--menu", action="store_true")
    p.add_argument("--menu-permission")
    frontend = p.add_mutually_exclusive_group()
    frontend.add_argument("--frontend", dest="frontend", action="store_true")
    frontend.add_argument("--no-frontend", dest="frontend", action="store_false")
    p.set_defaults(frontend=None)
    p.add_argument("--output", type=Path)
    p.add_argument("--force", action="store_true")
    return p


def build_contract(args: argparse.Namespace) -> dict[str, object]:
    feature_type = args.feature_type
    frontend_required = (
        feature_type in FRONTEND_DEFAULT_TRUE if args.frontend is None else args.frontend
    )
    backend_required = feature_type in BACKEND_DEFAULT_TRUE
    permissions_required = bool(args.permission)

    if feature_type in PERMISSION_REQUIRED_TYPES and not args.permission:
        raise ValueError(
            f"{feature_type} requires explicit --permission declarations; "
            "the generator will not invent permission semantics"
        )

    if feature_type == "system_admin":
        for item in args.permission:
            if item["scope"] != "system":
                raise ValueError("system_admin permissions must use scope=system")
            if item["assignable"] is not False:
                raise ValueError("system_admin SYSTEM permissions must use assignable=false")

    if not frontend_required and (args.route or args.menu or args.menu_permission):
        raise ValueError("routes/menu/menu-permission cannot be declared with --no-frontend")

    declared_codes = {str(item["code"]) for item in args.permission}
    if args.menu:
        if not args.menu_permission:
            raise ValueError("--menu requires --menu-permission")
        if args.menu_permission not in declared_codes:
            raise ValueError(
                "--menu-permission must be one of this contract's explicit --permission codes"
            )

    if feature_type == "scheduled_job" and args.trigger == "none":
        args.trigger = "scheduled"
    if feature_type == "user_triggered_operation" and args.trigger == "none":
        args.trigger = "user"
    if feature_type == "ui_only" and not frontend_required:
        raise ValueError("ui_only cannot use --no-frontend")

    user_facing = frontend_required or args.trigger in {"user", "api", "mixed"}

    permission_reason = None
    if not permissions_required:
        permission_reason = (
            "No end-user authorization boundary is part of this approved feature profile."
        )

    frontend_reason = None
    if not frontend_required:
        frontend_reason = "No user-facing route, page, menu or browser action is in scope."

    tenant_required = backend_required and args.tenant_scope in {"organization", "mixed"}
    runtime_auth_required = permissions_required and args.trigger in {"user", "api", "mixed"}
    if feature_type in {"crud_module", "read_only_module", "system_admin"}:
        runtime_auth_required = True

    database_required = feature_type == "crud_module"
    migration_required = database_required
    api_required = feature_type in {
        "crud_module",
        "read_only_module",
        "user_triggered_operation",
        "system_admin",
    }
    if args.trigger == "api":
        api_required = True

    audit_required = backend_required and feature_type in AUDIT_DEFAULT_TYPES
    forms_required = frontend_required and feature_type in {
        "crud_module",
        "user_triggered_operation",
        "system_admin",
    }

    app: dict[str, dict[str, str]] = {name: gate(False) for name in GATES}
    app["database"] = gate(
        database_required,
        "This profile does not require new persistent product data by default; set REQUIRED if the design adds storage.",
    )
    app["migration"] = gate(
        migration_required,
        "No schema/catalog migration is implied by this profile default; set REQUIRED when the design changes schema or permissions.",
    )
    app["permissions"] = gate(permissions_required, permission_reason)
    app["backend"] = gate(backend_required, "This is a frontend-only feature profile.")
    app["api"] = gate(api_required, "No public/user-facing API endpoint is part of this feature profile.")
    app["tenant_isolation"] = gate(
        tenant_required,
        "The feature does not process organization-owned backend data under the declared tenant scope.",
    )
    app["audit"] = gate(
        audit_required,
        "The profile has no approved mutation/external side effect requiring product audit by default.",
    )
    app["frontend"] = gate(frontend_required, frontend_reason)
    app["ui_permissions"] = gate(
        frontend_required and permissions_required,
        "No protected user-facing UI permission boundary exists for this feature.",
    )
    app["menu"] = gate(args.menu, "No navigation menu entry is part of the approved feature.")
    app["route_guard"] = gate(
        frontend_required and permissions_required and bool(args.route),
        "No protected browser route requiring a deep-link guard is declared.",
    )
    app["forms"] = gate(forms_required, "No create/edit/update form flow is part of this feature profile.")
    app["visual_qa"] = gate(frontend_required, frontend_reason)
    app["backend_tests"] = gate(backend_required, "No backend executable behavior changes in this profile.")
    app["frontend_tests"] = gate(frontend_required, frontend_reason)
    app["runtime_authorization"] = gate(
        runtime_auth_required,
        "No end-user/JWT authorization boundary triggers this feature.",
    )
    app["runtime_verification"] = gate(
        backend_required or frontend_required,
        "No executable runtime behavior is changed by this contract.",
    )
    app["deployment"] = gate(
        backend_required or frontend_required or migration_required,
        "No deployable runtime/schema artifact is changed by this contract.",
    )

    contract: dict[str, object] = {
        "version": 1,
        "id": args.feature_id,
        "title": args.title or args.feature_id.replace("_", " ").replace("-", " ").title(),
        "feature_type": feature_type,
        "owner": args.owner,
        "platform_reusability": args.platform_reusability,
        "trigger": args.trigger,
        "tenant_scope": args.tenant_scope,
        "user_facing": user_facing,
        "affected_paths": args.paths,
        "permissions": {
            "required": permissions_required,
            **({} if permissions_required else {"reason": permission_reason}),
            "items": args.permission,
        },
        "frontend": {
            "required": frontend_required,
            **({} if frontend_required else {"reason": frontend_reason}),
            "routes": args.route,
            "menu": args.menu,
            "menu_permission": args.menu_permission,
        },
        "applicability": app,
        "notes": (
            "Generated profile defaults must be reviewed against the approved Delivery Contract "
            "before implementation. Change any default that does not match the real feature."
        ),
    }
    return contract


def main() -> int:
    args = parser().parse_args()
    try:
        contract = build_contract(args)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    output = args.output or (DEFAULT_DIR / f"{args.feature_id}.json")
    if not output.is_absolute():
        output = ROOT / output

    errors = validate_contract(output, contract)
    if errors:
        print("Generated contract is not valid:")
        for error in errors:
            print(f" - {error}")
        print("No file was written.")
        return 1

    if output.exists() and not args.force:
        print(f"ERROR: {output.relative_to(ROOT)} already exists; use --force to replace it")
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Created {output.relative_to(ROOT)}")
    print("Review every REQUIRED/N/A decision before coding; generated defaults are not product approval.")
    print("Validate with: python scripts/validate_feature_contracts.py --contracts-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
