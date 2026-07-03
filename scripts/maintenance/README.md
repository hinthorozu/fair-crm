# Maintenance Developer Toolkit

Internal developer/admin scripts for one-time database maintenance, analysis, and exports.

**These are not product features.** They are not exposed in the API or UI. Run only against the intended environment with a current backup when scripts modify data.

Run all commands from the project root:

```powershell
cd fair-crm
python scripts/maintenance/<folder>/<script_name>.py
```

## Output locations

| Directory | Purpose |
|-----------|---------|
| `scripts/maintenance/reports/` | Analysis Excel outputs |
| `scripts/maintenance/exports/` | Duplicate export workbooks |

---

## Analysis (`analysis/`)

Read-only reports. No database changes.

### `report_customer_duplicates.py`

**Purpose:** Find duplicate customer groups across the full database.

**When to use:** Master duplicate audit before merge planning or data cleanup.

**Example:**

```powershell
python scripts/maintenance/analysis/report_customer_duplicates.py
```

**Output:** `scripts/maintenance/reports/customer_duplicates_<timestamp>.xlsx`

---

## Exports (`exports/`)

Read-only Excel exports for duplicate-group review.

### `export_duplicate_group_customers.py`

**Purpose:** Export all customers in duplicate groups with fair participation rows (one row per participation).

**When to use:** Single workbook for duplicate review across all fairs.

**Example:**

```powershell
python scripts/maintenance/exports/export_duplicate_group_customers.py
```

**Output:** `scripts/maintenance/exports/duplicate_group_customers_<timestamp>.xlsx`

---

### `export_duplicate_groups_by_fair.py`

**Purpose:** Same duplicate export split into one Excel file per fair plus `NO_FAIR.xlsx` and `SUMMARY.xlsx`.

**When to use:** Fair-by-fair operator review of duplicate groups.

**Example:**

```powershell
python scripts/maintenance/exports/export_duplicate_groups_by_fair.py
```

**Output:** `scripts/maintenance/exports/duplicate_groups_by_fair/` (`<fair_name>_<year>.xlsx`, `NO_FAIR.xlsx`, `SUMMARY.xlsx`)

---

## Cleanup (`cleanup/`)

**Destructive.** Modifies the database. Internal admin use only.

### `delete_customers_without_fair.py`

**Purpose:** Physically delete all customers with zero fair participations.

**When to use:** One-time master DB cleanup after analysis and backup. No confirmation prompts — use with care.

**Example:**

```powershell
python scripts/maintenance/cleanup/delete_customers_without_fair.py
```

**Output:** Console summary only (deleted / failed counts).

---

## Shared paths

`scripts/maintenance/_paths.py` defines `ROOT`, `REPORTS_DIR`, `EXPORTS_DIR`, and `bootstrap()` for backend imports and `.env` loading.
