"""Fail CI when organization-scoped product code lacks isolation evidence.

This is deliberately a repository/system governance test rather than a domain
unit test. The full backend pytest suite runs it on every backend-affecting PR.

Contract:
- production modules are auto-discovered by the presence of ``organization_id``;
- every discovered module must have registered ABC/XYZ isolation evidence or a
  narrow architectural exclusion with a reason;
- registered evidence must resolve to executable pytest code;
- a module cannot be both covered and excluded.

The evidence tests themselves remain responsible for exercising the applicable
adversarial cases (own-org success, foreign direct IDs, relationships, bulk,
exports/downloads and async identifiers as applicable).
"""

from __future__ import annotations

from pathlib import Path

from .tenant_isolation_registry import (
    TENANT_ISOLATION_EVIDENCE,
    TENANT_SCOPE_EXCLUSIONS,
)


BACKEND_ROOT = Path(__file__).resolve().parents[2]
APP_MODULES_ROOT = BACKEND_ROOT / "app" / "modules"
TESTS_ROOT = BACKEND_ROOT / "tests"


def _module_uses_organization_scope(module_dir: Path) -> bool:
    for source_file in module_dir.rglob("*.py"):
        try:
            source = source_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "organization_id" in source:
            return True
    return False


def _discovered_organization_scoped_modules() -> set[str]:
    return {
        module_dir.name
        for module_dir in APP_MODULES_ROOT.iterdir()
        if module_dir.is_dir()
        and not module_dir.name.startswith("_")
        and _module_uses_organization_scope(module_dir)
    }


def _evidence_python_files(relative_path: str) -> list[Path]:
    evidence_path = TESTS_ROOT / relative_path
    if evidence_path.is_file():
        return [evidence_path] if evidence_path.suffix == ".py" else []
    if evidence_path.is_dir():
        return sorted(evidence_path.rglob("test_*.py"))
    return []


def test_every_organization_scoped_module_has_registered_isolation_contract() -> None:
    discovered = _discovered_organization_scoped_modules()
    registered = set(TENANT_ISOLATION_EVIDENCE)
    excluded = set(TENANT_SCOPE_EXCLUSIONS)

    overlap = registered & excluded
    assert not overlap, (
        "Tenant-isolation registry error: modules cannot be both covered and "
        f"excluded: {sorted(overlap)}"
    )

    missing = discovered - registered - excluded
    assert not missing, (
        "New organization-scoped FAIR CRM module(s) have no tenant-isolation "
        f"contract: {sorted(missing)}. Register ABC/XYZ adversarial test evidence "
        "in tests/system/tenant_isolation_registry.py. Do not add an exclusion "
        "unless the module truly owns no organization-scoped product data."
    )


def test_registered_isolation_evidence_resolves_to_executable_pytest() -> None:
    discovered = _discovered_organization_scoped_modules()
    errors: list[str] = []

    for module_name in sorted(discovered & set(TENANT_ISOLATION_EVIDENCE)):
        evidence_paths = TENANT_ISOLATION_EVIDENCE[module_name]
        if not evidence_paths:
            errors.append(f"{module_name}: no evidence paths registered")
            continue

        executable_evidence = False
        for relative_path in evidence_paths:
            python_files = _evidence_python_files(relative_path)
            if not python_files:
                errors.append(f"{module_name}: missing pytest evidence at {relative_path}")
                continue

            for python_file in python_files:
                source = python_file.read_text(encoding="utf-8").lower()
                if "def test_" not in source:
                    continue
                has_org_context = (
                    "organization_id" in source
                    or "x-organization-id" in source
                    or "organization-id" in source
                )
                has_negative_boundary = any(
                    marker in source
                    for marker in (
                        "foreign",
                        "cross_org",
                        "cross-organization",
                        "other_org",
                        "other_organization",
                    )
                )
                if has_org_context and has_negative_boundary:
                    executable_evidence = True
                    break
            if executable_evidence:
                break

        if not executable_evidence:
            errors.append(
                f"{module_name}: evidence exists but no executable ABC/XYZ-style "
                "negative organization-boundary test was detected"
            )

    assert not errors, "Tenant-isolation evidence errors:\n - " + "\n - ".join(errors)


def test_tenant_scope_exclusions_have_durable_reasons() -> None:
    invalid = {
        module_name: reason
        for module_name, reason in TENANT_SCOPE_EXCLUSIONS.items()
        if len(reason.strip()) < 30
    }
    assert not invalid, (
        "Tenant-scope exclusions require a durable architectural reason; invalid "
        f"entries: {sorted(invalid)}"
    )