from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.digest import router as digest_router
from app.api.landscape import router as landscape_router
from app.api.signals import router as signals_router
from app.api.tenants import router as tenants_router
from app.api.watchlist import router as watchlist_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(signals_router)
api_router.include_router(tenants_router)
api_router.include_router(landscape_router)
api_router.include_router(watchlist_router)
api_router.include_router(digest_router)
