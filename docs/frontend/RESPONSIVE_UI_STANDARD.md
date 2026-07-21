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

## 8. DataTable responsive

Use `UniversalDataTable` → `ResponsiveDataTable` with column `priority`:

| Priority | Desktop | Tablet / Mobile |
|----------|---------|-----------------|
| `primary` | Main row | Main row / card |
| `secondary` | Main row | Expand child panel |
| `technical` | Expand only | Expand only |

- Default horizontal scroll is **off**.
- Opt-in only: `table-wrap--scroll-only` (e.g. mapping grids).
- Tablet/mobile: `+` / `−` expand control for secondary/technical fields.

## 9. Pagination

- Use `PaginationBar` via `ServerDataTableFrame`.
- Separated visually from the filter grid.

## 10. Long text / UUID / URL / technical fields

Do **not** put these in the main table as primary columns:

- `run_id`, `adapter_key`, `engine_key`, UUID, `external_id`
- Long URLs, JSON/debug/error detail, long technical messages

Use `priority: "technical"`, `TruncatedText`, `TechnicalDetails`, and `.text-wrap` / `.text-mono`.

## 11. Responsive breakpoints

Every screen must be usable at 390 / 768 / 1024 / 1440. “Desktop works” is not acceptance.

## 12. Definition of Done (frontend)

A frontend screen or component change is not done until:

- [ ] Uses shared primitives (`PageHeader`, `FilterPanel`, `FormGrid`/`FormField`, `UniversalDataTable`, `Modal`, `PaginationBar`, etc.)
- [ ] Form/filter grid is 3 / 2 / 1 responsive
- [ ] Checkbox/radio use shared fields
- [ ] List columns declare `priority` where needed; technical fields not in main row
- [ ] No default horizontal scroll on the page
- [ ] Actions visible at 390px
- [ ] Modal actions visible on mobile (footer when needed)
- [ ] Long UUID/URL/text does not overflow viewport
- [ ] Existing API / filter / pagination / silent-refresh behavior unchanged
- [ ] Smoke-checked at 390, 768, 1024, 1440
- [ ] `npm run build` PASS

## Key files

| File | Role |
|------|------|
| `frontend/src/components/ui/ResponsiveDataTable.tsx` | Priority + expand |
| `frontend/src/components/ui/UniversalDataTable.tsx` | List standard entry |
| `frontend/src/components/ui/FilterPanel.tsx` | Filter shell |
| `frontend/src/components/ui/TruncatedText.tsx` | Short + title full |
| `frontend/src/components/ui/TechnicalDetails.tsx` | Collapsible tech block |
| `frontend/src/styles.css` (ADR-032 section) | Tokens + layout |
