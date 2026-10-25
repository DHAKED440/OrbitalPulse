from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.analysis import AnalysisResponse, SamplesResponse
from app.services.analysis import analyze_uploads
from app.services.change_detection import InvalidImageError
from app.services.reporting import build_intelligence_report, report_html, report_json, report_markdown
from app.services.storage import UploadTooLargeError, list_sample_scenarios, load_report

router = APIRouter(prefix="/api", tags=["analysis"])
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_images(
    before_image: UploadFile = File(...),
    after_image: UploadFile = File(...),
    location: str | None = Form(None, max_length=200),
    before_acquisition_date: date | None = Form(None),
    after_acquisition_date: date | None = Form(None),
    comparison_mode: Literal["registered", "original"] = Form("registered"),
    ai_consent: bool = Form(False),
) -> AnalysisResponse:
    uploads = (before_image, after_image)
    try:
        for upload in uploads:
            if upload.content_type not in ALLOWED_TYPES:
                raise HTTPException(status_code=415, detail="Only PNG, JPEG, and WebP images are supported")
        try:
            return await analyze_uploads(
                before_image,
                after_image,
                location=location.strip() if location and location.strip() else None,
                before_acquisition_date=before_acquisition_date,
                after_acquisition_date=after_acquisition_date,
                comparison_mode=comparison_mode,
                ai_consent=ai_consent,
                settings=get_settings(),
            )
        except UploadTooLargeError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except InvalidImageError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        for upload in uploads:
            await upload.close()


@router.get("/samples", response_model=SamplesResponse)
def get_samples() -> SamplesResponse:
    settings = get_settings()
    return SamplesResponse(samples=list_sample_scenarios(settings.samples_dir))


@router.get("/report/{analysis_id}", response_model=AnalysisResponse)
def get_report(analysis_id: str) -> AnalysisResponse:
    return _get_valid_report(analysis_id)


@router.get("/report/{analysis_id}/download")
def download_report(
    analysis_id: str,
    format: Literal["json", "markdown", "html"] = Query("json"),
) -> Response:
    report = _get_valid_report(analysis_id)
    if format == "json":
        content, media_type = report_json(report), "application/json"
    elif format == "markdown":
        content, media_type = report_markdown(report), "text/markdown; charset=utf-8"
    else:
        content, media_type = report_html(report), "text/html; charset=utf-8"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="orbitalpulse-{analysis_id}.{format}"'},
    )


def _get_valid_report(analysis_id: str) -> AnalysisResponse:
    settings = get_settings()
    results_dir = settings.storage_dir / "results"
    data = load_report(results_dir, analysis_id, settings.report_retention_hours * 3600)
    if data is None:
        raise HTTPException(status_code=404, detail="Analysis report was not found or has expired")
    # Backfill reports written by an earlier app version using the retained file's timestamp.
    if "report" not in data:
        try:
            stored_at = datetime.fromtimestamp((results_dir / f"{analysis_id}.json").stat().st_mtime, timezone.utc)
        except OSError:
            raise HTTPException(status_code=404, detail="Analysis report was not found or has expired") from None
        data["report"] = build_intelligence_report(data, timestamp=stored_at).model_dump(mode="json")
    try:
        return AnalysisResponse.model_validate(data)
    except ValidationError:
        raise HTTPException(status_code=500, detail="The retained analysis report is invalid") from None
