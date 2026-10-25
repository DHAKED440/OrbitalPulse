import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.schemas.analysis import AnalysisResponse

router = APIRouter(prefix="/api/reports", tags=["reports"])
REPORT_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


def _report_path(analysis_id: str, suffix: str) -> Path:
    if not REPORT_ID_PATTERN.fullmatch(analysis_id):
        raise HTTPException(status_code=404, detail="Report not found")
    return get_settings().storage_dir / "results" / f"{analysis_id}{suffix}"


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_report(analysis_id: str) -> AnalysisResponse:
    path = _report_path(analysis_id, ".json")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        return AnalysisResponse.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=500, detail="Stored report is invalid") from exc


@router.get("/{analysis_id}/annotated")
def get_annotated_image(analysis_id: str) -> FileResponse:
    path = _report_path(analysis_id, ".png")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Annotated image not found")
    return FileResponse(path, media_type="image/png", filename=f"{analysis_id}-annotated.png")
