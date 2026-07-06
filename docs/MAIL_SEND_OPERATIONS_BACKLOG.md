# Mail Send Operations — Faz 2 / Future Work Backlog

**Status:** Backlog only — not scheduled, not in active development.

**Context:** Faz 1 delivered safe batch processing logic for `mail_send_operations` (`ProcessMailSendOperationsWorker`, manual CLI runner, stuck-operation recovery, duplicate guard, tests). The worker does **not** run automatically today; fair bulk and test-mail paths still use their existing synchronous/background flows.

This document captures follow-up work for a hardened mail queue platform. Items are unordered unless dependencies are noted inline.

---

## Backlog items

### Scheduling & runtime

- **Periodic / automatic mail queue worker** — run `ProcessMailSendOperationsWorker` on an interval without manual CLI invocation.
- **Core jobs integration** — delegate scheduling/execution to KYROX Core `platform_jobs` (or equivalent public HTTP contract); Fair CRM must not import Core Python modules directly (see `AGENTS.md`, ADR-009).
- **Dedicated mail-worker container / daemon runner** — long-lived process or sidecar separate from the FastAPI API process; distinct deploy unit, health signal, and graceful shutdown.

### Rate limiting & dispatch

- **SMTP account–based rate limit** — cap send throughput per configured SMTP account.
- **Organization-based rate limit** — tenant-scoped caps independent of SMTP account.
- **SMTP-aware dispatch** — route/defer operations based on account capacity, connection state, and provider constraints.

### Reliability & policy

- **Retry / backoff engine** — structured retry policy for transient SMTP failures (timeouts, 4xx deferrals); distinct from user-initiated “Tekrar Gönder”.
- **Provider-specific policy** — per-provider rules (batch size, concurrency, quiet hours, bounce handling hooks).

### Observability

- **Monitoring / dashboard** — queue depth, stuck `sending` count, success/failure rates, SMTP timeout metrics, worker lag; operator-facing view aligned with Admin / Mail Operations UI.

---

## Out of scope for this backlog note

- Implementation, migrations, API changes, or container wiring.
- Changes to Import, Merge, or Scraper modules.

## Related code (Faz 1 reference)

| Area | Path |
|------|------|
| Worker use case | `backend/app/modules/mail_send_operations/application/process_mail_send_operations_worker.py` |
| Dispatcher | `backend/app/modules/mail_send_operations/application/mail_send_operation_dispatcher.py` |
| CLI (manual) | `backend/app/workers/mail_send_operation_worker.py` |
