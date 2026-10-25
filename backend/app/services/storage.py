import json
import os
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import UploadFile


async def save_upload(upload: UploadFile, destination: Path, max_bytes: int) -> Path:
    """Stream an upload to a private, randomly named temporary file."""
    destination.mkdir(parents=True, exist_ok=True)
    fd, raw_path = tempfile.mkstemp(prefix="upload-", suffix=".img", dir=destination)
    path = Path(raw_path)
    size = 0
    try:
        with os.fdopen(fd, "wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise UploadTooLargeError("Each image must be within the configured upload limit")
                output.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
    return path


class UploadTooLargeError(ValueError):
    pass


def save_report(results_dir: Path, report_id: str, payload: str) -> None:
    """Atomically persist a JSON report under a server-generated identifier."""
    results_dir.mkdir(parents=True, exist_ok=True)
    target = results_dir / f"{report_id}.json"
    fd, raw_path = tempfile.mkstemp(prefix=".report-", suffix=".tmp", dir=results_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(raw_path, target)
    except Exception:
        Path(raw_path).unlink(missing_ok=True)
        raise


def load_report(results_dir: Path, report_id: str, retention_seconds: int) -> dict | None:
    """Read a retained report; delete expired records and reject unsafe IDs."""
    if not report_id.isalnum() or len(report_id) != 32:
        return None
    path = results_dir / f"{report_id}.json"
    try:
        if time.time() - path.stat().st_mtime > retention_seconds:
            path.unlink(missing_ok=True)
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def list_sample_scenarios(samples_dir: Path) -> list[dict]:
    """Return only complete scenario folders and their synthetic sample metadata."""
    if not samples_dir.is_dir():
        return []
    media_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    scenarios: list[dict] = []
    for folder in sorted(samples_dir.iterdir()):
        metadata_path = folder / "scenario.json"
        if not folder.is_dir() or not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            scenario_id = metadata.get("id")
            if not isinstance(scenario_id, str) or scenario_id != folder.name or not scenario_id.replace("-", "").isalnum():
                continue
            before = (folder / "before.png").resolve()
            after = (folder / "after.png").resolve()
            resolved_folder = folder.resolve()
            if before.parent != resolved_folder or after.parent != resolved_folder or not before.is_file() or not after.is_file():
                continue
            for key, path in (("before", before), ("after", after)):
                metadata[key] = {
                    "filename": path.name,
                    "url": f"/api/samples/{quote(scenario_id)}/{quote(path.name)}",
                    "size_bytes": path.stat().st_size,
                    "media_type": media_types[path.suffix.lower()],
                }
            scenarios.append(metadata)
        except (OSError, ValueError, TypeError):
            continue
    return scenarios
