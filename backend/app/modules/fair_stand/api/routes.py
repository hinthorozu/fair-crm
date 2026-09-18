from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.integrations.kyrox_core.auth import AuthContext
from app.modules.fair_stand.api.dependencies import (
    get_catalog_bootstrap_use_case,
    get_item_use_case,
    require_fair_stand_catalog_access,
)
from app.modules.fair_stand.application.get_catalog_bootstrap import GetCatalogBootstrapUseCase
from app.modules.fair_stand.application.get_item import GetItemUseCase

router = APIRouter(prefix="/fair-stand", tags=["fair-stand"])


@router.get("/catalog/bootstrap")
def get_catalog_bootstrap(
    auth: Annotated[AuthContext, Depends(require_fair_stand_catalog_access)],
    use_case: Annotated[GetCatalogBootstrapUseCase, Depends(get_catalog_bootstrap_use_case)],
) -> dict[str, Any]:
    _ = auth
    snapshot = use_case.execute()
    return {
        "revision": snapshot.revision,
        "categories": [
            {
                "catalogKey": category.catalog_key,
                "catalogName": category.catalog_name,
                "catalogIndex": category.catalog_index,
            }
            for category in snapshot.categories
        ],
        "items": [item.payload for item in snapshot.items],
    }


@router.get("/items/{item_key}")
def get_item(
    item_key: str,
    auth: Annotated[AuthContext, Depends(require_fair_stand_catalog_access)],
    use_case: Annotated[GetItemUseCase, Depends(get_item_use_case)],
) -> dict[str, Any]:
    _ = auth
    item = use_case.execute(item_key)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item.payload
