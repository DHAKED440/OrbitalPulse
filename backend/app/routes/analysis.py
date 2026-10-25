from datetime import date
from uuid import uuid4

import cv2
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import get_settings
from app.schemas.analysis import AnalysisResponse
from app.services.change_detection import InvalidImageError, compare_images, validate_image
from app.services.storage import save_upload
from app.services.vision import get_vision_provider

router = APIRouter(prefix="/api", tags=["analysis"])
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_images(
    before_image: UploadFile = File(...),
    after_image: UploadFile = File(...),
    location: str | None = Form(default=None, max_length=200),
    before_date: date | None = Form(default=None),
    after_date: date | None = Form(default=None),
) -> AnalysisResponse:
    settings = get_settings()
    for upload in (before_image, after_image):
        if upload.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail="Only PNG, JPEG, and WebP images are supported")
    if before_date and after_date and before_date > after_date:
        raise HTTPException(status_code=422, detail="Baseline date must be on or before latest image date")
    upload_dir = settings.storage_dir / "uploads"
    saved = []
    try:
        max_bytes = settings.max_upload_mb * 1024 * 1024
        for upload in (before_image, after_image):
            path = await save_upload(upload, upload_dir, max_bytes)
            saved.append(path)
            validate_image(path)
        metrics, annotated = compare_images(saved[0], saved[1])
    except ValueError as exc:
        for path in saved:
            path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        for path in saved:
            path.unlink(missing_ok=True)
        raise

    provider = get_vision_provider(settings.vision_provider)
    try:
        ai_analysis = await provider.explain_changes(str(saved[0]), str(saved[1]), str(metrics["summary"])) if provider else None
    except Exception:
        # Keep local CV useful when an optional remote provider is unavailable.
        ai_analysis = None
    finally:
        for path in saved:
            path.unlink(missing_ok=True)
    analysis_id = uuid4().hex
    results_dir = settings.storage_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    annotated_path = results_dir / f"{analysis_id}.png"
    if not cv2.imwrite(str(annotated_path), annotated):
        raise HTTPException(status_code=500, detail="Could not save annotated comparison image")
    report = AnalysisResponse(
        analysis_id=analysis_id,
        location=location.strip() if location and location.strip() else None,
        before_date=before_date,
        after_date=after_date,
        annotated_image_url=f"/api/reports/{analysis_id}/annotated",
        report_url=f"/api/reports/{analysis_id}",
        ai_analysis=ai_analysis,
        **metrics,
    )
    (results_dir / f"{analysis_id}.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
