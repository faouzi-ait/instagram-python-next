import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ROUTES
from routes.auth import router as auth_router
from routes.health import router as health_router

auth_allowed_origins = os.environ.get("AUTH_ALLOWED_ORIGINS")
if not auth_allowed_origins:
    raise RuntimeError(
        "AUTH_ALLOWED_ORIGINS is required. Set it to the comma-separated frontend origin(s)."
    )

allowed_origins = [
    origin.strip()
    for origin in auth_allowed_origins.split(",")
    if origin.strip()
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=allowed_origins,
    allow_headers=["Content-Type", "Accept"],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(health_router, prefix="/api")
