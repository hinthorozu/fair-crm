from fastapi import APIRouter

from app.modules.activities.api.routes import customer_activities_router, router as activities_router
from app.modules.contacts.api.routes import customer_contacts_router, router as contacts_router
from app.modules.customers.api.routes import router as customers_router
from app.modules.fairs.api.routes import router as fairs_router
from app.modules.imports.api.routes import router as imports_router
from app.modules.participations.api.routes import (
    customer_participations_router,
    fair_participants_router,
    router as participations_router,
)

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(customer_activities_router)
api_v1_router.include_router(activities_router)
api_v1_router.include_router(customer_contacts_router)
api_v1_router.include_router(contacts_router)
api_v1_router.include_router(customer_participations_router)
api_v1_router.include_router(fair_participants_router)
api_v1_router.include_router(participations_router)
api_v1_router.include_router(customers_router)
api_v1_router.include_router(fairs_router)
api_v1_router.include_router(imports_router)
