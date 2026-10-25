from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


async def save_upload(upload: UploadFile, destination: Path, max_bytes: int) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "image").suffix.lower()
    path = destination / f"{uuid4().hex}{suffix}"
    size = 0
    try:
        with path.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("Image exceeds the configured upload limit")
                output.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
    return path
