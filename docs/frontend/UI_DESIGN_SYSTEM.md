# FAIR CRM UI Design System

**Binding master:** [FRONTEND_UI_MASTER_STANDARD.md](FRONTEND_UI_MASTER_STANDARD.md) — read before any frontend UI change. This file is a supporting catalog; on conflict, the master wins.

Complements [RESPONSIVE_UI_STANDARD.md](RESPONSIVE_UI_STANDARD.md), [ADR-034](../DECISIONS.md), and `PROJECT_CONSTITUTION.md`.

If a shared component exists, **use it**. Ad-hoc UI is forbidden unless documented under the inventory allowlist / specialty policy in the master standard.

---

## Principles

1. **One design system** — tokens + shared components under `frontend/src/components/ui/`.
2. **No raw controls in consumers** — pages/features must not invent parallel buttons, inputs, tables, modals, banners, loading, or empty states.
3. **PageShell for production pages** — every in-app route page wraps content in `PageShell` (Login is the documented auth exception).
4. **Responsive by default** — fluid layout; no device-specific CSS; no new magic breakpoints without ADR.
5. **Build PASS ≠ Done** — Inventory gates + visual QA + responsive QA + a11y must PASS.

---

## Design tokens

Source of truth: `frontend/src/styles.css` (`:root`).

| Category | Tokens (examples) |
|----------|-------------------|
| Surfaces | `--bg`, `--surface`, `--surface-raised`, `--surface-sunken`, `--surface-overlay` |
| Text | `--text`, `--muted` |
| Borders | `--border`, `--border-strong` |
| Brand / semantic | `--primary*`, `--success*`, `--warning*`, `--danger*`, `--info*`, `--neutral*` |
| Typography | `--font-sans`, `--font-mono`, `--text-xs`…`--text-3xl`, `--leading-*`, `--weight-*` |
| Spacing | `--space-1`…`--space-12` (4px base) |
| Layout | `--page-padding` (`clamp`), `--page-content-max-width`, `--section-gap`, sidebar/subnav widths |
| Form widths | `--form-width-narrow` (28rem), `--form-width-standard` (48rem), `--form-width-wide` (72rem), `--form-width-full` |
| Controls | `--control-height*`, `--control-padding-x`, `--control-radius`, `--check-size` |
| Radius | `--radius-sm`, `--radius`, `--radius-lg` |
| Shadows | `--shadow-sm`, `--shadow`, `--shadow-lg` |
| Focus | `--focus-ring`, `--focus-ring-danger` |
| Disabled | `--disabled-opacity` |
| Breakpoints | `--bp-mobile` 390, `--bp-tablet` 768, `--bp-laptop` 1024, `--bp-desktop` 1440 |

**Rules:** Prefer tokens over hard-coded colors/spacing. New tokens require updating this doc + `styles.css`.

### Typography

- Body: `--font-sans`, `--text-base`, `--leading-normal`
- Mono / technical: `--font-mono` / `.text-mono`
- Page titles via `PageHeader`; do not invent one-off hero typography inside CRM chrome

### Spacing

Use `--space-*` and layout gaps (`--section-gap`, `--form-gap`). Prefer CSS grid/flex + `gap` over magic margins.

### Focus / disabled / loading

- Focus: visible ring via `--focus-ring` on interactive controls
- Disabled: `--disabled-opacity`; never remove focus styles for “disabled look”
- Loading: `LoadingState` for page/section; `Button` `loading` prop for actions; never ad-hoc “Yükleniyor…” paragraphs

### Container / form width

- Default page content clamped by `PageShell` / `--page-content-max-width`
- `PageShell fullWidth` only for specialty dense grids (e.g. Import Wizard)
- Forms: pick narrow / standard / wide / full by intent; use `FormGrid` for field layout

---

## Component catalog

Paths are under `frontend/src/components/ui/` unless noted.

### Button

| | |
|--|--|
| **Use** | Primary/secondary/danger/ghost/link actions |
| **Avoid** | Raw `<button>` without `.btn` / `Button`; custom colored divs as buttons |
| **Variants** | `primary`, `secondary`, `danger`, `ghost`, `link` (+ sizes `sm`/`md`/`lg`, `loading`) |
| **API** | `Button` (`Button.tsx`) preferred; `.btn.*` class tokens still valid |
| **Responsive** | Critical actions remain visible at 390px; wrap/stack in toolbars, do not hide behind horizontal scroll |
| **A11y** | Real `<button>`; disabled + `aria-busy` when loading |

### IconButton

| | |
|--|--|
| **Use** | Icon-only actions (kebab, expand, password toggle, sidebar collapse) |
| **Avoid** | Bare `<button className="btn icon">` in consumers |
| **Variants** | Via `IconButton` props / shared icon classes |
| **Responsive** | Min hit target ~40px; keep in action clusters |
| **A11y** | **Required** `aria-label` (or visible text) |

### TextInput / PasswordInput / TextareaInput / SelectInput

| | |
|--|--|
| **Use** | All text/password/textarea/select fields in forms and filters |
| **Avoid** | Raw `<input>`, `<textarea>`, `<select>` outside kit/allowlist |
| **Variants** | Invalid via `aria-invalid` + `form-control--invalid`; disabled via prop |
| **Responsive** | Full width of grid cell; never fixed px widths that overflow |
| **A11y** | Associated label (`FormField`); `aria-describedby` for errors/hints |

### Combobox

| | |
|--|--|
| **Use** | Async entity search: `FairEntitySelect`, `AdapterSelect` |
| **Avoid** | Rebuilding listbox from scratch; raw selects for large entity lists |
| **Responsive** | Dropdown must stay in viewport (`useFloatingMenuPosition`) |
| **A11y** | Keyboard open/close; announce loading/empty |

### CheckboxField / RadioField

| | |
|--|--|
| **Use** | Every checkbox/radio in product UI |
| **Avoid** | Bare `type="checkbox|radio"` outside `FormInputs` |
| **Responsive** | Control + label one row; no stretched full-bleed controls |
| **A11y** | Label wraps or is programmatically associated |

### Switch

| | |
|--|--|
| **Status** | No shared Switch yet |
| **Rule** | Do **not** invent ad-hoc toggles; use `CheckboxField` or propose a shared Switch via ADR + kit |

### FieldError

| | |
|--|--|
| **Use** | Inline field validation messages |
| **Avoid** | Bare `.form-error` / `.field-error` class spam in consumers |
| **A11y** | Linked via `aria-describedby` |

### Banner

| | |
|--|--|
| **Use** | Page/section feedback: success, warning, error, info |
| **Avoid** | Toast systems, bare `.banner` / `.toast` classes |
| **Responsive** | Full content width; text wraps; actions wrap |
| **A11y** | Role/status appropriate to severity |

### Card

| | |
|--|--|
| **Use** | Content surface grouping |
| **Avoid** | Bare `className="card"` on raw elements |
| **Responsive** | Fluid; stack children; no fixed min-width that forces page scroll |

### Badge

| | |
|--|--|
| **Use** | Compact status chips in tables/headers |
| **Avoid** | One-off pill CSS for status |
| **Responsive** | Truncate/wrap with parent cell rules |

### Table (UniversalDataTable)

| | |
|--|--|
| **Use** | All list tables → `UniversalDataTable` → `WidthResponsiveDataTable` |
| **Avoid** | Raw `<table>`, page-local responsive table CSS, deprecated `DataTable`/`ResponsiveDataTable` consumers |
| **Responsive** | Container-width column hide + child row (see responsive standard §8) |
| **A11y** | Sortable headers announce state; Actions column never sortable |

### TableRowActions

| | |
|--|--|
| **Use** | Row action clusters (edit/archive/menu) |
| **Avoid** | Bare `.table-actions` / `*-list-actions` wrappers |
| **Responsive** | Stay visible; icon buttons with labels |

### Pagination

| | |
|--|--|
| **Use** | `PaginationBar` via `ServerDataTableFrame` (dual top+bottom default) |
| **Avoid** | Custom page-number bars |
| **Responsive** | Separate row under filters; wrap controls |

### Modal / FormModal / ConfirmDialog / Drawer

| | |
|--|--|
| **Use** | Overlays per ADR-028; forms in `FormModal`; confirms in `ConfirmDialog`; side panels in `Drawer` |
| **Avoid** | Ad-hoc backdrops; bare `.modal-actions` footers; `form-actions` inside modal chrome (use modal `footer`) |
| **Responsive** | Desktop centered → tablet wide → mobile bottom sheet + sticky footer |
| **A11y** | Focus trap; dirty-guard (no backdrop/Escape dismiss when dirty) |

### Dropdown / Menu

| | |
|--|--|
| **Use** | Kebab / action menus built on `IconButton` + floating position helper |
| **Avoid** | Absolute menus without viewport clamping |
| **A11y** | Escape closes; focus returns to trigger |

### EmptyState / LoadingState

| | |
|--|--|
| **Use** | Empty lists/sections; page or section loading |
| **Avoid** | `<p className="text-muted">` empty/loading copy |
| **Responsive** | Centered in content area; no overflow |

### PageHeader / Toolbar / FilterPanel

| | |
|--|--|
| **Use** | `PageHeader` for title/actions; `FilterPanel` for list filters; toolbar slot via `ServerDataTableFrame` |
| **Avoid** | Local `.filters` toolbars without `FilterPanel` |
| **Responsive** | 3/2/1 filter grid; actions wrap |

### NavLink

| | |
|--|--|
| **Use** | Sidebar / subnav links in `AppLayout`, `AdminSystemLayout`, `DataIntegrationLayout` |
| **Avoid** | Bare `.sidebar-link` / `*-subnav-link` markup |
| **A11y** | Active state exposed |

### PageShell

| | |
|--|--|
| **Use** | Root wrapper for every in-app production page |
| **Avoid** | Page content floating without `.page` / `PageShell` |
| **Variants** | `fullWidth` for specialty dense layouts |
| **Responsive** | Applies page padding + ultrawide max-width clamp |

---

## Governance gates (summary)

| Gate | Script |
|------|--------|
| P0–P3, FINAL, ALL | `python scripts/maintenance/inventory_frontend_ui.py --gate <GATE>` |
| Frontend build | `cd frontend && npm run build` |
| Unit tests | `cd frontend && npm test` |

Detail: `PROJECT_CONSTITUTION.md` → Frontend UI Governance.

---

## Visual QA (mandatory)

**Inventory PASS ≠ UI is good.** Definition of Done also requires human/visual checks:

- Alignment and consistent whitespace
- Hierarchy (title → toolbar → content → pagination)
- Field sizing and form column balance
- Action placement (primary obvious; destructive clear)
- Responsive balance at BP−1 / BP / BP+1
- Ultrawide: content clamp, no sparse broken rows
- Large features: screenshot evidence via `frontend/scripts/capture-ui-evidence.mjs`

---

## Specialty policy

Specialty UI is allowed only when:

1. Generic component **cannot** meet the interaction (document why)
2. Implementation still uses **design tokens**
3. Covered by inventory allowlist entry (**file + pattern + reason + owner**)
4. Verified by a test or gate (inventory allowlist and/or targeted test)

`"specialty"` alone is **not** a reason. See [UI_INVENTORY_ALLOWLIST.md](UI_INVENTORY_ALLOWLIST.md).
