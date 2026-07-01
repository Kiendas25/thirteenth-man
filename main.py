"""13th Man — Multi-Agent Cognitive Operating System.

Entry point: starts the FastAPI server with static file serving.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.auth import init_auth_db
from app.config import settings
from app.rate_limiter import RateLimiter
from app.trust.memory import init_db

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(application: FastAPI):
    await init_db()
    await init_auth_db()
    yield


app = FastAPI(
    title="13th Man",
    description=(
        "Multi-agent cognitive operating system with adversarial verification. "
        "Jarvis orchestrates specialist agents and the 13th Man challenges "
        "every conclusion before it reaches you."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# Rate limiting middleware
app.add_middleware(RateLimiter)

app.include_router(router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def landing():
    """Landing page."""
    return FileResponse("app/static/landing.html")


@app.get("/app")
async def app_page():
    """Main application."""
    return FileResponse("app/static/index.html")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
