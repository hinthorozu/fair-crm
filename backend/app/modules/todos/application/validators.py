from uuid import UUID

from app.modules.fairs.domain.exceptions import FairNotFoundError
from app.modules.fairs.domain.ports import FairRepository


def ensure_source_fair_exists(
    fair_repository: FairRepository,
    organization_id: UUID,
    source_fair_id: UUID,
) -> None:
    fair = fair_repository.get_by_id(organization_id, source_fair_id)
    if fair is None:
        raise FairNotFoundError("Fair not found")
