#!/usr/bin/env python3

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

import inventory_system_behavior as inventory
from test_enrich_backend_permission_evidence import EnrichBackendPermissionEvidenceTests  # noqa: F401
from test_refine_system_behavior_inventory import RefineSystemBehaviorInventoryTests  # noqa: F401


class SystemBehaviorInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "backend/app/api/v1").mkdir(parents=True)
        (self.root / "backend/app/modules/customers/api").mkdir(parents=True)
        (self.root / "frontend/src/api").mkdir(parents=True)
        (self.root / "frontend/src/pages").mkdir(parents=True)
        (self.root / ".kyrox/features").mkdir(parents=True)

        (self.root / "backend/app/api/v1/router.py").write_text(
            textwrap.dedent(
                """
                from fastapi import APIRouter
                from app.modules.customers.api.routes import router as customers_router

                api_v1_router = APIRouter(prefix="/api/v1")
                api_v1_router.include_router(customers_router)
                """
            ),
            encoding="utf-8",
        )
        (self.root / "backend/app/modules/customers/api/dependencies.py").write_text(
            textwrap.dedent(
                """
                PERMISSION_READ = "fair_crm.customers.read"

                def _require_permission(*, permission_code):
                    return permission_code

                def require_read_permission():
                    return _require_permission(permission_code=PERMISSION_READ)
                """
            ),
            encoding="utf-8",
        )
        (self.root / "backend/app/modules/customers/api/routes.py").write_text(
            textwrap.dedent(
                """
                from fastapi import APIRouter, Depends
                from .dependencies import require_read_permission

                router = APIRouter(prefix="/customers")

                @router.get("")
                def list_customers(auth=Depends(require_read_permission)):
                    query = dict(organization_id=auth.organization_id)
                    return query
                """
            ),
            encoding="utf-8",
        )
        (self.root / "frontend/src/api/customers.ts").write_text(
            textwrap.dedent(
                """
                import { apiRequest } from "./client";

                export async function listCustomers() {
                  return apiRequest(`/api/v1/customers`);
                }
                """
            ),
            encoding="utf-8",
        )
        (self.root / "frontend/src/pages/CustomersPage.tsx").write_text(
            textwrap.dedent(
                """
                import { listCustomers } from "../api/customers";

                export function CustomersPage() {
                  const load = () => listCustomers();
                  return <button onClick={load}>Load</button>;
                }
                """
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_links_frontend_to_backend_with_permission_and_org_scope(self) -> None:
        result = inventory.build_inventory(self.root)

        self.assertEqual(result["stats"]["backend_routes"], 1)
        self.assertEqual(result["stats"]["frontend_api_calls"], 1)
        self.assertEqual(result["stats"]["frontend_backend_links"], 1)
        self.assertEqual(result["findings"], [])

        route = result["backend_routes"][0]
        self.assertEqual(route["path"], "/api/v1/customers")
        self.assertEqual(route["permission_codes"], ["fair_crm.customers.read"])
        self.assertEqual(route["organization_scope_evidence"], "auth.organization_id")

        call = result["frontend_api_calls"][0]
        self.assertTrue(any(ref["kind"] == "call" for ref in call["ui_references"]))

    def test_missing_backend_route_is_a_regression_finding(self) -> None:
        (self.root / "frontend/src/api/missing.ts").write_text(
            textwrap.dedent(
                """
                import { apiRequest } from "./client";

                export async function createMissing() {
                  return apiRequest(`/api/v1/missing`, { method: "POST" });
                }
                """
            ),
            encoding="utf-8",
        )

        result = inventory.build_inventory(self.root)
        categories = {item["category"] for item in result["findings"]}
        self.assertIn("frontend_api_without_backend_route", categories)

    def test_nested_typescript_generic_and_method_are_parsed(self) -> None:
        text = """
        export async function load() {
          return apiRequest<StandardListResponse<Customer>>(`/api/v1/customers`);
        }
        export async function create() {
          return apiRequest(`/api/v1/customers`, { method: "POST" });
        }
        """
        (self.root / "frontend/src/api/customers.ts").write_text(text, encoding="utf-8")

        calls = inventory.frontend_api_calls(self.root)
        self.assertEqual([(call["function"], call["method"]) for call in calls], [("create", "POST"), ("load", "GET")])


if __name__ == "__main__":
    unittest.main()
