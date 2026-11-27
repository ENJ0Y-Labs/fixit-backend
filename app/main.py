from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import get_settings
settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug, description="Backend API for the FixIt marketplace.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Accept", "Content-Type", "X-CSRF-Token"])
app.include_router(api_router, prefix="/api/v1")
@app.get("/", tags=["Root"], summary="API information")
def root() -> dict[str, str]:
    return {"application": settings.app_name, "version": settings.app_version, "docs": "/docs", "health": "/api/v1/health"}
