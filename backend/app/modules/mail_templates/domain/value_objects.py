from enum import Enum


class MailTemplateType(str, Enum):
    TRANSACTIONAL = "transactional"
    NOTIFICATION = "notification"
    MARKETING = "marketing"
    SYSTEM = "system"
