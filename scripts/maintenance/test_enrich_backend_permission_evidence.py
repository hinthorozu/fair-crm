#!/usr/bin/env python3

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from enrich_backend_permission_evidence import enrich_backend_permission_evidence


class EnrichBackendPermissionEvidenceTests(unittest.TestCase):
    def _base_data(self, route_path: str, dependency: str) -> dict:
        return {
            "backend_routes": [
                {
                    "file": route_path,
                    "function": "route",
                    "method": "GET",
                    "match_path": "/api/v1/example",
                    "permission_codes": [],
                    "permission_evidence": "unknown",
                    "dependencies": [
                        {
                            "parameter": "auth",
                            "dependency": dependency,
                            "annotation": "AuthContext",
                        }
                    ],
                }
            ],
            "links": [],
        }

    def test_follows_permission_constant_imported_by_dependency_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "backend/app/modules/example/api").mkdir(parents=True)
            (root / "backend/app/modules/example/application").mkdir(parents=True)

            (root / "backend/app/modules/example/application/service.py").write_text(
                'PERMISSION_READ = "fair_crm.customers.read"\n',
                encoding="utf-8",
            )
            (root / "backend/app/modules/example/api/dependencies.py").write_text(
                textwrap.dedent(
                    """
                    from app.modules.example.application.service import PERMISSION_READ as READ_PERMISSION

                    def require_read_permission():
                        return check_permission(permission_code=READ_PERMISSION)
                    """
                ),
                encoding="utf-8",
            )
            route_path = "backend/app/modules/example/api/routes.py"
            (root / route_path).write_text("def route():\n    return None\n", encoding="utf-8")

            data = self._base_data(route_path, "require_read_permission")
            enrich_backend_permission_evidence(root, data)
            route = data["backend_routes"][0]
            self.assertEqual(route["permission_codes"], ["fair_crm.customers.read"])
            self.assertEqual(route["permission_evidence"], "dependency_provider_import_chain")
            self.assertEqual(route["permission_provider_evidence"], ["require_read_permission"])

    def test_follows_assigned_permission_factory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "backend/app/modules/example/api").mkdir(parents=True)
            route_path = "backend/app/modules/example/api/routes.py"
            (root / route_path).write_text("def route():\n    return None\n", encoding="utf-8")
            (root / "backend/app/modules/example/api/dependencies.py").write_text(
                textwrap.dedent(
                    """
                    PERMISSION_READ = "fair_crm.quote_templates.read"

                    def _require(permission_code):
                        return permission_code

                    require_read_permission = _require(PERMISSION_READ)
                    """
                ),
                encoding="utf-8",
            )

            data = self._base_data(route_path, "require_read_permission")
            enrich_backend_permission_evidence(root, data)
            route = data["backend_routes"][0]
            self.assertEqual(route["permission_codes"], ["fair_crm.quote_templates.read"])
            self.assertEqual(route["permission_provider_evidence"], ["require_read_permission"])


if __name__ == "__main__":
    unittest.main()
