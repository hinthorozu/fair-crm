#!/usr/bin/env python3

from __future__ import annotations

import ast
import tempfile
import textwrap
import unittest
from pathlib import Path

import refine_system_behavior_inventory as refine


class RefineSystemBehaviorInventoryTests(unittest.TestCase):
    def test_template_path_resolves_constants_params_and_query_suffix(self) -> None:
        constants = {"BASE": "/api/v1/items"}
        path, target, evidence = refine.eval_path_expression(
            "`${BASE}/${encodeURIComponent(id)}/logs${query ? `?${query}` : \"\"}`",
            constants,
        )
        self.assertEqual(path, "/api/v1/items/{param}/logs")
        self.assertEqual(target, "fair-crm")
        self.assertEqual(evidence, "template")
        self.assertEqual(refine.normalize_match_path(path), "/api/v1/items/{}/logs")

    def test_core_transport_is_classified_separately(self) -> None:
        path, target, _ = refine.eval_path_expression(
            "`${config.coreBaseUrl}/api/v1${path}`",
            {},
        )
        self.assertEqual(target, "kyrox-core")
        self.assertEqual(path, "/api/v1{param}")

    def test_nested_permission_factory_is_resolved(self) -> None:
        tree = ast.parse(
            textwrap.dedent(
                """
                def route(auth = Depends(require_permission(CATEGORY_VIEW))):
                    return auth
                """
            )
        )
        fn = tree.body[0]
        permissions = refine.nested_dependency_permissions(
            fn,
            {"CATEGORY_VIEW": "fair_crm.cost_catalog.categories.read"},
        )
        self.assertEqual(permissions, {"fair_crm.cost_catalog.categories.read"})

    def test_scope_follows_local_helper(self) -> None:
        tree = ast.parse(
            textwrap.dedent(
                """
                def _command(auth):
                    return dict(organization_id=auth.organization_id)

                def route(auth):
                    return _command(auth)
                """
            )
        )
        functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        self.assertEqual(
            refine.scope_via_local_helpers(functions["route"], functions),
            "local_helper:_command",
        )

    def test_rebuild_does_not_require_permission_for_uncontracted_public_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".kyrox/features").mkdir(parents=True)
            (root / "backend/app/modules/auth/api").mkdir(parents=True)
            route_file = root / "backend/app/modules/auth/api/routes.py"
            route_file.write_text(
                "def login():\n    return None\n",
                encoding="utf-8",
            )
            raw = {
                "stats": {},
                "backend_routes": [
                    {
                        "method": "POST",
                        "path": "/api/v1/auth/login",
                        "match_path": "/api/v1/auth/login",
                        "file": "backend/app/modules/auth/api/routes.py",
                        "function": "login",
                        "permission_codes": [],
                        "contract_permission_codes": [],
                        "feature_contracts": [],
                        "organization_scope_evidence": "unknown",
                    }
                ],
                "frontend_api_calls": [],
            }
            result = refine.rebuild(root, raw)
            categories = {item["category"] for item in result["findings"]}
            self.assertNotIn("backend_permission_evidence_unknown", categories)


if __name__ == "__main__":
    unittest.main()
