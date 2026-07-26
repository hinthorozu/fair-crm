"""Central MailerSend / email-provider status transition policy.

Prevents provider_status regression when webhooks arrive out of order.
"""

from __future__ import annotations

# Ranked progression. Higher rank may replace lower. Equal rank is a no-op.
# Compliance terminals outrank delivery/engagement; hard_bounced outranks soft failures.
PROVIDER_STATUS_RANK: dict[str, int] = {
    "accepted": 10,
    "sent": 20,
    "deferred": 25,
    "soft_bounced": 25,
    "delivered": 40,
    "opened": 50,
    "clicked": 60,
    "hard_bounced": 100,
    "unsubscribed": 110,
    "spam_complaint": 120,
}

MAILERSEND_EVENT_TO_PROVIDER_STATUS: dict[str, str] = {
    "activity.sent": "sent",
    "activity.delivered": "delivered",
    "activity.soft_bounced": "soft_bounced",
    "activity.hard_bounced": "hard_bounced",
    "activity.deferred": "deferred",
    "activity.opened": "opened",
    "activity.clicked": "clicked",
    "activity.unsubscribed": "unsubscribed",
    "activity.spam_complaint": "spam_complaint",
}

SUPPORTED_MAILERSEND_ACTIVITY_EVENTS = frozenset(MAILERSEND_EVENT_TO_PROVIDER_STATUS)


def map_mailersend_event_to_provider_status(event_type: str) -> str | None:
    return MAILERSEND_EVENT_TO_PROVIDER_STATUS.get(event_type)


def should_update_provider_status(current: str | None, incoming: str) -> bool:
    """Return True only when ``incoming`` is a forward (non-regressive) transition."""
    if not incoming:
        return False
    incoming_rank = PROVIDER_STATUS_RANK.get(incoming)
    if incoming_rank is None:
        return False
    if current is None or current == "":
        return True
    if current == incoming:
        return False
    current_rank = PROVIDER_STATUS_RANK.get(current)
    if current_rank is None:
        # Unknown legacy/current value — allow known incoming statuses.
        return True
    return incoming_rank > current_rank


def apply_provider_status_transition(current: str | None, incoming: str) -> str | None:
    """Return the status to store, or None when no change should be written."""
    if should_update_provider_status(current, incoming):
        return incoming
    return None
