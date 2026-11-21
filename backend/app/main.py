import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  (register all tables)
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.ratelimit import GlobalRateLimitMiddleware
from app.modules.admin.metrics import router as metrics_router
from app.modules.admin.router import router as admin_router
from app.modules.admin.staff import public_router as staff_public_router
from app.modules.admin.staff import router as staff_router
from app.modules.admin.workshops import router as admin_workshops_router
from app.modules.auth.router import router as auth_router
from app.modules.catalog.admin_router import router as catalog_admin_router
from app.modules.catalog.attributes_admin import router as attributes_admin_router
from app.modules.catalog.router import router as catalog_router
from app.modules.catalog.todo import router as todo_router
from app.modules.inventory.router import router as inventory_router
from app.modules.reference.router import router as reference_router
from app.modules.shop.router import admin_router as waitlist_admin_router
from app.modules.shop.router import router as shop_router
from app.modules.users.export import router as export_router
from app.modules.users.router import router as users_router
from app.modules.workshops.profile import router as profile_router
from app.modules.workshops.router import invitations_router
from app.modules.workshops.router import router as workshops_router

logging.basicConfig(level=logging.INFO)

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(title=f"{settings.app_name} API", version="0.1.0")
    # Added first = inner: CORS stays outermost, so 429 answers still carry CORS headers.
    app.add_middleware(GlobalRateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    for r in (
        auth_router,
        users_router,
        export_router,
        workshops_router,
        invitations_router,
        reference_router,
        admin_router,
        metrics_router,
        catalog_router,
        catalog_admin_router,
        inventory_router,
        profile_router,
        todo_router,
        attributes_admin_router,
        staff_router,
        staff_public_router,
        admin_workshops_router,
        shop_router,
        waitlist_admin_router,
    ):
        app.include_router(r, prefix=API_PREFIX)

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
