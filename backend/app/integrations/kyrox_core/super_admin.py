from collections.abc import Callable
from uuid import UUID

from app.integrations.kyrox_core.client import KyroxCoreHttpClient

SuperAdminReader = Callable[[str, UUID], bool]


def get_super_admin_reader() -> SuperAdminReader:
    client = KyroxCoreHttpClient()

    def read(access_token: str, organization_id: UUID) -> bool:
        return client.read_is_super_admin(
            access_token=access_token,
            organization_id=organization_id,
        )

    return read
