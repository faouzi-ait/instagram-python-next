import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ROUTES
from routes.auth import router as auth_router
from routes.health import router as health_router

allowed_origins = [
    origin.strip()
    for origin in os.environ["AUTH_ALLOWED_ORIGINS"].split(",")
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
