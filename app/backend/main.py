import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from rate_limit import limiter

# ROUTES
from routes.auth import router as auth_router
from routes.posts import router as posts_router
from routes.likes import router as likes_router
from routes.health import router as health_router
from routes.comments import router as comments_router
from routes.follow import router as follows_router

auth_allowed_origins = os.environ.get("AUTH_ALLOWED_ORIGINS")
if not auth_allowed_origins:
    raise RuntimeError("AUTH_ALLOWED_ORIGINS is required. Set it to the comma-separated frontend origin(s).")

allowed_origins = [
    origin.strip()
    for origin in auth_allowed_origins.split(",")
    if origin.strip()
]

app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=allowed_origins,
    allow_headers=["Content-Type", "Accept"],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(posts_router, prefix="/api")
app.include_router(comments_router, prefix="/api")
app.include_router(likes_router, prefix="/api")
app.include_router(follows_router, prefix="/api")

