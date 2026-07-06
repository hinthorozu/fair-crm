from dataclasses import dataclass

from app.modules.todos.domain.outcome_value_objects import OutcomePrimaryWorklistStatus


@dataclass(frozen=True)
class DefaultOutcomeSeedSpec:
    code: str
    name: str
    primary_worklist_status: str
    sort_order: int
    requires_action: bool = False
    marks_data_problem: bool = False
    description: str | None = None


DEFAULT_OUTCOME_SEEDS: tuple[DefaultOutcomeSeedSpec, ...] = (
    DefaultOutcomeSeedSpec(
        code="ulasildi",
        name="Ulaşıldı",
        primary_worklist_status=OutcomePrimaryWorklistStatus.CLOSED,
        sort_order=10,
    ),
    DefaultOutcomeSeedSpec(
        code="ulasilamadi",
        name="Ulaşılamadı",
        primary_worklist_status=OutcomePrimaryWorklistStatus.IN_FOLLOW_UP,
        sort_order=20,
    ),
    DefaultOutcomeSeedSpec(
        code="tekrar_aranacak",
        name="Tekrar aranacak",
        primary_worklist_status=OutcomePrimaryWorklistStatus.IN_FOLLOW_UP,
        sort_order=30,
    ),
    DefaultOutcomeSeedSpec(
        code="teklif_istiyor",
        name="Teklif istiyor",
        primary_worklist_status=OutcomePrimaryWorklistStatus.IN_FOLLOW_UP,
        sort_order=40,
        requires_action=True,
    ),
    DefaultOutcomeSeedSpec(
        code="cizim_yapilacak",
        name="Çizim yapılacak",
        primary_worklist_status=OutcomePrimaryWorklistStatus.IN_FOLLOW_UP,
        sort_order=50,
        requires_action=True,
    ),
    DefaultOutcomeSeedSpec(
        code="ilgisiz",
        name="İlgisiz",
        primary_worklist_status=OutcomePrimaryWorklistStatus.CLOSED,
        sort_order=60,
    ),
    DefaultOutcomeSeedSpec(
        code="yanlis_numara",
        name="Yanlış numara",
        primary_worklist_status=OutcomePrimaryWorklistStatus.IN_FOLLOW_UP,
        sort_order=70,
        requires_action=True,
        marks_data_problem=True,
    ),
    DefaultOutcomeSeedSpec(
        code="ozel_takip",
        name="Özel takip gerekiyor",
        primary_worklist_status=OutcomePrimaryWorklistStatus.IN_FOLLOW_UP,
        sort_order=80,
    ),
)
