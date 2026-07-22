"""Full FAIR CRM frontend UI inventory + CI gate enforcement.

Scans frontend/src for shared vs local/non-standard UI usage.
Writes JSON + Markdown under scripts/maintenance/reports/.

CI / local gate commands (from repo root):

  python scripts/maintenance/inventory_frontend_ui.py --gate P0
  python scripts/maintenance/inventory_frontend_ui.py --gate P1
  python scripts/maintenance/inventory_frontend_ui.py --gate P2
  python scripts/maintenance/inventory_frontend_ui.py --gate P3
  python scripts/maintenance/inventory_frontend_ui.py --gate FINAL
  python scripts/maintenance/inventory_frontend_ui.py --gate ALL

Exit code 0 = gate PASS; non-zero = FAIL. See PROJECT_CONSTITUTION.md
and docs/frontend/UI_DESIGN_SYSTEM.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"
APP_TSX = SRC / "App.tsx"
CAPTURE_EVIDENCE = ROOT / "frontend" / "scripts" / "capture-ui-evidence.mjs"
OUT_DEFAULT = Path(__file__).resolve().parent / "reports" / "frontend-ui-inventory"
OUT = OUT_DEFAULT

SKIP_DIRS = {"node_modules", "dist", "__pycache__"}

# Shared standard primitives (canonical ADR-028 / ADR-032 / form kit)
SHARED = {
    "button": {
        "standard": [".btn", "btn primary", "btn secondary", "btn danger", "btn ghost", "btn link", "btn-primary", "btn-secondary", "btn-danger", "btn-ghost"],
        "component_files": ["Button.tsx"],
        "notes": "Prefer `Button` from `components/ui/Button`. Class-based `.btn` / `.btn-*` remains supported (same tokens).",
    },
    "input": {
        "standard_imports": ["TextInput", "PasswordInput"],
        "standard_from": ["components/ui/form", "ui/form", "FormInputs"],
        "raw_tags": [r"<input\b"],
        "notes": "Shared: TextInput / PasswordInput from ui/form.",
    },
    "textarea": {
        "standard_imports": ["TextareaInput"],
        "standard_from": ["components/ui/form", "ui/form", "FormInputs"],
        "raw_tags": [r"<textarea\b"],
        "notes": "Shared: TextareaInput from ui/form.",
    },
    "select": {
        "standard_imports": ["SelectInput"],
        "standard_from": ["components/ui/form", "ui/form", "FormInputs"],
        "raw_tags": [r"<select\b"],
        "notes": "Shared: SelectInput from ui/form. Domain selects (FairEntitySelect, CustomerEntitySelect, AdapterSelect) are OK wrappers.",
    },
    "checkbox_radio": {
        "standard_imports": ["CheckboxField", "RadioField"],
        "standard_from": ["components/ui/form", "ui/form", "FormInputs"],
        "raw_tags": [r'type=["\']checkbox["\']', r'type=["\']radio["\']'],
        "notes": "Shared: CheckboxField / RadioField only (ADR-032 §4).",
    },
    "form": {
        "standard_imports": [
            "FormGrid",
            "FormField",
            "FormSection",
            "FormActions",
            "FormModal",
        ],
        "standard_from": ["components/ui/form", "ui/form", "FormField", "FormGrid"],
        "notes": "Shared form kit under components/ui/form (+ legacy FormField.tsx re-export).",
    },
    "modal": {
        "standard_imports": ["Modal", "ConfirmDialog", "FormModal", "Drawer"],
        "standard_from": ["components/ui/Modal", "ui/Modal", "ConfirmDialog", "FormModal", "Drawer"],
        "notes": "ADR-028: Modal + ConfirmDialog (+ FormModal/Drawer).",
    },
    "datatable": {
        "standard_imports": [
            "UniversalDataTable",
            "WidthResponsiveDataTable",
            "ServerDataTableFrame",
            "DataTableShell",
        ],
        "deprecated_imports": ["ResponsiveDataTable", "DataTable"],
        "raw_tags": [r"<table\b"],
        "notes": "ADR-032: UniversalDataTable → WidthResponsiveDataTable. DataTableShell scroll-only for specialty grids.",
    },
    "pagination": {
        "standard_imports": ["PaginationBar", "ServerDataTablePagination", "ServerDataTableFrame"],
        "standard_from": ["Pagination", "ServerDataTableFrame", "ServerDataTablePagination"],
        "notes": "PaginationBar + ServerDataTableFrame dual pagination.",
    },
    "filter_toolbar": {
        "standard_imports": ["FilterPanel"],
        "standard_from": ["FilterPanel"],
        "class_hooks": [r'className=["\'][^"\']*\bfilters\b', r'className=["\'][^"\']*\bfilter-panel\b'],
        "notes": "Shared: FilterPanel. Local `.filters` toolbars are non-standard if not FilterPanel.",
    },
    "card": {
        "standard_imports": ["Card"],
        "standard_from": ["components/ui/Card", "ui/Card"],
        "class_hooks": [],
        "notes": "Shared Card component only. Bare class token `card` on raw elements is a P1 violation.",
    },
    "page_header": {
        "standard_imports": ["PageHeader", "SectionHeader"],
        "standard_from": ["PageHeader", "SectionHeader"],
        "notes": "PageHeader for pages; SectionHeader for nested sections.",
    },
    "layout_shell": {
        "standard_imports": [
            "AppLayout",
            "AdminSystemLayout",
            "DataIntegrationLayout",
            "Breadcrumb",
            "UserMenu",
            "SidebarCollapseButton",
        ],
        "notes": "App shell + nested Admin/DI layouts.",
    },
    "alert_toast": {
        "standard_imports": ["Banner"],
        "standard_from": ["components/ui/Banner", "ui/Banner"],
        "class_hooks": [],
        "notes": "Shared Banner (success/warning/error/info). No parallel toast system. Field-level `.form-error` stays with FormField.",
    },
    "other": {
        "standard_imports": [
            "Tabs",
            "Badge",
            "TruncatedText",
            "TechnicalDetails",
            "EmptyState",
            "LoadingState",
            "DetailWebsite",
        ],
        "notes": "Tabs, Badge, TruncatedText, TechnicalDetails, Empty/Loading states, Detail fields.",
    },
}


@dataclass
class Hit:
    file: str
    line: int
    kind: str  # standard | local | raw | deprecated | class
    snippet: str


@dataclass
class CategoryReport:
    category: str
    standard_infra: str
    total_hits: int = 0
    standard_hits: int = 0
    nonstandard_hits: int = 0
    files_standard: list[str] = field(default_factory=list)
    files_nonstandard: list[str] = field(default_factory=list)
    samples_nonstandard: list[dict] = field(default_factory=list)
    notes: str = ""


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for path in SRC.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in {".tsx", ".ts", ".css"}:
            continue
        # skip tests optionally? include them for completeness but tag
        files.append(path)
    return sorted(files)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def line_no(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def snippet_at(text: str, index: int, width: int = 120) -> str:
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    if end < 0:
        end = min(len(text), index + width)
    line = text[start:end].strip()
    return line[:width]


def file_imports_symbol(text: str, symbol: str) -> bool:
    # import { X } from ... or import X from
    patterns = [
        rf"\bimport\s+\{{[^}}]*\b{re.escape(symbol)}\b[^}}]*\}}",
        rf"\bimport\s+{re.escape(symbol)}\b",
    ]
    return any(re.search(p, text) for p in patterns)


def count_jsx_usage(text: str, symbol: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for m in re.finditer(rf"<{re.escape(symbol)}\b", text):
        hits.append((line_no(text, m.start()), snippet_at(text, m.start())))
    return hits


def count_class_usage(text: str, pattern: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for m in re.finditer(pattern, text):
        hits.append((line_no(text, m.start()), snippet_at(text, m.start())))
    return hits


def is_definition_file(path: Path, symbols: list[str]) -> bool:
    name = path.name
    for s in symbols:
        if s.lower() in name.lower():
            return True
    # ui kit homes
    parts = path.as_posix()
    return "/components/ui/" in parts or parts.endswith("/Pagination.tsx")


def inventory_buttons(files: list[Path]) -> CategoryReport:
    report = CategoryReport(
        category="Button",
        standard_infra="`.btn` / `.btn.primary|secondary|danger|ghost|link` (+ kebab aliases) — no Button component",
        notes=SHARED["button"]["notes"],
    )
    std_files: set[str] = set()
    local_files: set[str] = set()
    samples: list[dict] = []

    btn_re = re.compile(
        r'className=["\'][^"\']*\bbtn\b[^"\']*["\']|className=\{[^}]*\bbtn\b'
    )
    # nonstandard: button without btn class, or custom button-* classes excluding btn
    raw_button = re.compile(r"<button\b")
    has_btn_class = re.compile(r"\bbtn\b")

    for path in files:
        if path.suffix == ".css":
            continue
        text = path.read_text(encoding="utf-8")
        r = rel(path)
        for m in btn_re.finditer(text):
            report.standard_hits += 1
            report.total_hits += 1
            std_files.add(r)
        # raw <button> lines
        for m in raw_button.finditer(text):
            snip = snippet_at(text, m.start(), 200)
            # skip if same line / nearby has btn
            line = snip
            report.total_hits += 1
            if has_btn_class.search(line) or "btn" in line:
                report.standard_hits += 1
                std_files.add(r)
            else:
                # might be icon-only / sidebar without btn — flag as local
                report.nonstandard_hits += 1
                local_files.add(r)
                if len(samples) < 25:
                    samples.append({"file": r, "line": line_no(text, m.start()), "snippet": snip})

    report.files_standard = sorted(std_files)
    report.files_nonstandard = sorted(local_files)
    report.samples_nonstandard = samples
    return report


def inventory_import_category(
    category: str,
    standard_infra: str,
    notes: str,
    files: list[Path],
    standard_imports: list[str],
    raw_patterns: list[str] | None = None,
    class_patterns: list[str] | None = None,
    deprecated: list[str] | None = None,
    allow_raw_in_definition: bool = True,
) -> CategoryReport:
    report = CategoryReport(category=category, standard_infra=standard_infra, notes=notes)
    std_files: set[str] = set()
    local_files: set[str] = set()
    samples: list[dict] = []
    deprecated = deprecated or []

    for path in files:
        if path.suffix == ".css":
            continue
        text = path.read_text(encoding="utf-8")
        r = rel(path)
        is_def = is_definition_file(path, standard_imports + deprecated)

        for sym in standard_imports:
            usages = count_jsx_usage(text, sym)
            if usages or file_imports_symbol(text, sym):
                if usages:
                    for ln, snip in usages:
                        report.standard_hits += 1
                        report.total_hits += 1
                        std_files.add(r)
                elif file_imports_symbol(text, sym) and not is_def:
                    # imported but maybe re-exported — count lightly
                    pass

        for sym in deprecated:
            usages = count_jsx_usage(text, sym)
            for ln, snip in usages:
                report.nonstandard_hits += 1
                report.total_hits += 1
                local_files.add(r)
                if len(samples) < 30:
                    samples.append(
                        {
                            "file": r,
                            "line": ln,
                            "snippet": snip,
                            "reason": f"deprecated:{sym}",
                        }
                    )

        if raw_patterns:
            for pat in raw_patterns:
                for m in re.finditer(pat, text, flags=re.IGNORECASE):
                    if is_def and allow_raw_in_definition:
                        # still count as infra, not local
                        continue
                    # if file already uses standard component for same concern, raw may be specialty
                    snip = snippet_at(text, m.start(), 160)
                    # skip comments
                    if snip.startswith("//") or snip.startswith("*"):
                        continue
                    report.nonstandard_hits += 1
                    report.total_hits += 1
                    local_files.add(r)
                    if len(samples) < 40:
                        samples.append(
                            {
                                "file": r,
                                "line": line_no(text, m.start()),
                                "snippet": snip,
                                "reason": f"raw:{pat}",
                            }
                        )

        if class_patterns:
            for pat in class_patterns:
                for ln, snip in count_class_usage(text, pat):
                    # If FilterPanel used in same file, class filters may be nested OK
                    uses_filter_panel = "FilterPanel" in text and category == "Filter / Toolbar"
                    if uses_filter_panel and "filters" in snip:
                        report.standard_hits += 1
                        report.total_hits += 1
                        std_files.add(r)
                        continue
                    report.nonstandard_hits += 1
                    report.total_hits += 1
                    local_files.add(r)
                    if len(samples) < 40:
                        samples.append(
                            {
                                "file": r,
                                "line": ln,
                                "snippet": snip,
                                "reason": f"class:{pat}",
                            }
                        )

    report.files_standard = sorted(std_files)
    # Purely nonstandard files (exclude files that also have standard usage in this category)
    report.files_nonstandard = sorted(local_files - std_files)
    report.samples_nonstandard = samples
    return report


@dataclass(frozen=True)
class AllowlistEntry:
    """Specialty exception. 'specialty' alone is never a valid reason."""

    file: str
    pattern: str
    reason: str
    owner: str


# Specialty / intentional exceptions — documented in docs/frontend/UI_INVENTORY_ALLOWLIST.md
P0_RAW_ALLOWLIST_ENTRIES: list[AllowlistEntry] = [
    AllowlistEntry(
        "frontend/src/components/ui/form/FormInputs.tsx",
        "raw <input|select|textarea|checkbox|radio>",
        "Shared form-kit definition; primitives wrap native controls.",
        "ui/form kit",
    ),
    AllowlistEntry(
        "frontend/src/components/imports/ExcelMappingGrid.tsx",
        "raw <select> in mapping grid",
        "Dense Excel mapping specialty requires native selects inside scroll-only grid; generic SelectInput breaks cell density.",
        "import mapping specialty",
    ),
    AllowlistEntry(
        "frontend/src/components/FairEntitySelect.tsx",
        "raw combobox input chrome",
        "Domain async combobox; wraps search input + listbox pattern not covered by SelectInput.",
        "domain select wrappers",
    ),
    AllowlistEntry(
        "frontend/src/components/CustomerEntitySelect.tsx",
        "raw combobox input chrome",
        "Domain async combobox; wraps search input + listbox pattern not covered by SelectInput.",
        "domain select wrappers",
    ),
    AllowlistEntry(
        "frontend/src/components/AdapterSelect.tsx",
        "raw combobox input chrome",
        "Domain async combobox; wraps search input + listbox pattern not covered by SelectInput.",
        "domain select wrappers",
    ),
]
P0_RAW_ALLOWLIST = {e.file for e in P0_RAW_ALLOWLIST_ENTRIES}


def compute_p0_violations(ts_files: list[Path]) -> dict:
    """P0: FilterPanel-less local filters + bare checkbox/radio + raw filter/form controls.

    Specialty Import mapping table selects and ExcelMappingGrid are excluded.
    """
    bare_cb_radio: list[dict] = []
    local_filters: list[dict] = []
    raw_form_controls: list[dict] = []

    filters_class_re = re.compile(r'className=["\'][^"\']*\bfilters\b')
    bare_cb_re = re.compile(r'type=["\']checkbox["\']', re.I)
    bare_radio_re = re.compile(r'type=["\']radio["\']', re.I)
    raw_tag_re = re.compile(r"<(input|select|textarea)\b")

    for path in ts_files:
        text = path.read_text(encoding="utf-8")
        r = rel(path)
        if r in P0_RAW_ALLOWLIST:
            continue

        # 1) Bare checkbox/radio outside form kit definition
        if "FormInputs.tsx" not in r:
            for pat, kind in ((bare_cb_re, "checkbox"), (bare_radio_re, "radio")):
                for m in pat.finditer(text):
                    bare_cb_radio.append(
                        {
                            "file": r,
                            "line": line_no(text, m.start()),
                            "kind": kind,
                            "snippet": snippet_at(text, m.start()),
                        }
                    )

        # 2) className …filters without FilterPanel in the same file
        uses_filter_panel = file_imports_symbol(text, "FilterPanel") or "<FilterPanel" in text
        for m in filters_class_re.finditer(text):
            snip = snippet_at(text, m.start())
            if uses_filter_panel:
                continue
            # skip filter-panel itself
            if "filter-panel" in snip:
                continue
            local_filters.append(
                {
                    "file": r,
                    "line": line_no(text, m.start()),
                    "snippet": snip,
                }
            )

        # 3) Raw input/select/textarea in consumer files (specialty mapping table allowed in ImportWizard)
        for m in raw_tag_re.finditer(text):
            ln = line_no(text, m.start())
            snip = snippet_at(text, m.start(), 200)
            # Import Wizard specialty: mapping-table source column selects (scroll-only exception)
            if "ImportWizardPage.tsx" in r:
                lines = text.splitlines()
                window = "\n".join(lines[max(0, ln - 40) : min(len(lines), ln + 15)])
                if m.group(1) == "select" and (
                    "mapping-table" in window
                    or "MAPPING_FIELDS" in window
                    or "mappingCrmField" in window
                    or "noMapping" in window
                ):
                    continue
                if "ExcelMappingGrid" in window:
                    continue
            raw_form_controls.append(
                {
                    "file": r,
                    "line": ln,
                    "tag": m.group(1),
                    "snippet": snip,
                }
            )

    total = len(bare_cb_radio) + len(local_filters) + len(raw_form_controls)
    return {
        "total_violations": total,
        "bare_checkbox_radio": bare_cb_radio,
        "local_filters_without_filter_panel": local_filters,
        "raw_form_controls": raw_form_controls,
        "allowlist": sorted(P0_RAW_ALLOWLIST),
        "pass": total == 0,
    }


P1_ALERT_ALLOWLIST_ENTRIES: list[AllowlistEntry] = [
    AllowlistEntry(
        "frontend/src/components/ui/Banner.tsx",
        "class token banner",
        "Shared Banner definition applies the canonical banner class.",
        "ui/Banner kit",
    ),
]
P1_CARD_ALLOWLIST_ENTRIES: list[AllowlistEntry] = [
    AllowlistEntry(
        "frontend/src/components/ui/Card.tsx",
        "class token card",
        "Shared Card definition applies the canonical card class.",
        "ui/Card kit",
    ),
]
P1_ALERT_ALLOWLIST = {e.file for e in P1_ALERT_ALLOWLIST_ENTRIES}
P1_CARD_ALLOWLIST = {e.file for e in P1_CARD_ALLOWLIST_ENTRIES}

CLASSNAME_ATTR_RE = re.compile(r'className=(["\'])([^"\']*)\1|className=\{`([^`]*)`\}')


def _class_tokens(class_str: str) -> set[str]:
    return {t for t in re.split(r"\s+", class_str.strip()) if t}


def compute_p1_violations(ts_files: list[Path]) -> dict:
    """P1: bare Banner/Toast classes + bare Card class token outside shared components."""
    bare_alerts: list[dict] = []
    bare_cards: list[dict] = []
    intentional: list[dict] = []

    alert_tokens = {"banner", "toast", "import-toast"}
    # Compound layout names that contain 'banner' as suffix but are not notification banners
    non_alert_compounds = {
        "restore-job-polling-banner",
        "import-complete-banner",
        "duplicate-group-summary-banner",  # modifier used WITH Banner component
    }

    for path in ts_files:
        text = path.read_text(encoding="utf-8")
        r = rel(path)

        for m in CLASSNAME_ATTR_RE.finditer(text):
            cls = m.group(2) or m.group(3) or ""
            tokens = _class_tokens(cls)
            ln = line_no(text, m.start())
            snip = snippet_at(text, m.start(), 160)

            # Alert / toast bare tokens
            if r not in P1_ALERT_ALLOWLIST:
                hit_alert = tokens & alert_tokens
                # compound-only (no bare banner/toast token) → intentional specialty layout
                compound_hits = tokens & non_alert_compounds
                if compound_hits and not hit_alert:
                    # Modifier on <Banner> is fine; only report raw specialty layout wrappers
                    lines = text.splitlines()
                    window = "\n".join(lines[max(0, ln - 4) : min(len(lines), ln + 1)])
                    if "<Banner" not in window:
                        intentional.append(
                            {
                                "file": r,
                                "line": ln,
                                "kind": "specialty_banner_layout",
                                "snippet": snip,
                            }
                        )
                elif hit_alert:
                    bare_alerts.append(
                        {
                            "file": r,
                            "line": ln,
                            "tokens": sorted(hit_alert),
                            "snippet": snip,
                        }
                    )

            # Bare card token
            if r not in P1_CARD_ALLOWLIST and "card" in tokens:
                bare_cards.append(
                    {
                        "file": r,
                        "line": ln,
                        "snippet": snip,
                    }
                )

    total = len(bare_alerts) + len(bare_cards)
    return {
        "total_violations": total,
        "bare_alert_toast": bare_alerts,
        "bare_card": bare_cards,
        "intentional_exceptions": intentional,
        "allowlist_alert": sorted(P1_ALERT_ALLOWLIST),
        "allowlist_card": sorted(P1_CARD_ALLOWLIST),
        "pass": total == 0,
    }


P2_DEFINITION_FILES = {
    "FieldError.tsx",
    "TableEntityLink.tsx",
    "TableRowActions.tsx",
    "EmptyState.tsx",
    "LoadingState.tsx",
    "FormInputs.tsx",
}


def compute_p2_violations(ts_files: list[Path]) -> dict:
    """P2: legacy form-error/link-button, ad-hoc empty/loading, bare action wrappers."""
    form_errors: list[dict] = []
    link_buttons: list[dict] = []
    adhoc_empty: list[dict] = []
    adhoc_loading: list[dict] = []
    bare_action_wrappers: list[dict] = []
    intentional: list[dict] = []

    form_error_re = re.compile(r'className=(["\'])([^"\']*\bform-error\b[^"\']*)\1')
    link_button_re = re.compile(r'className=(["\'])([^"\']*\blink-button\b[^"\']*)\1')
    adhoc_empty_re = re.compile(
        r'emptyState=\{\s*<p\s+className=["\']text-muted["\']',
        re.M,
    )
    adhoc_loading_re = re.compile(
        r'<p\s+className=["\']text-muted["\']>\s*Yükleniyor',
        re.M,
    )
    bare_actions_re = re.compile(
        r'<div\s+className=["\'](?:table-actions|[\w-]*list-actions)(?:\s[^"\']*)?["\']',
        re.M,
    )

    for path in ts_files:
        if path.name in P2_DEFINITION_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        r = rel(path)

        for m in form_error_re.finditer(text):
            form_errors.append(
                {"file": r, "line": line_no(text, m.start()), "snippet": snippet_at(text, m.start())}
            )
        for m in link_button_re.finditer(text):
            link_buttons.append(
                {"file": r, "line": line_no(text, m.start()), "snippet": snippet_at(text, m.start())}
            )
        for m in adhoc_empty_re.finditer(text):
            adhoc_empty.append(
                {"file": r, "line": line_no(text, m.start()), "snippet": snippet_at(text, m.start())}
            )
        for m in adhoc_loading_re.finditer(text):
            # Specialty combobox messages are usually not <p className="text-muted">
            adhoc_loading.append(
                {"file": r, "line": line_no(text, m.start()), "snippet": snippet_at(text, m.start())}
            )
        for m in bare_actions_re.finditer(text):
            bare_action_wrappers.append(
                {"file": r, "line": line_no(text, m.start()), "snippet": snippet_at(text, m.start())}
            )

    # Intentional specialty: entity select loading chrome (not page LoadingState)
    for path in ts_files:
        r = rel(path)
        if path.name in {"FairEntitySelect.tsx", "CustomerEntitySelect.tsx", "AdapterSelect.tsx"}:
            intentional.append(
                {
                    "file": r,
                    "line": 0,
                    "kind": "domain_combobox_loading",
                    "snippet": "inline combobox loading text (not page LoadingState)",
                }
            )

    total = (
        len(form_errors)
        + len(link_buttons)
        + len(adhoc_empty)
        + len(adhoc_loading)
        + len(bare_action_wrappers)
    )
    return {
        "total_violations": total,
        "bare_form_error": form_errors,
        "link_button": link_buttons,
        "adhoc_empty": adhoc_empty,
        "adhoc_loading": adhoc_loading,
        "bare_action_wrappers": bare_action_wrappers,
        "intentional_exceptions": intentional,
        "pass": total == 0,
    }


P3_DEFINITION_FILES = {
    "IconButton.tsx",
    "NavLink.tsx",
    "PageShell.tsx",
    "SidebarCollapseButton.tsx",
}

P3_PAGE_ALLOWLIST_ENTRIES: list[AllowlistEntry] = [
    AllowlistEntry(
        "frontend/src/pages/LoginPage.tsx",
        "PageShell missing",
        "Auth brand shell is outside AppLayout; PageShell is for in-app pages only.",
        "auth shell specialty",
    ),
]
P3_PAGE_ALLOWLIST = {Path(e.file).name for e in P3_PAGE_ALLOWLIST_ENTRIES}

P3_REQUIRED_NAVLINK_LAYOUTS = {
    "AppLayout.tsx",
    "AdminSystemLayout.tsx",
    "DataIntegrationLayout.tsx",
}


def compute_p3_violations(ts_files: list[Path]) -> dict:
    """P3: shell/chrome — IconButton, NavLink, PageShell, login Banner."""
    bare_icon_buttons: list[dict] = []
    login_form_errors: list[dict] = []
    bare_nav_links: list[dict] = []
    missing_pageshell: list[dict] = []
    missing_navlink: list[dict] = []
    intentional: list[dict] = []

    icon_class_re = re.compile(
        r'className=(["\'])([^"\']*\b(?:btn icon|kebab-menu-btn|password-input__toggle|table-expand-btn)\b[^"\']*)\1'
    )
    login_err_re = re.compile(r'login-form-error')
    nav_class_re = re.compile(
        r'className=(["\'`])([^"\'`]*\b(?:sidebar-link|di-subnav-link|admin-subnav-link)\b[^"\'`]*)\1'
    )

    for path in ts_files:
        text = path.read_text(encoding="utf-8")
        r = rel(path)

        if path.name in P3_DEFINITION_FILES:
            continue

        for m in login_err_re.finditer(text):
            login_form_errors.append(
                {"file": r, "line": line_no(text, m.start()), "snippet": snippet_at(text, m.start())}
            )

        for m in icon_class_re.finditer(text):
            # Decorative span placeholders in table expand chrome are allowed
            snip = snippet_at(text, m.start(), 120)
            if "<span" in text[max(0, m.start() - 80) : m.start()] and "table-expand-btn" in m.group(2):
                intentional.append(
                    {
                        "file": r,
                        "line": line_no(text, m.start()),
                        "kind": "table_expand_placeholder_span",
                        "snippet": snip,
                    }
                )
                continue
            bare_icon_buttons.append(
                {"file": r, "line": line_no(text, m.start()), "snippet": snip}
            )

        if path.name != "NavLink.tsx":
            for m in nav_class_re.finditer(text):
                bare_nav_links.append(
                    {
                        "file": r,
                        "line": line_no(text, m.start()),
                        "snippet": snippet_at(text, m.start()),
                    }
                )

        if path.name in P3_REQUIRED_NAVLINK_LAYOUTS and "NavLink" not in text:
            missing_navlink.append(
                {
                    "file": r,
                    "line": 0,
                    "snippet": "layout missing NavLink import/usage",
                }
            )

        if "/pages/" in r.replace("\\", "/") and path.name not in P3_PAGE_ALLOWLIST:
            if "PageShell" not in text:
                missing_pageshell.append(
                    {
                        "file": r,
                        "line": 0,
                        "snippet": "page missing PageShell",
                    }
                )

    intentional.append(
        {
            "file": "frontend/src/components/mail_templates/MailTemplateActionsMenu.tsx",
            "line": 0,
            "kind": "labeled_actions_menu",
            "snippet": "text trigger (not icon kebab) — intentional",
        }
    )
    intentional.append(
        {
            "file": "frontend/src/pages/LoginPage.tsx",
            "line": 0,
            "kind": "auth_shell",
            "snippet": "login brand shell outside AppLayout/PageShell — intentional",
        }
    )

    total = (
        len(bare_icon_buttons)
        + len(login_form_errors)
        + len(bare_nav_links)
        + len(missing_pageshell)
        + len(missing_navlink)
    )
    return {
        "total_violations": total,
        "bare_icon_buttons": bare_icon_buttons,
        "login_form_error": login_form_errors,
        "bare_nav_links": bare_nav_links,
        "missing_pageshell": missing_pageshell,
        "missing_navlink_layouts": missing_navlink,
        "intentional_exceptions": intentional,
        "pass": total == 0,
    }


FINAL_FIELD_ERROR_ALLOWLIST = {
    "FieldError.tsx",
    "FormField.tsx",
}

FINAL_FORM_ACTIONS_IN_MODAL_ALLOWLIST = {
    # Multi-action in-form wizards / panels (submit stays with form document flow)
    "FairBulkEmailWizard.tsx",
    "MailTemplateTestEmailPanel.tsx",
    "TodoWorklistActivityModal.tsx",
    "ManualTaskMailModal.tsx",
    "FormActions.tsx",
}

# Canonical ADR-032 / ADR-034 breakpoint pixel set (max/min-width media queries).
ADR_BREAKPOINTS_PX = {767, 768, 1023, 1024, 1440}

# Production page files that may exist without being mounted from App.tsx (nested result views).
ROUTE_UNMOUNTED_PAGE_ALLOWLIST = {
    "DataOperationAnalyzeResultPage.tsx",
    "DataOperationDuplicateResultPage.tsx",
    # Nested result/list view mounted from TodosPage tabs, not App.tsx page switch.
    "FollowUpsPage.tsx",
}


def extract_app_routes() -> list[str]:
    """Derive production AppRoute literals from frontend/src/App.tsx (source of truth)."""
    if not APP_TSX.exists():
        return []
    text = APP_TSX.read_text(encoding="utf-8")
    m = re.search(r"type\s+AppRoute\s*=\s*(.*?);", text, flags=re.S)
    if not m:
        return []
    return sorted(set(re.findall(r'["\'](/[^"\']+)["\']', m.group(1))))


def extract_mounted_page_components() -> list[str]:
    """Page components mounted from App.tsx JSX (`<XxxPage`)."""
    if not APP_TSX.exists():
        return []
    text = APP_TSX.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"<([A-Z][A-Za-z0-9]*Page)\b", text)))


def extract_smoke_covered_routes() -> list[str]:
    """Routes referenced in capture-ui-evidence.mjs (responsive smoke catalog)."""
    if not CAPTURE_EVIDENCE.exists():
        return []
    text = CAPTURE_EVIDENCE.read_text(encoding="utf-8")
    # Prefer explicit route: "..." keys; also collect extractAppRoutes() merge marker.
    return sorted(set(re.findall(r'route:\s*["\'](/[^"\']+)["\']', text)))


def inventory_routes(ts_files: list[Path]) -> dict:
    """New-route auto-coverage: AppRoute → mounted page → PageShell → smoke catalog."""
    routes = extract_app_routes()
    mounted = extract_mounted_page_components()
    smoke = set(extract_smoke_covered_routes())
    pages_dir = SRC / "pages"
    page_files = sorted(p.name for p in pages_dir.glob("*Page.tsx")) if pages_dir.exists() else []

    missing_pageshell: list[dict] = []
    unmounted_pages: list[dict] = []
    routes_missing_smoke: list[dict] = []

    page_by_export: dict[str, Path] = {}
    for path in ts_files:
        if "/pages/" not in rel(path).replace("\\", "/"):
            continue
        if not path.name.endswith("Page.tsx"):
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(
            rf"export\s+(?:function|const)\s+({re.escape(path.stem)}|[A-Z][A-Za-z0-9]*Page)\b",
            text,
        ):
            page_by_export[m.group(1)] = path
        # Convention: file name matches component
        page_by_export.setdefault(path.stem, path)

    for name in mounted:
        path = page_by_export.get(name)
        if path is None:
            # May live under pages/ with same stem
            candidate = pages_dir / f"{name}.tsx"
            path = candidate if candidate.exists() else None
        if path is None:
            continue
        if path.name in P3_PAGE_ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8")
        if "PageShell" not in text:
            missing_pageshell.append(
                {
                    "file": rel(path),
                    "line": 0,
                    "route_component": name,
                    "snippet": "mounted production page missing PageShell",
                }
            )

    mounted_files = {f"{n}.tsx" for n in mounted}
    for page_name in page_files:
        if page_name in P3_PAGE_ALLOWLIST or page_name in ROUTE_UNMOUNTED_PAGE_ALLOWLIST:
            continue
        if page_name not in mounted_files:
            # Nested result pages imported by other pages are OK if allowlisted; else flag
            unmounted_pages.append(
                {
                    "file": f"frontend/src/pages/{page_name}",
                    "line": 0,
                    "snippet": "page file not mounted from App.tsx — add route mount or allowlist",
                }
            )

    for route in routes:
        if route in smoke:
            continue
        # capture-ui-evidence auto-merges AppRoute; require either explicit route: key
        # or the AUTO_FROM_APPROUTE marker after we update the script.
        routes_missing_smoke.append(
            {
                "file": rel(CAPTURE_EVIDENCE) if CAPTURE_EVIDENCE.exists() else "frontend/scripts/capture-ui-evidence.mjs",
                "line": 0,
                "route": route,
                "snippet": "AppRoute not present in responsive smoke catalog",
            }
        )

    # If the capture script declares AUTO_FROM_APPROUTE, treat static routes as covered.
    if CAPTURE_EVIDENCE.exists() and "AUTO_FROM_APPROUTE" in CAPTURE_EVIDENCE.read_text(encoding="utf-8"):
        routes_missing_smoke = [
            hit
            for hit in routes_missing_smoke
            if ":" in hit["route"] and hit["route"] not in smoke
        ]

    total = len(missing_pageshell) + len(unmounted_pages) + len(routes_missing_smoke)
    return {
        "app_routes": routes,
        "mounted_page_components": mounted,
        "smoke_covered_routes": sorted(smoke),
        "page_files": page_files,
        "missing_pageshell_on_mounted": missing_pageshell,
        "unmounted_page_files": unmounted_pages,
        "routes_missing_smoke_coverage": routes_missing_smoke,
        "total_violations": total,
        "pass": total == 0,
    }


def compute_final_violations(
    ts_files: list[Path],
    p0: dict,
    p1: dict,
    p2: dict,
    p3: dict,
    route_inv: dict | None = None,
) -> dict:
    """FINAL system gate: residual chrome + tokens + a11y + routes + breakpoints beyond P0–P3."""
    bare_field_error: list[dict] = []
    bare_modal_actions: list[dict] = []
    form_actions_in_modal: list[dict] = []
    legacy_breakpoints: list[dict] = []
    a11y_icon_buttons: list[dict] = []
    intentional: list[dict] = []

    def class_has_token(class_value: str, token: str) -> bool:
        return token in class_value.split()

    field_error_re = re.compile(r'className=(["\'])([^"\']*)\1')
    icon_btn_missing_label_re = re.compile(
        r"<button\b[^>]*className=(['\"])[^'\"]*\bicon\b[^'\"]*\1[^>]*>",
        re.I,
    )
    media_re = re.compile(
        r"@media\s*\((?:max|min)-width:\s*(\d+)px\)",
        re.I,
    )

    for path in ts_files:
        text = path.read_text(encoding="utf-8")
        r = rel(path)

        for m in field_error_re.finditer(text):
            class_value = m.group(2)
            if class_has_token(class_value, "field-error") and path.name not in FINAL_FIELD_ERROR_ALLOWLIST:
                bare_field_error.append(
                    {"file": r, "line": line_no(text, m.start()), "snippet": snippet_at(text, m.start())}
                )
            if class_has_token(class_value, "modal-actions"):
                bare_modal_actions.append(
                    {"file": r, "line": line_no(text, m.start()), "snippet": snippet_at(text, m.start())}
                )

        uses_modal = ("<Modal" in text) or ("<FormModal" in text) or ("ConfirmDialog" in path.name)
        if uses_modal and path.name not in FINAL_FORM_ACTIONS_IN_MODAL_ALLOWLIST:
            for m in field_error_re.finditer(text):
                class_value = m.group(2)
                if not class_has_token(class_value, "form-actions"):
                    continue
                if "modal-footer" in text[max(0, m.start() - 80) : m.start()]:
                    continue
                form_actions_in_modal.append(
                    {"file": r, "line": line_no(text, m.start()), "snippet": snippet_at(text, m.start())}
                )

        if path.name != "IconButton.tsx":
            for m in icon_btn_missing_label_re.finditer(text):
                chunk = text[m.start() : m.start() + 220]
                if "aria-label=" in chunk or "IconButton" in text[max(0, m.start() - 40) : m.start()]:
                    continue
                a11y_icon_buttons.append(
                    {"file": r, "line": line_no(text, m.start()), "snippet": snippet_at(text, m.start())}
                )

    breakpoints_found: set[int] = set()
    for css_path in sorted(SRC.rglob("*.css")):
        if any(part in SKIP_DIRS for part in css_path.parts):
            continue
        css = css_path.read_text(encoding="utf-8")
        for m in media_re.finditer(css):
            px = int(m.group(1))
            breakpoints_found.add(px)
            if px not in ADR_BREAKPOINTS_PX:
                legacy_breakpoints.append(
                    {
                        "file": rel(css_path),
                        "line": line_no(css, m.start()),
                        "snippet": snippet_at(css, m.start(), 80),
                        "px": px,
                    }
                )

    for name in sorted(FINAL_FORM_ACTIONS_IN_MODAL_ALLOWLIST):
        intentional.append(
            {
                "file": f"frontend/src/**/{name}",
                "line": 0,
                "kind": "in_form_modal_actions",
                "snippet": "multi-action form/wizard keeps form-actions in body",
            }
        )

    route_inv = route_inv if route_inv is not None else inventory_routes(ts_files)
    prior_fail = not (p0["pass"] and p1["pass"] and p2["pass"] and p3["pass"])
    route_fail_count = route_inv.get("total_violations", 0)
    total = (
        len(bare_field_error)
        + len(bare_modal_actions)
        + len(form_actions_in_modal)
        + len(legacy_breakpoints)
        + len(a11y_icon_buttons)
        + route_fail_count
        + (1 if prior_fail else 0)
    )
    return {
        "total_violations": total,
        "bare_field_error": bare_field_error,
        "bare_modal_actions": bare_modal_actions,
        "form_actions_in_modal": form_actions_in_modal,
        "legacy_breakpoints": legacy_breakpoints,
        "a11y_icon_buttons_missing_label": a11y_icon_buttons,
        "route_coverage": route_inv,
        "prior_gates_failed": prior_fail,
        "intentional_exceptions": intentional,
        "pass": total == 0,
        "breakpoints_found": sorted(breakpoints_found),
        "allowlist_policy": {
            "p0": [asdict(e) for e in P0_RAW_ALLOWLIST_ENTRIES],
            "p1_alert": [asdict(e) for e in P1_ALERT_ALLOWLIST_ENTRIES],
            "p1_card": [asdict(e) for e in P1_CARD_ALLOWLIST_ENTRIES],
            "p3_pages": [asdict(e) for e in P3_PAGE_ALLOWLIST_ENTRIES],
            "rule": "Allowlist requires file + pattern + reason + owner. 'specialty' alone is invalid.",
        },
    }


def inventory_css_overrides(files: list[Path]) -> dict:
    """Find CSS that fights shared standards."""
    css_path = SRC / "styles.css"
    text = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    patterns = {
        "table_layout_fixed": r"table-layout:\s*fixed",
        "min_width_forced_rem": r"min-width:\s*\d+rem",
        "min_width_forced_px_large": r"min-width:\s*(1[5-9]\d|[2-9]\d\d)px",
        "overflow_x_auto": r"overflow-x:\s*auto",
        "overflow_x_clip": r"overflow-x:\s*clip|overflow:\s*clip",
        "word_break_all": r"word-break:\s*break-all",
        "page_local_table": r"\.(backups-table|duplicate-groups-table|scraper-run-history-table|adapter-runs-table|import-analyze|mapping-table|excel-mapping)",
        "legacy_card_stack": r"table-wrap--cards|display:\s*block;\s*\n\s*width:\s*100%",
        "btn_aliases_ok": r"\.btn-primary|\.btn-secondary",
    }
    findings: dict[str, list[dict]] = {}
    for name, pat in patterns.items():
        hits = []
        for m in re.finditer(pat, text, flags=re.MULTILINE):
            hits.append({"line": line_no(text, m.start()), "snippet": snippet_at(text, m.start(), 140)})
        if hits:
            findings[name] = hits[:40]
            findings[f"{name}_count"] = len(list(re.finditer(pat, text, flags=re.MULTILINE)))  # type: ignore
    return findings


def inventory_component_catalog() -> dict:
    ui_dir = SRC / "components" / "ui"
    catalog = {
        "shared_ui_files": sorted(p.name for p in ui_dir.rglob("*.tsx") if p.is_file()),
        "form_kit": sorted((ui_dir / "form").glob("*.tsx")),
        "layout": sorted((SRC / "components" / "layout").glob("*.tsx")),
        "admin_di_layout": [
            "components/admin/AdminSystemLayout.tsx",
            "components/dataIntegration/DataIntegrationLayout.tsx",
        ],
    }
    catalog["form_kit"] = [p.name for p in catalog["form_kit"]]
    catalog["layout"] = [p.name for p in catalog["layout"]]
    return catalog


def compute_all_gates(ts_files: list[Path]) -> dict:
    p0 = compute_p0_violations(ts_files)
    p1 = compute_p1_violations(ts_files)
    p2 = compute_p2_violations(ts_files)
    p3 = compute_p3_violations(ts_files)
    route_inv = inventory_routes(ts_files)
    p_final = compute_final_violations(ts_files, p0, p1, p2, p3, route_inv)
    return {
        "p0": p0,
        "p1": p1,
        "p2": p2,
        "p3": p3,
        "routes": route_inv,
        "final": p_final,
    }


def gate_passed(gates: dict, name: str) -> bool:
    key = name.lower()
    if key == "all":
        return all(gates[g]["pass"] for g in ("p0", "p1", "p2", "p3", "final"))
    if key == "final":
        return gates["final"]["pass"]
    return gates[key]["pass"]


def print_gate_summary(gates: dict, selected: str) -> None:
    order = ["P0", "P1", "P2", "P3", "FINAL"]
    print("UI GOVERNANCE GATES")
    for name in order:
        key = name.lower()
        g = gates[key]
        status = "PASS" if g["pass"] else "FAIL"
        print(f"  {name}: {status} (violations={g['total_violations']})")
    routes = gates["routes"]
    print(
        f"  ROUTES: {'PASS' if routes['pass'] else 'FAIL'} "
        f"(app_routes={len(routes['app_routes'])}, mounted={len(routes['mounted_page_components'])})"
    )
    if selected.upper() != "ALL":
        ok = gate_passed(gates, selected)
        print(f"Selected gate {selected.upper()}: {'PASS' if ok else 'FAIL'}")


def main(argv: list[str] | None = None) -> int:
    global OUT
    parser = argparse.ArgumentParser(description="FAIR CRM frontend UI inventory + governance gates")
    parser.add_argument(
        "--gate",
        choices=["P0", "P1", "P2", "P3", "FINAL", "ALL"],
        default=None,
        help="Enforce a gate and exit non-zero on FAIL (CI mode).",
    )
    parser.add_argument(
        "--report-dir",
        default=str(OUT_DEFAULT),
        help="Directory for REPORT.md / inventory.json",
    )
    parser.add_argument(
        "--full-report",
        action="store_true",
        help="Always write the full category inventory report (default when --gate omitted).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress long report stdout; still print gate summary.",
    )
    args = parser.parse_args(argv)

    OUT = Path(args.report_dir)
    OUT.mkdir(parents=True, exist_ok=True)
    files = iter_source_files()
    ts_files = [p for p in files if p.suffix in {".ts", ".tsx"}]

    gates = compute_all_gates(ts_files)
    p0, p1, p2, p3, p_final = gates["p0"], gates["p1"], gates["p2"], gates["p3"], gates["final"]
    route_inv = gates["routes"]

    write_full = args.full_report or args.gate is None
    reports: list[CategoryReport] = []
    local_modals: list[str] = []
    css_findings: dict = {}
    catalog: dict = {}
    domain_selects: list[str] = []

    if write_full:
        reports.append(inventory_buttons(ts_files))
        reports.append(
            inventory_import_category(
                "Input / TextBox",
                "TextInput, PasswordInput (`components/ui/form`)",
                SHARED["input"]["notes"],
                ts_files,
                SHARED["input"]["standard_imports"],
                raw_patterns=SHARED["input"]["raw_tags"],
            )
        )
        reports.append(
            inventory_import_category(
                "TextArea",
                "TextareaInput (`components/ui/form`)",
                SHARED["textarea"]["notes"],
                ts_files,
                SHARED["textarea"]["standard_imports"],
                raw_patterns=SHARED["textarea"]["raw_tags"],
            )
        )
        reports.append(
            inventory_import_category(
                "Select",
                "SelectInput (`components/ui/form`) + domain EntitySelect wrappers",
                SHARED["select"]["notes"],
                ts_files,
                SHARED["select"]["standard_imports"],
                raw_patterns=SHARED["select"]["raw_tags"],
            )
        )
        reports.append(
            inventory_import_category(
                "Checkbox / Radio",
                "CheckboxField, RadioField (`components/ui/form`)",
                SHARED["checkbox_radio"]["notes"],
                ts_files,
                SHARED["checkbox_radio"]["standard_imports"],
                raw_patterns=SHARED["checkbox_radio"]["raw_tags"],
            )
        )
        reports.append(
            inventory_import_category(
                "Form",
                "FormGrid / FormField / FormSection / FormActions / FormModal",
                SHARED["form"]["notes"],
                ts_files,
                SHARED["form"]["standard_imports"],
            )
        )
        reports.append(
            inventory_import_category(
                "Modal / Dialog / Confirmation",
                "Modal, ConfirmDialog, FormModal, Drawer (ADR-028)",
                SHARED["modal"]["notes"],
                ts_files,
                SHARED["modal"]["standard_imports"],
            )
        )
        reports.append(
            inventory_import_category(
                "DataTable / Table",
                "UniversalDataTable -> WidthResponsiveDataTable (+ ServerDataTableFrame)",
                SHARED["datatable"]["notes"],
                ts_files,
                SHARED["datatable"]["standard_imports"],
                raw_patterns=SHARED["datatable"]["raw_tags"],
                deprecated=["ResponsiveDataTable"],
            )
        )
        reports.append(
            inventory_import_category(
                "Pagination",
                "PaginationBar + ServerDataTableFrame dual pagination",
                SHARED["pagination"]["notes"],
                ts_files,
                SHARED["pagination"]["standard_imports"],
            )
        )
        reports.append(
            inventory_import_category(
                "Filter / Toolbar",
                "FilterPanel",
                SHARED["filter_toolbar"]["notes"],
                ts_files,
                SHARED["filter_toolbar"]["standard_imports"],
                class_patterns=[r'className=["\'][^"\']*\bfilters\b'],
            )
        )
        reports.append(
            inventory_import_category(
                "Card",
                "Card (`components/ui/Card`)",
                SHARED["card"]["notes"],
                ts_files,
                SHARED["card"]["standard_imports"],
            )
        )
        reports.append(
            inventory_import_category(
                "PageHeader",
                "PageHeader / SectionHeader",
                SHARED["page_header"]["notes"],
                ts_files,
                SHARED["page_header"]["standard_imports"],
            )
        )
        reports.append(
            inventory_import_category(
                "Layout / Shell",
                "AppLayout, AdminSystemLayout, DataIntegrationLayout, Breadcrumb, UserMenu",
                SHARED["layout_shell"]["notes"],
                ts_files,
                SHARED["layout_shell"]["standard_imports"],
            )
        )
        reports.append(
            inventory_import_category(
                "Alert / Toast / Banner",
                "Banner (`components/ui/Banner`) — success/warning/error/info",
                SHARED["alert_toast"]["notes"],
                ts_files,
                SHARED["alert_toast"]["standard_imports"],
            )
        )
        reports.append(
            inventory_import_category(
                "Other shared UI",
                "Tabs, Badge, TruncatedText, TechnicalDetails, EmptyState, LoadingState, DetailFields",
                SHARED["other"]["notes"],
                ts_files,
                SHARED["other"]["standard_imports"],
            )
        )

        for path in ts_files:
            if "Modal" not in path.name and "Dialog" not in path.name:
                continue
            text_src = path.read_text(encoding="utf-8")
            r = rel(path)
            if "/components/ui/" in r:
                continue
            uses_shared = any(
                file_imports_symbol(text_src, s)
                for s in ("Modal", "ConfirmDialog", "FormModal", "Drawer")
            )
            if not uses_shared:
                local_modals.append(r)

        css_findings = inventory_css_overrides(files)
        catalog = inventory_component_catalog()
        domain_selects = [
            rel(p)
            for p in ts_files
            if p.name.endswith("Select.tsx") or "EntitySelect" in p.name
        ]

    payload = {
        "catalog": catalog,
        "domain_select_wrappers": domain_selects,
        "local_modal_wrappers_without_shared_import": local_modals,
        "categories": [asdict(r) for r in reports],
        "css_override_hotspots": css_findings,
        "routes": route_inv,
        "p0": p0,
        "p1": p1,
        "p2": p2,
        "p3": p3,
        "final": p_final,
        "gates": {
            "P0": p0["pass"],
            "P1": p1["pass"],
            "P2": p2["pass"],
            "P3": p3["pass"],
            "FINAL": p_final["pass"],
            "ALL": gate_passed(gates, "ALL"),
        },
    }
    (OUT / "inventory.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# FAIR CRM Frontend UI Inventory",
        "",
        "Audit of `frontend/src` against PROJECT_CONSTITUTION, ADR-028/032/034, "
        "`docs/frontend/UI_DESIGN_SYSTEM.md`, and `docs/frontend/RESPONSIVE_UI_STANDARD.md`.",
        "",
        "## P0 standardization gate",
        "",
        f"- **PASS:** {'YES' if p0['pass'] else 'NO'}",
        f"- **Total P0 violations:** {p0['total_violations']}",
        f"- Bare checkbox/radio (outside FormInputs): **{len(p0['bare_checkbox_radio'])}**",
        f"- Local `.filters` without FilterPanel: **{len(p0['local_filters_without_filter_panel'])}**",
        f"- Raw `<input|select|textarea>` (excl. specialty/domain allowlist): **{len(p0['raw_form_controls'])}**",
        f"- Allowlist: {', '.join(f'`{x}`' for x in p0['allowlist'])}",
        "",
        "## P1 standardization gate",
        "",
        f"- **PASS:** {'YES' if p1['pass'] else 'NO'}",
        f"- **Total P1 violations:** {p1['total_violations']}",
        f"- Bare alert/toast class tokens (`banner`/`toast`/`import-toast`): **{len(p1['bare_alert_toast'])}**",
        f"- Bare `card` class token on raw elements: **{len(p1['bare_card'])}**",
        "",
        "## P2 standardization gate",
        "",
        f"- **PASS:** {'YES' if p2['pass'] else 'NO'}",
        f"- **Total P2 violations:** {p2['total_violations']}",
        f"- Bare `form-error` class: **{len(p2['bare_form_error'])}**",
        f"- Legacy `link-button`: **{len(p2['link_button'])}**",
        f"- Ad-hoc emptyState: **{len(p2['adhoc_empty'])}**",
        f"- Ad-hoc page loading: **{len(p2['adhoc_loading'])}**",
        f"- Bare table/list action wrappers: **{len(p2['bare_action_wrappers'])}**",
        "",
        "## P3 standardization gate",
        "",
        f"- **PASS:** {'YES' if p3['pass'] else 'NO'}",
        f"- **Total P3 violations:** {p3['total_violations']}",
        f"- Bare icon-button class tokens: **{len(p3['bare_icon_buttons'])}**",
        f"- Pages missing PageShell: **{len(p3['missing_pageshell'])}**",
        f"- Layouts missing NavLink: **{len(p3['missing_navlink_layouts'])}**",
        "",
        "## Route auto-coverage",
        "",
        f"- **PASS:** {'YES' if route_inv['pass'] else 'NO'}",
        f"- AppRoute count: **{len(route_inv['app_routes'])}**",
        f"- Mounted page components: **{len(route_inv['mounted_page_components'])}**",
        f"- Missing PageShell on mounted pages: **{len(route_inv['missing_pageshell_on_mounted'])}**",
        f"- Unmounted page files: **{len(route_inv['unmounted_page_files'])}**",
        f"- Routes missing smoke catalog: **{len(route_inv['routes_missing_smoke_coverage'])}**",
        "",
        "## FINAL standardization gate",
        "",
        f"- **PASS:** {'YES' if p_final['pass'] else 'NO'}",
        f"- **Total FINAL violations:** {p_final['total_violations']}",
        f"- Bare `field-error`: **{len(p_final['bare_field_error'])}**",
        f"- Bare `modal-actions`: **{len(p_final['bare_modal_actions'])}**",
        f"- `form-actions` inside Modal/FormModal: **{len(p_final['form_actions_in_modal'])}**",
        f"- Legacy CSS breakpoints: **{len(p_final['legacy_breakpoints'])}**",
        f"- Icon buttons missing aria-label: **{len(p_final['a11y_icon_buttons_missing_label'])}**",
        f"- Route coverage violations: **{route_inv['total_violations']}**",
        f"- Prior gates failed: **{'YES' if p_final['prior_gates_failed'] else 'NO'}**",
        f"- Breakpoints found: {', '.join(str(x) for x in p_final.get('breakpoints_found', []))}",
        "",
        "## Gate commands",
        "",
        "```powershell",
        "python scripts/maintenance/inventory_frontend_ui.py --gate P0",
        "python scripts/maintenance/inventory_frontend_ui.py --gate P1",
        "python scripts/maintenance/inventory_frontend_ui.py --gate P2",
        "python scripts/maintenance/inventory_frontend_ui.py --gate P3",
        "python scripts/maintenance/inventory_frontend_ui.py --gate FINAL",
        "python scripts/maintenance/inventory_frontend_ui.py --gate ALL",
        "```",
        "",
    ]

    if write_full and catalog:
        insert_at = lines.index("## Gate commands")
        extra = [
            "## Shared catalog",
            "",
            f"- `components/ui`: {', '.join(catalog.get('shared_ui_files', []))}",
            f"- Form kit: {', '.join(catalog.get('form_kit', []))}",
            "",
            "## Category summary",
            "",
            "| UI türü | Ortak altyapı | Toplam hit | Standart | Standart dışı |",
            "|---|---|---:|---:|---:|",
        ]
        for r in reports:
            extra.append(
                f"| {r.category} | {r.standard_infra} | {r.total_hits} | {r.standard_hits} | {r.nonstandard_hits} |"
            )
        extra.append("")
        lines[insert_at:insert_at] = extra

    report_text = "\n".join(lines)
    (OUT / "REPORT.md").write_text(report_text, encoding="utf-8")

    print_gate_summary(gates, args.gate or "ALL")
    if not args.quiet and write_full:
        print(report_text[:3000].encode("ascii", "replace").decode("ascii"))
        print(f"\n... full report: {OUT / 'REPORT.md'}")
    print(f"json: {OUT / 'inventory.json'}")

    if args.gate:
        return 0 if gate_passed(gates, args.gate) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
