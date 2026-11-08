from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import me_router
from app.api.routes.auth import router as auth_router
from app.api.routes.catalog import router as catalog_router
from app.api.routes.copies import router as copies_router
from app.api.routes.decks import router as decks_router
from app.api.routes.groups import router as groups_router
from app.api.routes.health import router as health_router
from app.api.routes.requests import router as requests_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(me_router)
api_router.include_router(groups_router)
api_router.include_router(catalog_router)
api_router.include_router(copies_router)
api_router.include_router(decks_router)
api_router.include_router(requests_router)
api_router.include_router(admin_router, include_in_schema=False)
