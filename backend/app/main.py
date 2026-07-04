import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.logging import setup_logging
from app.core.request_timing import RequestTimingMiddleware
from app.integrations.kyrox_core.dev_bypass import log_dev_bypass_startup_warning
from app.modules.scraper.core.playwright_availability import log_playwright_browser_startup_check

logger = logging.getLogger(__name__)

DEV_CORS_ORIGINS = frozenset(
    {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    }
)


def _cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin")
    if origin and origin in DEV_CORS_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


def _json_response(request: Request, status_code: int, content: dict) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=content, headers=_cors_headers(request))


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()

    app = FastAPI(
        title="FAIR CRM",
        version=settings.app_version,
        description="Fair CRM product service",
    )

    if settings.app_env in {"development", "local", "test"}:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(DEV_CORS_ORIGINS),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(
        RequestTimingMiddleware,
        slow_request_ms=float(settings.performance_slow_request_ms),
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "fair-crm", "version": settings.app_version}

    app.include_router(api_v1_router)
    log_dev_bypass_startup_warning()
    log_playwright_browser_startup_check()

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
        return _json_response(request, 401, {"detail": str(exc)})

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
        return _json_response(request, 403, {"detail": str(exc)})

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _json_response(request, exc.status_code, {"detail": detail})

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _json_response(request, 422, {"detail": exc.errors()})

    @app.exception_handler(ResponseValidationError)
    async def response_validation_handler(request: Request, exc: ResponseValidationError) -> JSONResponse:
        logger.exception("Response validation failed")
        return _json_response(request, 500, {"detail": "Response validation failed"})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled application error")
        return _json_response(request, 500, {"detail": "Internal server error"})

    return app


app = create_app()
