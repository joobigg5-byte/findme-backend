"""
find-me backend — entry point.

Run locally with:
    uvicorn app.main:app --reload --port 8000

Then visit http://localhost:8000/docs for live, interactive API docs
(Swagger UI) — every endpoint below is real and callable from there.
"""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from . import models
from .database import engine
from .auth import limiter
from .routers import auth, facilities, directory, staff, cautions

# Structured logging to stdout — every real host (Render included) captures
# stdout automatically and shows it in a log dashboard, no extra service
# needed to get basic visibility into what the app is doing.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("findme")

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="find-me API",
    description="Backend for find-me — multi-tenant facility wayfinding and directory.",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS_ORIGINS is a comma-separated list, e.g.
#   CORS_ORIGINS=https://app.find-me.example,https://admin.find-me.example
# Defaults to "*" (allow everything) for frictionless local development —
# set this explicitly before real traffic hits the API.
_cors_env = os.environ.get("CORS_ORIGINS", "*")
cors_origins = ["*"] if _cors_env == "*" else [origin.strip() for origin in _cors_env.split(",")]
if cors_origins == ["*"]:
    logger.warning("CORS_ORIGINS not set — allowing all origins. Set this before going live.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(facilities.router)
app.include_router(directory.router)
app.include_router(staff.router)
app.include_router(cautions.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    logger.info("find-me API starting up. CORS origins: %s", cors_origins)
