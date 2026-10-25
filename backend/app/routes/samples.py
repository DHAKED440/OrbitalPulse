import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["samples"])
SCENARIO_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PAIR_FILES = {"before.png", "after.png"}


@router.get("/samples/{scenario_id}/{filename}")
def get_scenario_asset(scenario_id: str, filename: str) -> FileResponse:
    if not SCENARIO_ID_PATTERN.fullmatch(scenario_id) or filename not in PAIR_FILES:
        raise HTTPException(status_code=404, detail="Sample not found")
    sample_dir = get_settings().samples_dir.resolve()
    scenario_dir = (sample_dir / scenario_id).resolve()
    path = (scenario_dir / filename).resolve()
    if scenario_dir.parent != sample_dir or path.parent != scenario_dir or not path.is_file():
        raise HTTPException(status_code=404, detail="Sample not found")
    return FileResponse(path, media_type="image/png", filename=filename)
