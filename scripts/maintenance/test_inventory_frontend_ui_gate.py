#!/usr/bin/env python3
"""Semantic checks for the absolute UI gate. These do not widen allowlists."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import inventory_frontend_ui as ui


class FormActionsModalScopeTests(unittest.TestCase):
    def test_preview_and_table_actions_outside_a_modal_are_not_modal_chrome(self) -> None:
        text = """
        <div className="form-actions"><h3>Önizleme</h3></div>
        <div className="form-actions" role="tablist"></div>
        <FormModal title="Edit">
          <div className="form-actions"></div>
        </FormModal>
        """
        preview = text.index('className="form-actions"><h3>')
        tabs = text.index('role="tablist"')
        inside = text.index('className="form-actions"></div>')
        self.assertFalse(ui.form_actions_inside_open_modal(text, preview))
        self.assertFalse(ui.form_actions_inside_open_modal(text, tabs))
        self.assertTrue(ui.form_actions_inside_open_modal(text, inside))

    def test_closed_modal_does_not_keep_later_actions_inside(self) -> None:
        text = "<Modal title=\"A\"></Modal><div className=\"form-actions\"></div>"
        pos = text.index("form-actions")
        self.assertFalse(ui.form_actions_inside_open_modal(text, pos))


class PageShellDelegationTests(unittest.TestCase):
    def test_wrapper_that_renders_a_shelled_page_counts_as_shelled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            child = root / "CustomerEnrichmentPage.tsx"
            child.write_text("export function CustomerEnrichmentPage(){ return <PageShell />; }\n", encoding="utf-8")
            wrapper = root / "EnrichmentOperationPage.tsx"
            wrapper.write_text(
                'import { CustomerEnrichmentPage } from "./CustomerEnrichmentPage";\n'
                "export function EnrichmentOperationPage(){ return <CustomerEnrichmentPage />; }\n",
                encoding="utf-8",
            )
            text = wrapper.read_text(encoding="utf-8")
            self.assertTrue(ui.delegates_pageshell(wrapper, text))

    def test_page_without_shell_or_delegate_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "BarePage.tsx"
            page.write_text("export function BarePage(){ return <main />; }\n", encoding="utf-8")
            self.assertFalse(ui.delegates_pageshell(page, page.read_text(encoding="utf-8")))


class MountedPageTests(unittest.TestCase):
    def test_admin_and_enrichment_pages_are_mounted_through_their_hosts(self) -> None:
        mounted = set(ui.collect_mounted_page_components())
        self.assertIn("UsersAdminPage", mounted)
        self.assertIn("RoleManagementPage", mounted)
        self.assertIn("CostCatalogPage", mounted)
        self.assertIn("CustomerEnrichmentPage", mounted)
        self.assertIn("EnrichmentOperationPage", mounted)
        self.assertIn("OperationDetailPage", mounted)


if __name__ == "__main__":
    unittest.main()
