from collections.abc import Callable

from fastapi import Depends

from app.modules.auth.infrastructure.core_auth_client import CoreAuthClient


def get_core_auth_client() -> CoreAuthClient:
    return CoreAuthClient()


CoreAuthClientDep = Callable[[], CoreAuthClient]
