from fastapi import APIRouter

from app.api import appeals, audit, auth, reports, settings, staff, stats, users

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(appeals.router)
api_router.include_router(staff.router)
api_router.include_router(users.router)
api_router.include_router(stats.router)
api_router.include_router(reports.router)
api_router.include_router(settings.router)
api_router.include_router(audit.router)

__all__ = ["api_router"]
