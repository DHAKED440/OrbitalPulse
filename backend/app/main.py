from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routes.analysis import router as analysis_router

settings = get_settings()
app = FastAPI(title="OrbitalPulse API", version="0.1.0", description="Local-first satellite imagery change detection")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(analysis_router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "vision_provider": settings.vision_provider}
