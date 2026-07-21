# FAIR CRM Responsive UI Standard (ADR-032)

Canonical frontend responsive design system. All current and future screens must follow this document.

## Breakpoints

| Tier | Width | Smoke target |
|------|-------|--------------|
| Mobile | `< 768px` | 390px |
| Tablet | `768px–1023px` | 768px |
| Laptop | `≥ 1024px` | 1024px |
| Desktop | `≥ 1440px` | 1440px |

CSS tokens: `--bp-mobile`, `--bp-tablet`, `--bp-laptop`, `--bp-desktop` in `frontend/src/styles.css`.

**Note:** List **tables** do **not** switch layout by these breakpoints. Tables use available container width (see §8).

## 1. Page skeleton

```
PageHeader
FilterPanel / Toolbar
SummaryCards (optional)
Content Card
DataTable / Form / Detail
Pagination / Actions
Modal / Drawer
```

## 2. Form grid

- Use `FormGrid` (`columns={3}` default, or `2`).
- Desktop ≥1024: 3 columns; tablet: 2; mobile: 1.
- Labels, inputs, hints, and errors stay aligned via `FormField` / `.field`.
- Use `CheckboxField` / `RadioField` — never a bare checkbox without a label.

## 3. FilterPanel / Toolbar

- Use `FilterPanel` for list filters.
- Pagination lives in a separate row under filters (`ServerDataTableFrame`) — never squeezed between filter controls.

## 4. Checkbox / radio

- Shared components only: `CheckboxField`, `RadioField`.
- Control + label must stay on one row; control never floats alone.

## 5. Buttons

- Variants: `primary` | `secondary` | `danger` | `ghost` | `link`.
- Classes: `.btn.primary` or alias `.btn-primary` (same for secondary/danger/ghost).
- Critical actions must remain visible on mobile (no horizontal scroll to reach them).

## 6. Card / Panel

- Use shared `Card` for content containers.
- Prefer existing surface tokens; avoid one-off card chrome.

## 7. Modal

- Desktop: centered.
- Tablet: wide modal.
- Mobile: full-width bottom-sheet style; sticky `footer` prop for actions.
- ADR-028 dirty-guard rules still apply (no backdrop/Escape dismiss).

## 8. DataTable standard (mandatory for all lists)

**Entry point:** `UniversalDataTable` → `WidthResponsiveDataTable` (+ `ServerDataTableFrame` when using `table=`).

**This is the default for every existing and every new list table.** Do not invent page-local responsive table implementations.

### 8.1 Width-responsive columns

- Behavior is driven by **available container width** (`ResizeObserver`), not fixed mobile/tablet/desktop table layouts.
- **Column array order = responsive priority** (1st column highest priority; trailing columns hide first).
- As space shrinks, hide from the right; show hidden fields in a child row via `+` / `−`.
- As space grows, columns return to the main row automatically.
- When nothing is hidden (and no detail-only columns), the `+` control disappears.
- Very narrow layouts may keep only the first column + expand control.

### 8.2 Column squeezing forbidden

- Do not crush columns to “fit” the viewport.
- No letter-by-letter wrapping (`word-break: break-all` and similar) on table cells.
- Short cells (dates, status, actions, headers) stay on one line (`col-nowrap`).
- Long text may wrap at natural word boundaries (`allowWrap` / name-like keys).
- Default horizontal scroll is **off**. Opt-in only: `table-wrap--scroll-only` (e.g. Import Wizard mapping grids).

### 8.3 Child row

- Shows only columns currently hidden from the main row, plus `priority: "technical"` detail-only fields.
- Format: `Alan adı: Değer` using user-facing labels (`title` / `dataLabel`), never raw internal keys when a label exists.

### 8.4 Column `priority` (legacy + technical)

| Value | Behavior |
|-------|----------|
| *(omit)* / `primary` / `secondary` | Main-row candidate; **array order** decides hide order. `secondary` no longer means breakpoint hide. |
| `technical` | **Never** in the main row (even when space allows). Child row only. |

Do not put technical/internal columns in the main grid just because width remains.

### 8.5 Dual pagination (default)

- `ServerDataTableFrame` renders the same `ServerDataTablePagination` **above and below** the table by default (`showBottomPagination: true`).
- One shared controller state — no duplicated pagination logic.
- Top and bottom stay in sync: page, total, page size, previous, next.
- Set `showBottomPagination={false}` only for rare nested/preview frames.

## 9. Pagination placement

- Use `PaginationBar` via `ServerDataTableFrame` / `ServerDataTablePagination`.
- Separated visually from the filter grid.
- Dual top+bottom is the project standard (§8.5).

## 10. Long text / UUID / URL / technical fields

Do **not** put these in the main table as primary columns:

- `run_id`, `adapter_key`, `engine_key`, UUID, `external_id`
- Long URLs, JSON/debug/error detail, long technical messages

Use `priority: "technical"`, `TruncatedText`, `TechnicalDetails`, and `.text-wrap` / `.text-mono`.

## 11. Responsive breakpoints

Every screen must be usable at 390 / 768 / 1024 / 1440. “Desktop works” is not acceptance.

Table column visibility uses container width (§8), not these tiers.

## 12. Definition of Done (frontend)

A frontend screen or component change is not done until:

- [ ] Uses shared primitives (`PageHeader`, `FilterPanel`, `FormGrid`/`FormField`, `UniversalDataTable` → `WidthResponsiveDataTable`, `Modal`, `PaginationBar`, etc.)
- [ ] Form/filter grid is 3 / 2 / 1 responsive
- [ ] Checkbox/radio use shared fields
- [ ] List uses width-responsive + child row; technical fields not in main row
- [ ] Dual pagination present for server-side lists (unless explicitly opted out)
- [ ] No default horizontal scroll on the page
- [ ] Actions visible at 390px
- [ ] Modal actions visible on mobile (footer when needed)
- [ ] Long UUID/URL/text does not overflow viewport
- [ ] Existing API / filter / pagination / silent-refresh behavior unchanged
- [ ] Smoke-checked at 390, 768, 1024, 1440 (and table resize behavior)
- [ ] `npm run build` PASS
- [ ] No page-local responsive table CSS/hacks

## Key files

| File | Role |
|------|------|
| `frontend/src/components/ui/WidthResponsiveDataTable.tsx` | Width-based hide + child row engine |
| `frontend/src/components/ui/UniversalDataTable.tsx` | List standard entry |
| `frontend/src/components/ui/ServerDataTableFrame.tsx` | Toolbar + dual pagination |
| `frontend/src/components/ui/FilterPanel.tsx` | Filter shell |
| `frontend/src/components/ui/TruncatedText.tsx` | Short + title full |
| `frontend/src/components/ui/TechnicalDetails.tsx` | Collapsible tech block |
| `frontend/src/components/ui/ResponsiveDataTable.tsx` | Deprecated adapter → WidthResponsive |
| `frontend/src/styles.css` (ADR-032 + width-responsive) | Tokens + layout |
