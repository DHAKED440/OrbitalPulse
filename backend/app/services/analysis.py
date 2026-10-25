import logging
import tempfile
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings
from app.schemas.analysis import AnalysisResponse
from app.services.classifier import VisionInputLimitError, classify_analysis
from app.services.change_detection import InvalidImageError, compare_images, validate_image
from app.services.reporting import build_intelligence_report
from app.services.storage import UploadTooLargeError, save_report, save_upload
from app.services.vision import VisionProviderError, VisionRateLimitError, get_vision_provider

logger = logging.getLogger(__name__)


async def analyze_uploads(
    before_image: UploadFile,
    after_image: UploadFile,
    *,
    location: str | None,
    before_acquisition_date: date | None,
    after_acquisition_date: date | None,
    comparison_mode: str,
    ai_consent: bool,
    settings: Settings,
) -> AnalysisResponse:
    """Validate, temporarily stage, and compare a pair of uploaded images."""
    staging_root = settings.storage_dir / "tmp"
    staging_root.mkdir(parents=True, exist_ok=True)
    report_id = uuid4().hex
    semantic_status = "not_requested"
    semantic_analysis = None
    semantic_error = None
    provider = get_vision_provider(settings)
    try:
        with tempfile.TemporaryDirectory(prefix="analysis-", dir=staging_root) as workdir:
            work = Path(workdir)
            max_bytes = settings.max_upload_mb * 1024 * 1024
            paths = []
            for upload in (before_image, after_image):
                path = await save_upload(upload, work, max_bytes)
                validate_image(path, max_dimension=settings.max_image_dimension, max_pixels=settings.max_image_pixels)
                paths.append(path)
            metrics = compare_images(
                paths[0],
                paths[1],
                max_working_dimension=settings.max_working_dimension,
                threshold=settings.change_threshold,
                min_region_area=settings.min_region_area,
                min_region_percent=settings.min_region_percent,
                comparison_mode=comparison_mode,
            )
            if not ai_consent:
                if provider is not None:
                    semantic_status = "consent_required"
                    semantic_error = "Explicit consent is required before images are sent to OpenAI."
                else:
                    semantic_status = "unavailable"
                    semantic_error = "Semantic classification is not configured."
            elif provider is None:
                semantic_status = "unavailable"
                semantic_error = "Semantic classification is not configured."
            else:
                try:
                    semantic_analysis = await classify_analysis(
                        provider,
                        paths[0],
                        paths[1],
                        metrics,
                        settings=settings,
                        location=location,
                        before_acquisition_date=before_acquisition_date.isoformat() if before_acquisition_date else None,
                        after_acquisition_date=after_acquisition_date.isoformat() if after_acquisition_date else None,
                    )
                    semantic_status = "complete"
                except VisionRateLimitError:
                    logger.warning("Semantic classifier rate limited; computer-vision result retained")
                    semantic_status = "rate_limited"
                    semantic_error = "Semantic classification is rate limited; computer-vision results are still available."
                except (VisionProviderError, VisionInputLimitError):
                    logger.warning("Semantic classifier unavailable; computer-vision result retained", exc_info=True)
                    semantic_status = "failed"
                    semantic_error = "Semantic classification failed; computer-vision results are still available."
                except Exception:
                    logger.exception("Unexpected semantic classifier failure; computer-vision result retained")
                    semantic_status = "failed"
                    semantic_error = "Semantic classification failed; computer-vision results are still available."
    except (UploadTooLargeError, InvalidImageError) as exc:
        logger.info("Rejected image analysis request: %s", exc)
        raise
    except Exception:
        logger.exception("Image analysis failed")
        raise

    report_content = {
        **metrics,
        "analysis_id": report_id,
        "location": location,
        "before_acquisition_date": before_acquisition_date,
        "after_acquisition_date": after_acquisition_date,
        "semantic_status": semantic_status,
        "semantic_analysis": semantic_analysis.model_dump(mode="json") if semantic_analysis else None,
        "semantic_error": semantic_error,
    }
    intelligence_report = build_intelligence_report(report_content)
    report = AnalysisResponse(
        analysis_id=report_id,
        location=location,
        before_acquisition_date=before_acquisition_date,
        after_acquisition_date=after_acquisition_date,
        semantic_status=semantic_status,
        semantic_analysis=semantic_analysis,
        semantic_error=semantic_error,
        report=intelligence_report,
        **metrics,
    )
    save_report(settings.storage_dir / "results", report_id, report.model_dump_json(indent=2))
    logger.info("Image comparison completed", extra={"analysis_id": report_id})
    return report
