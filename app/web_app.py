"""FastAPI web server: Administrator paneli va REST API."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.database.base import Base
from app.database.session import dispose_engine, get_engine, session_scope
from app.services.exceptions import ServiceError
from app.services.staff_service import ensure_super_admins
from app.utils.logging_setup import setup_logging
from app.utils.redis_client import close_redis
from config.settings import get_settings


async def init_db_and_admins() -> None:
    """Bazada jadvallarni tekshiradi va Super Adminlarni ta'minlaydi."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = get_settings()
    if settings.super_admin_id_list:
        async with session_scope() as session:
            added = await ensure_super_admins(session, settings.super_admin_id_list)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    # Bazani tekshirish va super adminlarni qo'shish
    await init_db_and_admins()
    yield
    # Resurslarni tozalash
    await close_redis()
    await dispose_engine()


app = FastAPI(
    title="Urganch davlat akademik litseyi — Murojaatlar Tizimi API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "detail": exc.message},
    )


# API Routerni ulash
app.include_router(api_router)

# Statik fayllar (Logotip, favicon va h.k.)
STATIC_DIR = Path(__file__).parent / "admin" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Admin Panel HTML sahifasi
ADMIN_HTML_PATH = Path(__file__).parent / "admin" / "templates" / "index.html"


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    fav_path = STATIC_DIR / "favicon.ico"
    if fav_path.exists():
        return FileResponse(fav_path, media_type="image/x-icon")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
@app.get("/", include_in_schema=False)
async def serve_admin_panel():
    if not ADMIN_HTML_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin panel shabloni topilmadi",
        )
    return FileResponse(ADMIN_HTML_PATH, media_type="text/html")


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "app": "Urganch DAL Murojaat Tizimi"}
