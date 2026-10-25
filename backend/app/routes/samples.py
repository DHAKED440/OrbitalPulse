import json
import re
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.schemas.analysis import SampleImage, SampleScenario

router = APIRouter(prefix="/api/samples", tags=["samples"])
MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
SCENARIO_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PAIR_FILES = {"before.png", "after.png"}


def _asset(scenario_dir: Path, scenario_id: str, filename: str) -> SampleImage:
    path = scenario_dir / filename
    if not path.is_file() or path.suffix.lower() not in MEDIA_TYPES:
        raise ValueError(f"Missing supported sample asset: {filename}")
    return SampleImage(
        filename=filename,
        url=f"/api/samples/{quote(scenario_id)}/{quote(filename)}",
        size_bytes=path.stat().st_size,
        media_type=MEDIA_TYPES[path.suffix.lower()],
    )


@router.get("", response_model=list[SampleScenario])
def list_samples() -> list[SampleScenario]:
    sample_dir = get_settings().sample_dir
    if not sample_dir.exists():
        return []
    scenarios: list[SampleScenario] = []
    for scenario_dir in sorted(sample_dir.iterdir()):
        metadata_path = scenario_dir / "scenario.json"
        if not scenario_dir.is_dir() or not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            scenario_id = metadata.get("id")
            if not isinstance(scenario_id, str) or scenario_id != scenario_dir.name or not SCENARIO_ID_PATTERN.fullmatch(scenario_id):
                continue
            scenarios.append(
                SampleScenario(
                    **metadata,
                    before=_asset(scenario_dir, scenario_id, "before.png"),
                    after=_asset(scenario_dir, scenario_id, "after.png"),
                )
            )
        except (OSError, ValueError, TypeError):
            # Ignore incomplete or invalid scenario folders instead of failing the entire picker.
            continue
    return scenarios


@router.get("/{filename}")
def get_sample(filename: str) -> FileResponse:
    if Path(filename).name != filename:
        raise HTTPException(status_code=404, detail="Sample not found")
    sample_dir = get_settings().sample_dir.resolve()
    path = (sample_dir / filename).resolve()
    if path.parent != sample_dir or not path.is_file() or path.suffix.lower() not in MEDIA_TYPES:
        raise HTTPException(status_code=404, detail="Sample not found")
    return FileResponse(path, media_type=MEDIA_TYPES[path.suffix.lower()], filename=path.name)


@router.get("/{scenario_id}/{filename}")
def get_scenario_asset(scenario_id: str, filename: str) -> FileResponse:
    if not SCENARIO_ID_PATTERN.fullmatch(scenario_id) or filename not in PAIR_FILES:
        raise HTTPException(status_code=404, detail="Sample not found")
    sample_dir = get_settings().sample_dir.resolve()
    scenario_dir = (sample_dir / scenario_id).resolve()
    path = (scenario_dir / filename).resolve()
    if scenario_dir.parent != sample_dir or path.parent != scenario_dir or not path.is_file():
        raise HTTPException(status_code=404, detail="Sample not found")
    return FileResponse(path, media_type="image/png", filename=filename)
