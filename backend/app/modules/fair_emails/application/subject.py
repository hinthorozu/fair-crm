def build_bulk_email_subject(subject: str, fair_name: str | None) -> str:
    """Prefix the final bulk-email subject with its fair name when available."""
    normalized_subject = subject.strip()
    normalized_fair_name = (fair_name or "").strip()
    if not normalized_fair_name:
        return normalized_subject
    prefix = f"{normalized_fair_name} - "
    if normalized_subject.startswith(prefix):
        return normalized_subject
    return f"{prefix}{normalized_subject}"
