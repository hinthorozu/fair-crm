from app.modules.fairs.application.commands import FairListResultDto, FairResult
from app.modules.fairs.domain.entities import Fair
from app.modules.fairs.domain.ports import FairListResult


def fair_to_result(fair: Fair) -> FairResult:
    return FairResult(
        id=fair.id,
        organization_id=fair.organization_id,
        name=fair.name,
        organizer=fair.organizer,
        venue=fair.venue,
        city=fair.city,
        country=fair.country,
        start_date=fair.start_date,
        end_date=fair.end_date,
        website=fair.website,
        status=fair.status,
        description=fair.description,
        normalized_name=fair.normalized_name,
        created_at=fair.created_at,
        updated_at=fair.updated_at,
        deleted_at=fair.deleted_at,
    )


def list_result_to_dto(result: FairListResult) -> FairListResultDto:
    return FairListResultDto(
        items=[fair_to_result(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )
