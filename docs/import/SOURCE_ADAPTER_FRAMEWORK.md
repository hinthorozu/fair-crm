# Universal Source Adapter Framework

**Module:** Data Integration (`data_integration`)  
**Status:** Sprint 09.2 — architecture + Excel adapter migration  
**Related:** [IMPORT_ARCHITECTURE.md](IMPORT_ARCHITECTURE.md), [DECISIONS.md](../DECISIONS.md) ADR-016, ADR-017

Fair CRM is a **Universal Data Integration Platform**. Excel is the first source adapter; CSV, XML, REST API, scrapers, and ERP connectors follow the same contract without changing the Import Engine.

---

## Platform model

```text
Data Integration
    Sources (adapters)
        Excel Adapter          ← shipped (Sprint 09.1/09.2)
        CSV Adapter            ← planned
        XML Adapter            ← planned
        REST API Adapter       ← planned
        Scraper Adapters       ← one per fair site (TUYAP, IFM, …)
        ERP Adapters           ← Logo, Mikro, Netsis, SAP
```

---

## Adapter lifecycle

Every adapter implements the same stages. **No adapter writes to CRM tables.**

```text
Connect
    ↓
Read Source
    ↓
Normalize
    ↓
Transform (source-specific shaping only)
    ↓
Preview (raw matrix for Import Engine)
    ↓
Import Engine  ← mapping, matching, merge, decisions
    ↓
Background Job
    ↓
Report
```

| Stage | Adapter | Import Engine |
|-------|---------|---------------|
| Connect | Validate payload, credentials, URL | — |
| Read Source | Parse file / fetch API / scrape HTML | — |
| Normalize | Tabular raw rows + column metadata | — |
| Transform | Source-specific cleanup (encoding, pagination flatten) | — |
| Preview | Return preview dict (`columns`, `rows`, `total_rows`, …) | Consumes preview |
| Column mapping | — | Header modes, field mapping |
| Smart matching | — | DuplicateDetector |
| Merge preview | — | MergeStrategy |
| Apply | — | ImportExecutor + Background Job |

---

## SourceAdapter protocol

Backend protocol: `app.modules.data_integration.domain.source_adapter.SourceAdapter`

```python
@property
def source_type(self) -> ImportSourceType: ...

def connect(self, connection: SourceConnection) -> None: ...
def read_source(self, connection, *, sheet_name=None) -> RawSourceData: ...
def normalize(self, raw: RawSourceData) -> dict[str, Any]: ...
def preview(self, connection, *, sheet_name=None) -> dict[str, Any]: ...
```

Registration: `SourceAdapterRegistry` in `application/adapters/registry.py`.  
Upload and sheet selection resolve adapters via registry — **not** hard-coded Excel imports.

---

## Scraper adapter standard

Each fair website is a **separate adapter**. Examples:

| Adapter | Responsibility |
|---------|----------------|
| `TUYAPAdapter` | TUYAP URL structure, HTML parsing, pagination |
| `IFMAdapter` | IFM site rules |
| `FIstanbulAdapter` | F Istanbul exhibitor pages |
| `ExpomedAdapter` | Expomed listing API/HTML |
| `CNRAdapter` | CNR fair portal |

Each scraper adapter knows:

- URL patterns and entry points
- HTML/CSS selectors or JSON paths
- Pagination (page param, infinite scroll, next link)
- Field extraction → flat row projection

The Import Engine does **not** know site-specific rules. Scraper output must be normalized to the same preview contract as Excel.

---

## ERP adapter standard (future)

ERP connectors (Logo, Mikro, Netsis, SAP) implement `SourceAdapter` with:

- `Connect` — auth, tenant, endpoint
- `Read Source` — paginated entity fetch (customers, contacts, orders)
- `Normalize` — map ERP fields to raw columns (not yet CRM canonical fields)

Field mapping to CRM canonical fields remains in **Import Engine** (`ImportMapper`), not in ERP adapters.

---

## Adding a new adapter (checklist)

1. Implement `SourceAdapter` under `application/adapters/<name>/`.
2. Register in `get_source_adapter_registry()` with `file_extensions` or source type.
3. Add frontend menu entry under **Veri Entegrasyonu → Sources** (when UX ships).
4. Add adapter tests — lifecycle + registry resolution.
5. **Do not modify** `ImportExecutor`, `DuplicateDetector`, or `MergeStrategy` unless adding a new cross-cutting rule.

---

## Separation of concerns

| Component | Responsibility |
|-----------|----------------|
| **Adapter** | Read external source; output raw preview matrix |
| **Import Engine** | Mapping, validation, normalization to CRM fields, matching |
| **DuplicateDetector** | Compare rows to existing CRM records |
| **MergeStrategy** | Business rules for field-level merge |
| **ImportExecutor** | Apply approved rows via domain repositories |
| **Background Job** | Async apply + progress + final report |

Dependencies flow **one way**: Adapter → Engine → Job. Engine never imports adapter implementations except via registry at application boundaries (upload, sheet select).

---

## Sprint 09.2 Definition of Done

- [x] `SourceAdapter` protocol and `SourceAdapterRegistry`
- [x] Excel migrated to `ExcelSourceAdapter` on registry
- [x] Upload / sheet selection use registry (no direct Excel coupling in use cases)
- [x] Import Engine remains source-agnostic
- [x] Architecture documented (this file + ADR-017)

Future sprints add CSV, scraper, and ERP adapters by registration only.
