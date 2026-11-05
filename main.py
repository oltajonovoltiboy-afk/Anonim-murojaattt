"""Urganch davlat akademik litseyi Murojaatlar Tizimi — Faqat Web-Panel."""
from __future__ import annotations

import uvicorn
from app.web_app import app
from config.settings import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "app.web_app:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
