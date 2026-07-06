from fastapi import APIRouter

from app.modules.activities.api.routes import customer_activities_router, router as activities_router
from app.modules.contacts.api.routes import customer_contacts_router, router as contacts_router
from app.modules.customers.api.routes import router as customers_router
from app.modules.fairs.api.routes import router as fairs_router
from app.modules.data_integration.api.routes import router as data_integration_router
from app.modules.imports.api.routes import router as imports_router
from app.modules.system_admin.api.routes import router as system_admin_router
from app.modules.system_admin.api.data_operation_routes import router as data_operations_router
from app.modules.participations.api.routes import (
    customer_participations_router,
    fair_participants_router,
    router as participations_router,
)
from app.modules.scraper.api.routes import router as scraper_router
from app.modules.smtp.api.routes import router as smtp_router
from app.modules.mail_templates.api.routes import router as mail_templates_router
from app.modules.mail_send_operations.api.routes import router as mail_send_operations_router
from app.modules.fair_emails.api.routes import router as fair_emails_router
from app.modules.todos.api.routes import router as todos_router

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
api_v1_router.include_router(imports_router, prefix="/imports")
api_v1_router.include_router(imports_router, prefix="/data-integration/imports")
api_v1_router.include_router(data_integration_router)
api_v1_router.include_router(system_admin_router)
api_v1_router.include_router(data_operations_router)
api_v1_router.include_router(scraper_router)
api_v1_router.include_router(smtp_router)
api_v1_router.include_router(mail_templates_router)
api_v1_router.include_router(mail_send_operations_router)
api_v1_router.include_router(fair_emails_router)
api_v1_router.include_router(todos_router)
