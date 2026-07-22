from enum import StrEnum


class TodoStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class TodoPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TodoCategory(StrEnum):
    ARAMA = "arama"
    TOPLU_MAIL = "toplu_mail"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    ZIYARET = "ziyaret"
    TEKLIF = "teklif"
    VERI_TEMIZLEME = "veri_temizleme"
    IMPORT_KONTROL = "import_kontrol"
    MUSTERI_GUNCELLEME = "musteri_guncelleme"
    GENEL_GOREV = "genel_gorev"
    STAND_TASARIM = "stand_tasarim"
    DIGER = "diger"


CREATABLE_TODO_CATEGORIES = frozenset(
    {
        TodoCategory.ARAMA,
        TodoCategory.ZIYARET,
        TodoCategory.TEKLIF,
        TodoCategory.IMPORT_KONTROL,
        TodoCategory.MUSTERI_GUNCELLEME,
        TodoCategory.GENEL_GOREV,
        TodoCategory.STAND_TASARIM,
        TodoCategory.DIGER,
    }
)

LEGACY_SYSTEM_TODO_CATEGORIES = frozenset(
    {
        TodoCategory.TOPLU_MAIL,
        TodoCategory.SMS,
        TodoCategory.WHATSAPP,
        TodoCategory.VERI_TEMIZLEME,
    }
)
