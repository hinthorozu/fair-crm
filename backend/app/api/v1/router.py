from fastapi import APIRouter

from app.modules.contacts.api.routes import customer_contacts_router, router as contacts_router
from app.modules.customers.api.routes import router as customers_router
from app.modules.fairs.api.routes import router as fairs_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(customer_contacts_router)
api_v1_router.include_router(contacts_router)
api_v1_router.include_router(customers_router)
api_v1_router.include_router(fairs_router)
