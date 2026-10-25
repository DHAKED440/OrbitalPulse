import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routes.analysis import router as analysis_router
from app.routes.samples import router as samples_router
from app.services.vision import get_vision_provider

settings = get_settings()
logging.basicConfig(
    level=logging.INFO if settings.app_env == "production" else logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
app = FastAPI(title="OrbitalPulse API", version="0.1.0", description="Local-first satellite imagery change detection")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(analysis_router)
app.include_router(samples_router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str | bool]:
    ai_configured = get_vision_provider(settings) is not None
    return {
        "status": "ok",
        "ai_configured": ai_configured,
        "ai_status": "ready" if ai_configured else "unavailable",
    }
