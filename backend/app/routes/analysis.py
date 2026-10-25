from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import get_settings
from app.schemas.analysis import AnalysisResponse
from app.services.change_detection import InvalidImageError, compare_images, validate_image
from app.services.storage import save_upload
from app.services.vision import get_vision_provider

router = APIRouter(prefix="/api", tags=["analysis"])
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_images(
    before_image: UploadFile = File(...), after_image: UploadFile = File(...)
) -> AnalysisResponse:
    settings = get_settings()
    for upload in (before_image, after_image):
        if upload.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail="Only PNG, JPEG, and WebP images are supported")
    upload_dir = settings.storage_dir / "uploads"
    saved = []
    try:
        max_bytes = settings.max_upload_mb * 1024 * 1024
        for upload in (before_image, after_image):
            path = await save_upload(upload, upload_dir, max_bytes)
            saved.append(path)
            validate_image(path)
        metrics = compare_images(saved[0], saved[1])
    except ValueError as exc:
        for path in saved:
            path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        for path in saved:
            path.unlink(missing_ok=True)
        raise

    provider = get_vision_provider(settings.vision_provider)
    ai_analysis = await provider.explain_changes(str(saved[0]), str(saved[1]), str(metrics["summary"])) if provider else None
    report = AnalysisResponse(analysis_id=uuid4().hex, ai_analysis=ai_analysis, **metrics)
    results_dir = settings.storage_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"{report.analysis_id}.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
