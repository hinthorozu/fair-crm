"""Constants for mail send operation worker processing."""

SENDING_TIMEOUT_ERROR_CODE = "sending_timeout"

WORKER_EVENT_PICKED = "picked_by_worker"
WORKER_EVENT_SENDING_STARTED = "sending_started"
WORKER_EVENT_SENT = "sent"
WORKER_EVENT_FAILED = "failed"
WORKER_EVENT_SENDING_TIMEOUT = "sending_timeout"

WORKER_LOG_PICKED = "Worker tarafından seçildi"
WORKER_LOG_SENDING_STARTED = "Worker gönderimi başladı"
WORKER_LOG_SENT = "Worker ile gönderildi"
WORKER_LOG_SENDING_TIMEOUT = "Gönderim zaman aşımına uğradı"
WORKER_LOG_SENDING_TIMEOUT_FAILED = "Mail gönderimi zaman aşımı nedeniyle başarısız oldu"

TERMINAL_STATUSES = frozenset({"sent", "failed", "cancelled", "skipped"})
